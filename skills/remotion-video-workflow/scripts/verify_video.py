#!/usr/bin/env python3
"""Verify final video metadata, full decoding and optionally exact loop pixels."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
from timeline import validate


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or f'command failed: {command[0]}')
    return result.stdout


def pixel_diff(first, last, channels):
    if len(first) != len(last) or not first or len(first) % channels:
        raise ValueError('pixel buffers are empty or incompatible')
    return {'max_channel_difference': max(abs(a-b) for a, b in zip(first, last)),
            'different_values': sum(a != b for a, b in zip(first, last)),
            'different_pixels': sum(first[i:i+channels] != last[i:i+channels] for i in range(0, len(first), channels))}


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def verify(args):
    result = {'ok': False, 'file': args.video.name, 'errors': []}
    try:
        metadata = probe(args.video)
        videos = [x for x in metadata['streams'] if x['codec_type'] == 'video' and not x.get('disposition', {}).get('attached_pic')]
        audio = [x for x in metadata['streams'] if x['codec_type'] == 'audio']
        if len(videos) != 1:
            raise ValueError('expected exactly one video stream excluding attached pictures')
        stream = videos[0]
        count = stream.get('nb_frames')
        if not count or count == 'N/A':
            counted = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', str(stream['index']), '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'json', str(args.video)]))
            count = counted['streams'][0]['nb_read_frames']
        count = int(count)
        fps = Fraction(stream['avg_frame_rate'])
        result['video'] = {'width': stream['width'], 'height': stream['height'], 'fps': str(fps), 'frames': count,
                           'codec': stream['codec_name'], 'pixel_format': stream.get('pix_fmt'), 'duration': stream.get('duration')}
        result['audio'] = [{'codec': x['codec_name'], 'sample_rate': x.get('sample_rate'), 'channels': x.get('channels'), 'duration': x.get('duration')} for x in audio]
        expected = {'width': args.width, 'height': args.height, 'fps': args.fps, 'frames': args.frames}
        if args.timeline:
            timeline = validate(json.loads(args.timeline.read_text(encoding='utf-8')))
            if not timeline['ok']:
                raise ValueError('invalid timeline: ' + '; '.join(timeline['errors']))
            for key in ['fps', 'frames']:
                if expected[key] is not None and Fraction(str(expected[key])) != Fraction(str(timeline[key])):
                    raise ValueError(f'conflicting {key} expectations')
                expected[key] = timeline[key]
        for key, value in expected.items():
            if value is not None and Fraction(str(result['video'][key])) != Fraction(str(value)):
                result['errors'].append(f'{key}: got {result["video"][key]}, expected {value}')
        if args.audio == 'required' and not audio:
            result['errors'].append('audio stream required but absent')
        if args.audio == 'absent' and audio:
            result['errors'].append('silent output unexpectedly contains audio')
        decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(args.video), '-map', f'0:{stream["index"]}', '-map', '0:a?', '-f', 'null', '-'], capture_output=True, text=True)
        result['full_decode'] = decoded.returncode == 0 and not decoded.stderr.strip()
        if not result['full_decode']:
            result['errors'].append('full decode failed: ' + decoded.stderr.strip())
        if args.exact_loop:
            if count < 2:
                raise ValueError('loop comparison needs at least two frames')
            pixels = run(['ffmpeg', '-v', 'error', '-i', str(args.video), '-map', f'0:{stream["index"]}', '-an', '-vf', f'select=eq(n\\,0)+eq(n\\,{count-1})', '-fps_mode', 'vfr', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
            size = stream['width'] * stream['height'] * 3
            if len(pixels) != 2 * size:
                raise ValueError('did not decode exactly two boundary frames')
            result['encoded_boundaries'] = pixel_diff(pixels[:size], pixels[size:], 3)
            if result['encoded_boundaries']['different_values']:
                result['errors'].append('decoded video endpoints differ')
        if args.source_first or args.source_last:
            if not (args.source_first and args.source_last):
                raise ValueError('both --source-first and --source-last are required together')
            from PIL import Image
            with Image.open(args.source_first) as a, Image.open(args.source_last) as b:
                if a.size != b.size:
                    raise ValueError('source image dimensions differ')
                result['source_boundaries'] = pixel_diff(a.convert('RGBA').tobytes(), b.convert('RGBA').tobytes(), 4)
            if result['source_boundaries']['different_values']:
                result['errors'].append('source image endpoints differ')
    except (OSError, ValueError, KeyError, ImportError, ZeroDivisionError) as error:
        result['errors'].append(str(error))
    result['ok'] = not result['errors']
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--timeline', type=Path)
    p.add_argument('--width', type=int)
    p.add_argument('--height', type=int)
    p.add_argument('--fps')
    p.add_argument('--frames', type=int)
    p.add_argument('--audio', choices=['optional', 'required', 'absent'], default='optional')
    p.add_argument('--exact-loop', action='store_true')
    p.add_argument('--source-first', type=Path)
    p.add_argument('--source-last', type=Path)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    result = verify(args)
    content = json.dumps(result, ensure_ascii=False, indent=2)
    print(content)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content + '\n', encoding='utf-8')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
