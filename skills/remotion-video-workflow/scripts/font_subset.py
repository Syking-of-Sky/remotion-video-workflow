#!/usr/bin/env python3
"""Check actual caption glyphs before creating a redistributable font subset."""
import argparse
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font', type=Path, required=True)
    p.add_argument('--text', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    try:
        from fontTools.ttLib import TTFont
        from fontTools import subset
        if args.output.resolve() == args.font.resolve():
            raise ValueError('output must not replace the source font')
        if args.output.exists() and not args.force:
            raise FileExistsError('output exists; use --force to replace it')
        text = '\n'.join(path.read_text(encoding='utf-8') for path in args.text)
        with TTFont(args.font) as font:
            cmap = font.getBestCmap() or {}
            missing = sorted({c for c in text if not c.isspace() and ord(c) not in cmap})
            if missing:
                print(json.dumps({'ok': False, 'missing': missing}, ensure_ascii=False))
                return 1
            options = subset.Options()
            options.name_IDs = ['*']
            options.name_legacy = True
            options.name_languages = ['*']
            task = subset.Subsetter(options=options)
            task.populate(text=text)
            task.subset(font)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            font.save(args.output)
        print(json.dumps({'ok': True, 'missing': [], 'output': args.output.name}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, ImportError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
