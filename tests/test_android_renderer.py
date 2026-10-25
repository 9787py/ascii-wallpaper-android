"""Desktop checks of the exact Python bridge included in the APK."""
import logging
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'android-try/app/src/main/python'))
from PIL import Image, TiffImagePlugin
import bgmaker
import img2ascii
from android_renderer import render, source_size, image_info


class AndroidRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.source = self.directory / '中文选图.png'
        image = Image.new('RGB', (24, 32), (25, 50, 100))
        image.save(self.source)
        image.close()

    def tearDown(self):
        logger = logging.getLogger('android-renderer')
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        self.temp.cleanup()

    def call(self, mode='natural', width=64, height=80, font_size=10):
        return render(str(self.source), str(self.directory / '输出.png'),
                      bgmaker.find_font()[1], width, height, font_size,
                      mode, 'contain', 'auto', True, str(self.directory))

    def test_all_algorithms_and_chinese_paths(self):
        for mode in img2ascii.MODES:
            with self.subTest(mode=mode):
                selected = self.call(mode)
                self.assertIn(selected, img2ascii.MODES)
                self.assertNotEqual(selected, 'auto')
                with Image.open(self.directory / '输出.png') as output:
                    self.assertEqual(output.size, (64, 80))

    def test_unsafe_output_size_fails_before_writing(self):
        for width, height in [(0, 80), (4001, 4000), (-1, 80)]:
            with self.subTest(size=(width, height)), self.assertRaises(ValueError):
                self.call(width=width, height=height)
        self.assertFalse((self.directory / '输出.png').exists())
        self.assertIn('render failed', (self.directory / 'renderer.log').read_text(encoding='utf-8'))

    def test_invalid_font_size_rejected(self):
        with self.assertRaises(ValueError):
            self.call(font_size=65)

    def test_source_size_and_native_resolution_render(self):
        width, height = source_size(self.source)
        self.assertEqual((width, height), (24, 32))
        self.call(width=width, height=height)
        with Image.open(self.directory / '输出.png') as output:
            self.assertEqual(output.size, (24, 32))

    def test_source_size_honors_exif_rotation(self):
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                path = self.directory / '旋转照片.jpg'
                with Image.new('RGB', (24, 32)) as image:
                    exif = Image.Exif()
                    exif[274] = orientation
                    image.save(path, exif=exif)
                expected = (32, 24) if orientation in (5, 6, 7, 8) else (24, 32)
                self.assertEqual(source_size(path), expected)

    def test_image_info_without_exif(self):
        original = self.source.read_bytes()
        info = image_info(self.source, '中文选图.png')
        self.assertIn('文件名：中文选图.png', info)
        self.assertIn('格式：PNG', info)
        self.assertIn('显示尺寸：24×32', info)
        self.assertIn('设备型号：未提供', info)
        self.assertIn('GPS 纬度：未提供', info)
        self.assertEqual(self.source.read_bytes(), original)

    def test_image_info_camera_exif_and_gps(self):
        rational = TiffImagePlugin.IFDRational
        path = self.directory / '拍摄照片.jpg'
        with Image.new('RGB', (24, 32)) as image:
            exif = Image.Exif()
            exif[271], exif[272], exif[274] = 'Example', 'Camera 1', 6
            exif[34665] = {
                36867: '2026:10:25 12:30:00', 36881: '+08:00',
                42036: 'Lens 35', 34855: 200, 33437: rational(28, 10),
                33434: rational(1, 125), 37386: rational(35),
            }
            exif[34853] = {
                1: 'S', 2: (rational(30), rational(30), rational(0)),
                3: 'W', 4: (rational(120), rational(15), rational(0)),
            }
            image.save(path, exif=exif)
        info = image_info(path)
        for expected in ['设备型号：Camera 1', '镜头：Lens 35', 'ISO：200',
                         '光圈：f/2.8', '快门：1/125 秒', '焦距：35 mm',
                         '显示尺寸：32×24', '+08:00',
                         'GPS 纬度：-30.500000°', 'GPS 经度：-120.250000°']:
            self.assertIn(expected, info)

    def test_invalid_exif_numbers_do_not_break_metadata(self):
        path = self.directory / '损坏参数.jpg'
        with Image.new('RGB', (24, 32)) as image:
            exif = Image.Exif()
            exif[34665] = {33434: TiffImagePlugin.IFDRational(0, 0)}
            exif[34853] = {1: 'N', 2: (91, 0, 0), 3: 'E', 4: (120, 0, 0)}
            image.save(path, exif=exif)
        info = image_info(path)
        self.assertIn('快门：数据无效', info)
        self.assertIn('GPS 纬度：数据无效或不完整', info)
        self.assertIn('存储尺寸：24×32', info)
