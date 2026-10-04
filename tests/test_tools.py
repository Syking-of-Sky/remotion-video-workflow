"""Behavior checks on synthetic local inputs; no personal assets or network APIs."""
import copy
from functools import partial
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import wave

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/remotion-video-workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
from timeline import validate, export_srt, export_lrc
from preview_server import make_server


def cli(name, *args):
    return subprocess.run([sys.executable, str(SCRIPTS/name), *map(str, args)], capture_output=True, text=True)


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.data = {'fps': 30, 'durationInFrames': 90,
                     'scenes': [{'id': 'one', 'startFrame': 0, 'durationInFrames': 30}, {'id': 'two', 'startFrame': 30, 'durationInFrames': 60}],
                     'lines': [{'start': .1, 'end': 1, 'text': '你好', 'words': [{'start': .1, 'end': .4, 'text': '你'}, {'start': .5, 'end': 1, 'text': '好'}]},
                               {'start': 1.2, 'end': 2.8, 'text': '你好'}]}

    def test_exact_repeated_text_and_gap_are_valid(self):
        self.assertTrue(validate(self.data, ['你好', '你好'])['ok'])
        self.assertFalse(validate(self.data, ['你好'])['ok'])

    def test_non_contiguous_scenes_fail(self):
        self.data['scenes'][1]['startFrame'] = 31
        self.assertFalse(validate(self.data)['ok'])

    def test_words_must_reconstruct_and_stay_inside_line(self):
        self.data['lines'][0]['words'][1]['end'] = 1.1
        self.assertFalse(validate(self.data)['ok'])
        self.data['lines'][0]['words'][1]['end'] = 1
        self.data['lines'][0]['words'][1]['text'] = '号'
        self.assertFalse(validate(self.data)['ok'])

    def test_overlap_nonfinite_and_audio_truncation_fail(self):
        for value in [-1, .8, float('nan'), float('inf')]:
            candidate = copy.deepcopy(self.data)
            candidate['lines'][1]['start'] = value
            self.assertFalse(validate(candidate)['ok'])
        self.data['audioDuration'] = 3.1
        self.assertFalse(validate(self.data)['ok'])

    def test_rational_fps_and_timestamp_carry(self):
        self.assertTrue(validate({'fps': '30000/1001', 'durationInFrames': 300})['ok'])
        line = [{'start': 59.9996, 'end': 61, 'text': '原创示例'}]
        self.assertIn('00:01:00,000 --> 00:01:01,000', export_srt(line))
        self.assertTrue(export_lrc(line).startswith('[01:00.00]'))
        with self.assertRaises(ValueError):
            export_srt([{'start': 0.0001, 'end': 0.0002, 'text': '字'}])

    def test_cli_preserves_text_and_refuses_implicit_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, output = folder/'timeline.json', folder/'captions.srt'
            source.write_text(json.dumps(self.data), encoding='utf-8')
            self.assertEqual(cli('timeline.py', source, '--srt', output).returncode, 0)
            self.assertEqual(output.read_text(encoding='utf-8').count('你好'), 2)
            self.assertNotEqual(cli('timeline.py', source, '--srt', output).returncode, 0)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg/FFprobe required')
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.still, cls.changing = cls.folder/'still.mp4', cls.folder/'changing.mp4'
        for filter_, dest in [('color=c=blue:s=64x48:r=10:d=0.6', cls.still), ('testsrc2=s=64x48:r=10:d=0.6', cls.changing)]:
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', filter_, '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(dest)], check=True)
        cls.tone = cls.folder/'tone.wav'
        rate = 8000
        with wave.open(str(cls.tone), 'wb') as output:
            output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            output.writeframes(b''.join(struct.pack('<h', 0 if i < rate//2 else int(10000*math.sin(i*math.tau*440/rate))) for i in range(rate)))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_decode_and_equal_endpoints_pass(self):
        result = cli('verify_video.py', self.still, '--width', 64, '--height', 48, '--fps', 10, '--frames', 6, '--audio', 'absent', '--exact-loop')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['full_decode'])
        self.assertEqual(report['encoded_boundaries']['different_pixels'], 0)

    def test_changing_endpoints_fail(self):
        result = cli('verify_video.py', self.changing, '--exact-loop')
        self.assertEqual(result.returncode, 1)
        self.assertGreater(json.loads(result.stdout)['encoded_boundaries']['different_pixels'], 0)

    def test_expected_audio_and_wrong_frame_count_fail(self):
        self.assertEqual(cli('verify_video.py', self.still, '--audio', 'required').returncode, 1)
        self.assertEqual(cli('verify_video.py', self.still, '--frames', 7).returncode, 1)

    def test_corrupt_container_is_not_success(self):
        bad = self.folder/'bad.mp4'
        bad.write_bytes(self.still.read_bytes()[:70])
        self.assertEqual(cli('verify_video.py', bad).returncode, 1)

    def test_audio_envelope_does_not_invent_bpm(self):
        output = self.folder/'audio.json'
        result = cli('analyze_audio.py', self.tone, '--output', output, '--sample-rate', 8000, '--hop', 400)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(output.read_text())
        self.assertEqual(data['beatSource'], 'not_estimated')
        self.assertEqual(data['beats'], [])
        self.assertEqual(data['rms'][0]['rms'], 0)
        self.assertGreater(data['rms'][-1]['rms'], .1)
        result = cli('analyze_audio.py', self.tone, '--output', output, '--bpm', 120, '--force')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text())['beats'], [0, .5])

    def test_source_png_difference_is_detected(self):
        from PIL import Image
        first, last = self.folder/'first.png', self.folder/'last.png'
        a = Image.new('RGB', (8, 8), 'white')
        a.save(first)
        a.putpixel((0, 0), (0, 0, 0))
        a.save(last)
        result = cli('verify_video.py', self.still, '--source-first', first, '--source-last', last)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['source_boundaries']['different_pixels'], 1)


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)/'output'
        cls.root.mkdir()
        (cls.root/'demo.mp4').write_bytes(b'0123456789')
        cls.server = make_server(cls.root, 0)
        cls.thread = threading.Thread(target=partial(cls.server.serve_forever, poll_interval=.02), daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def test_range_body_suffix_and_head(self):
        for header, expected in [('bytes=2-5', b'2345'), ('bytes=-2', b'89'), ('bytes=8-', b'89')]:
            with urlopen(Request(self.base+'/demo.mp4', headers={'Range': header})) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), expected)
                self.assertEqual(int(response.headers['Content-Length']), len(expected))
        with urlopen(Request(self.base+'/demo.mp4', headers={'Range':'bytes=2-5'}, method='HEAD')) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), b'')
            self.assertEqual(response.headers['Content-Range'], 'bytes 2-5/10')

    def test_unsatisfied_range_and_symlink_escape(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/demo.mp4', headers={'Range':'bytes=20-'}))
        self.assertEqual(caught.exception.code, 416)
        outside = Path(self.temp.name)/'outside.txt'
        outside.write_text('not for serving')
        link = self.root/'outside.txt'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('symlink creation unsupported')
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base+'/outside.txt')
        self.assertEqual(caught.exception.code, 403)


