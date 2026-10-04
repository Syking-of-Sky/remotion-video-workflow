#!/usr/bin/env python3
"""Validate frame/second timelines and export supplied text without rewriting it."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate(data, expected=None):
    errors = []
    if not isinstance(data, dict):
        return {'ok': False, 'errors': ['timeline must be an object']}
    try:
        fps = Fraction(str(data['fps']))
        if fps <= 0:
            raise ValueError()
    except (KeyError, ValueError, ZeroDivisionError):
        return {'ok': False, 'errors': ['fps must be a positive number or rational string']}
    frames = data.get('durationInFrames')
    if not positive_int(frames):
        return {'ok': False, 'errors': ['durationInFrames must be a positive integer']}
    duration = float(Fraction(frames) / fps)
    scenes, lines = data.get('scenes', []), data.get('lines', [])
    if not isinstance(scenes, list) or not isinstance(lines, list):
        return {'ok': False, 'errors': ['scenes and lines must be arrays']}
    cursor, ids = 0, set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f'scene {i}: must be an object')
            continue
        name, start, length = scene.get('id'), scene.get('startFrame'), scene.get('durationInFrames')
        if not isinstance(name, str) or not name or name in ids:
            errors.append(f'scene {i}: id must be a unique nonempty string')
        else:
            ids.add(name)
        if not isinstance(start, int) or isinstance(start, bool) or start != cursor or not positive_int(length):
            errors.append(f'scene {i}: must continue at frame {cursor} with positive integer length')
        if isinstance(start, int) and positive_int(length):
            cursor = start + length
    if scenes and cursor != frames:
        errors.append(f'scene coverage ends at {cursor}, expected {frames}')
    previous = 0.0
    text_lines = []
    words_count = 0
    for i, line in enumerate(lines):
        if not isinstance(line, dict):
            errors.append(f'line {i}: must be an object')
            continue
        start, end, text = line.get('start'), line.get('end'), line.get('text')
        if not isinstance(text, str) or not text.strip() or '\n' in text or '\r' in text:
            errors.append(f'line {i}: text must be one nonempty line')
        text_lines.append(text)
        if not finite(start) or not finite(end) or not (0 <= start < end <= duration + 1e-6):
            errors.append(f'line {i}: invalid or out-of-range time')
            continue
        if start < previous - 1e-6:
            errors.append(f'line {i}: overlaps previous line')
        previous = end
        if 'words' in line:
            words = line['words']
            if not isinstance(words, list) or not words:
                errors.append(f'line {i}: words must be a nonempty array when supplied')
                continue
            word_end, fragments = start, []
            for j, word in enumerate(words):
                if not isinstance(word, dict):
                    errors.append(f'line {i} word {j}: must be an object')
                    continue
                a, b, value = word.get('start'), word.get('end'), word.get('text')
                if not isinstance(value, str) or not value:
                    errors.append(f'line {i} word {j}: missing text')
                else:
                    fragments.append(value)
                if not finite(a) or not finite(b) or not (start - 1e-6 <= a < b <= end + 1e-6):
                    errors.append(f'line {i} word {j}: outside line or nonpositive duration')
                    continue
                if a < word_end - 1e-6:
                    errors.append(f'line {i} word {j}: overlapping words')
                word_end = b
            if ''.join(fragments) != text:
                errors.append(f'line {i}: word text does not reconstruct line')
            words_count += len(words)
    if expected is not None and text_lines != expected:
        errors.append('ordered lyric text differs from expected text (including repetitions)')
    if 'audioDuration' in data and (not finite(data['audioDuration']) or not 0 < data['audioDuration'] <= duration + 1e-6):
        errors.append('audioDuration must be positive and not exceed video duration')
    return {'ok': not errors, 'errors': errors, 'fps': str(fps), 'frames': frames,
            'duration': duration, 'scenes': len(scenes), 'lines': len(lines), 'words': words_count}


def timestamp(seconds):
    value = round(seconds * 1000)
    hours, value = divmod(value, 3600000)
    minutes, value = divmod(value, 60000)
    seconds, millis = divmod(value, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def export_srt(lines):
    for line in lines:
        if round(line['end'] * 1000) <= round(line['start'] * 1000):
            raise ValueError('subtitle is too short for millisecond SRT precision')
    return '\n\n'.join(f'{i+1}\n{timestamp(line["start"])} --> {timestamp(line["end"])}\n{line["text"]}'
                       for i, line in enumerate(lines)) + '\n'


def export_lrc(lines):
    def mark(t):
        minutes, ticks = divmod(round(t * 100), 6000)
        seconds, hundredths = divmod(ticks, 100)
        return f'[{minutes:02}:{seconds:02}.{hundredths:02}]'
    return ''.join(mark(line['start']) + line['text'] + '\n' for line in lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--expected-text', type=Path)
    parser.add_argument('--srt', type=Path)
    parser.add_argument('--lrc', type=Path)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    try:
        data = json.loads(args.timeline.read_text(encoding='utf-8'))
        expected = None if not args.expected_text else [x.strip() for x in args.expected_text.read_text(encoding='utf-8').splitlines() if x.strip()]
        result = validate(data, expected)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result['ok']:
            return 1
        if (args.srt or args.lrc) and not data.get('lines'):
            raise ValueError('no lines to export')
        outputs = [(path, fn(data['lines'])) for path, fn in [(args.srt, export_srt), (args.lrc, export_lrc)] if path]
        for path, _ in outputs:
            if path.exists() and not args.force:
                raise FileExistsError(f'{path} exists; use --force to replace it')
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
