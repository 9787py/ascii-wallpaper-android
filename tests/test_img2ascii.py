import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))

from PIL import Image, ImageFont

import bgmaker
import img2ascii


class ImageToAsciiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cls.temp.close()
        image = Image.new("RGB", (48, 32))
        image.putdata([
            ((x * 5 + y) % 256, (x + y * 7) % 256, (x * 3 + y * 2) % 256)
            for y in range(32) for x in range(48)
        ])
        image.save(cls.temp.name)
        cls.font = ImageFont.truetype(bgmaker.find_font()[1], 10)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.temp.name)

    def test_every_render_mode_returns_requested_canvas(self):
        for mode in img2ascii.MODES:
            with self.subTest(mode=mode):
                result = img2ascii.ascii_image(
                    self.temp.name, self.font, (96, 54), (0, 0, 0), mode)
                self.assertEqual(result.size, (96, 54))
                self.assertEqual(result.mode, "RGB")

    def test_clahe_handles_small_and_odd_dimensions(self):
        for size in ((1, 1), (3, 9), (9, 3), (17, 31)):
            with self.subTest(size=size):
                self.assertEqual(
                    img2ascii.clahe(Image.new("L", size, 20)).size, size)

    def test_uniform_density_can_remain_blank(self):
        result = img2ascii.adaptive_density(Image.new("L", (8, 8), 42))
        self.assertEqual(result.getextrema(), (0, 0))

    def test_auto_recommends_an_existing_conventional_mode(self):
        self.assertIn(img2ascii.recommend_mode(self.temp.name), {
            "natural", "shadow2", "retinex", "edge", "structure"})

    def test_fit_modes_preserve_requested_grid(self):
        source = Image.new("RGB", (20, 40), "red")
        for fit in img2ascii.FIT_MODES:
            with self.subTest(fit=fit):
                result = img2ascii.fit_source(
                    source, (80, 40), (0, 0, 0), fit, sample_aspect=1)
                self.assertEqual(result.size, (80, 40))

    def test_auto_fit_avoids_large_aspect_crop(self):
        self.assertEqual(
            img2ascii.resolve_fit((400, 100), (100, 100), "auto"),
            "contain")
        self.assertEqual(
            img2ascii.resolve_fit((160, 90), (160, 90), "auto"),
            "cover")

    def test_unicode_source_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "中文图片.png")
            Image.new("RGB", (24, 16), "navy").save(path)
            result = img2ascii.ascii_image(
                path, self.font, (96, 54), (0, 0, 0), "natural")
            self.assertEqual(result.size, (96, 54))


if __name__ == "__main__":
    unittest.main()