class FontTests(unittest.TestCase):
    def test_subset_and_missing_glyph(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.ttLib import TTFont
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            builder = FontBuilder(1000, isTTF=True)
            names = ['.notdef', 'A', 'uni4E00']
            builder.setupGlyphOrder(names)
            builder.setupCharacterMap({65:'A', 0x4e00:'uni4E00'})
            glyphs = {}
            for name in names:
                pen = TTGlyphPen(None)
                pen.moveTo((60, 0)); pen.lineTo((300, 600)); pen.lineTo((540, 0)); pen.closePath()
                glyphs[name] = pen.glyph()
            builder.setupGlyf(glyphs)
            builder.setupHorizontalMetrics({name:(600, 0) for name in names})
            builder.setupHorizontalHeader(ascent=800, descent=-200)
            builder.setupNameTable({'familyName':'Synthetic Test', 'styleName':'Regular'})
            builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
            builder.setupPost()
            source, text, output = folder/'source.ttf', folder/'text.txt', folder/'subset.ttf'
            builder.save(source)
            text.write_text('A一', encoding='utf-8')
            result = cli('font_subset.py', '--font', source, '--text', text, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            with TTFont(output) as font:
                self.assertIn(0x4e00, font.getBestCmap())
            text.write_text('B', encoding='utf-8')
            result = cli('font_subset.py', '--font', source, '--text', text, '--output', folder/'bad.ttf')
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['missing'], ['B'])
            self.assertFalse((folder/'bad.ttf').exists())


if __name__ == '__main__':
    unittest.main()
