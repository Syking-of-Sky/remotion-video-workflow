#!/usr/bin/env python3
"""Local RMS/onset analysis; explicit BPM grids are not automatic beat tracking."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile


def analyze(path, rate=22050, hop=1102, bpm=None, offset=0.0):
    if rate <= 0 or hop <= 0 or not math.isfinite(offset) or offset < 0:
        raise ValueError('sample rate and hop must be positive; offset must be finite and nonnegative')
    if bpm is not None and (not math.isfinite(bpm) or bpm <= 0):
        raise ValueError('BPM must be finite and positive')
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]))
    if not any(s['codec_type'] == 'audio' for s in metadata['streams']):
        raise ValueError('input has no audio stream')
    envelope, samples = [], 0
    with tempfile.TemporaryFile() as diagnostics:
        process = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-'], stdout=subprocess.PIPE, stderr=diagnostics)
        try:
            while True:
                chunk = process.stdout.read(hop * 4)
                if not chunk:
                    break
                if len(chunk) % 4:
                    raise ValueError('incomplete PCM sample')
                values = array('f')
                values.frombytes(chunk)
                if sys.byteorder != 'little':
                    values.byteswap()
                energy = math.sqrt(sum(x*x for x in values) / len(values))
                if not math.isfinite(energy):
                    raise ValueError('nonfinite audio sample')
                envelope.append({'time': samples / rate, 'rms': energy})
                samples += len(values)
            code = process.wait()
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
        diagnostics.seek(0)
        message = diagnostics.read().decode(errors='replace').strip()
        if code or message:
            raise ValueError(message or 'audio decoding failed')
    if not envelope:
        raise ValueError('input decoded to no samples')
    peak = max(x['rms'] for x in envelope)
    for item in envelope:
        item['normalized'] = item['rms'] / peak if peak else 0.0
    changes = [max(0.0, envelope[i]['rms'] - envelope[i-1]['rms']) for i in range(1, len(envelope))]
    median = statistics.median(changes) if changes else 0.0
    deviation = statistics.median(abs(x-median) for x in changes) if changes else 0.0
    threshold = max(median + 3 * deviation, peak * .06)
    onsets = []
    for i, change in enumerate(changes, 1):
        time = envelope[i]['time']
        if change > threshold and (not onsets or time - onsets[-1] >= .15):
            onsets.append(time)
    duration = samples / rate
    beats = []
    if bpm is not None and offset < duration:
        count = math.ceil((duration-offset) * bpm / 60)
        if count > 100000:
            raise ValueError('requested BPM grid exceeds 100000 events')
        beats = [offset + i * 60 / bpm for i in range(count)]
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'sourceFile': path.name, 'sourceSha256': digest.hexdigest(),
            'sourceDuration': float(metadata['format']['duration']), 'decodedDuration': duration,
            'sampleRate': rate, 'hopSamples': hop, 'rms': envelope, 'onsetCandidates': onsets,
            'beats': beats, 'bpm': bpm, 'beatOffset': offset if bpm is not None else None,
            'beatSource': 'explicit_bpm_grid' if bpm is not None else 'not_estimated',
            'note': 'RMS is amplitude; onset candidates and supplied BPM grids are not verified musical beats.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('audio', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--sample-rate', type=int, default=22050)
    p.add_argument('--hop', type=int, default=1102)
    p.add_argument('--bpm', type=float)
    p.add_argument('--offset', type=float, default=0)
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    try:
        if args.output.exists() and not args.force:
            raise FileExistsError('output exists; use --force to replace it')
        if args.output.resolve() == args.audio.resolve():
            raise ValueError('output must not replace source audio')
        result = analyze(args.audio, args.sample_rate, args.hop, args.bpm, args.offset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'duration': result['decodedDuration'], 'rmsWindows': len(result['rms']), 'beatSource': result['beatSource']}))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
