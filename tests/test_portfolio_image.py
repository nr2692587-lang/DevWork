from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from portfolio_image import (
    CorruptImageError,
    InvalidImageInputError,
    UnsupportedImageFormatError,
    process_portfolio_image,
)

try:
    from PIL import Image, features
except ImportError as exc:  # pragma: no cover - test dependency failure is explicit
    raise RuntimeError("Pillow must be installed to run tests.") from exc


class ProcessPortfolioImageTests(unittest.TestCase):
    def test_processes_repository_jpeg_with_default_capture_metadata(self) -> None:
        image_path = (
            Path(__file__).resolve().parent.parent / "Capture1.JPG"
        )

        result = process_portfolio_image(
            image_path,
            max_size=(128, 128),
            extra_tags=["featured"],
        )

        self.assertEqual(result.source_format, "JPEG")
        self.assertEqual(result.original_dimensions, (192, 264))
        self.assertEqual(result.output_dimensions, (93, 128))
        self.assertIn("format:jpeg", result.tags)
        self.assertIn("orientation:portrait", result.tags)
        self.assertIn("featured", result.tags)
        self.assertEqual(result.metadata["color_mode"], "RGB")
        self.assertEqual(
            result.metadata["alt_text"],
            "Capture1.JPG: portrait-oriented jpeg portfolio image",
        )

    def test_processes_png_file_like_and_preserves_category_tag(self) -> None:
        image = Image.new("RGBA", (40, 20), color=(25, 50, 75, 128))
        buffer = BytesIO()
        buffer.name = "overlay.png"
        image.save(buffer, format="PNG")
        buffer.seek(0)

        result = process_portfolio_image(
            buffer,
            max_size=(20, 20),
            category="Portrait Session",
            extra_tags=["Client Select"],
        )

        self.assertEqual(result.source_format, "PNG")
        self.assertEqual(result.output_format, "PNG")
        self.assertEqual(result.source_size_bytes, len(buffer.getvalue()))
        self.assertEqual(result.output_dimensions, (20, 10))
        self.assertIn("category:portrait-session", result.tags)
        self.assertIn("client-select", result.tags)
        self.assertEqual(result.metadata["category"], "Portrait Session")

    @unittest.skipUnless(features.check("webp"), "WebP support is unavailable")
    def test_preserves_webp_output_by_default_when_supported(self) -> None:
        image = Image.new("RGB", (32, 16), color="purple")
        buffer = BytesIO()
        buffer.name = "sample.webp"
        image.save(buffer, format="WEBP")
        buffer.seek(0)

        result = process_portfolio_image(buffer)

        self.assertEqual(result.source_format, "WEBP")
        self.assertEqual(result.output_format, "WEBP")

    def test_uses_derivative_format_tag_for_tiff_conversion(self) -> None:
        image = Image.new("RGBA", (24, 12), color=(100, 50, 25, 128))
        buffer = BytesIO()
        buffer.name = "sample.tiff"
        image.save(buffer, format="TIFF")
        buffer.seek(0)

        result = process_portfolio_image(buffer)

        self.assertEqual(result.source_format, "TIFF")
        self.assertEqual(result.output_format, "PNG")
        self.assertIn("format:png", result.tags)

    def test_applies_exif_orientation_before_resizing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "rotated.jpg"
            image = Image.new("RGB", (90, 40), color="red")
            exif = Image.Exif()
            exif[274] = 6
            image.save(image_path, format="JPEG", exif=exif)

            result = process_portfolio_image(image_path, max_size=(80, 80))

        self.assertEqual(result.original_dimensions, (40, 90))
        self.assertEqual(result.output_dimensions, (36, 80))
        self.assertIn("orientation:portrait", result.tags)
        with Image.open(BytesIO(result.output_bytes)) as output_image:
            self.assertIsNone(output_image.getexif().get(274))

    def test_converts_palette_png_without_transparency_for_output(self) -> None:
        image = Image.new("P", (18, 18))
        image.putpalette([0, 0, 0, 255, 0, 0] + [0, 0, 0] * 254)
        buffer = BytesIO()
        buffer.name = "palette.png"
        image.save(buffer, format="PNG")
        buffer.seek(0)

        result = process_portfolio_image(buffer, output_format="PNG")

        with Image.open(BytesIO(result.output_bytes)) as output_image:
            self.assertEqual(output_image.mode, "RGB")
        self.assertEqual(result.output_format, "PNG")
        self.assertEqual(result.metadata["color_mode"], "RGB")
        self.assertEqual(result.metadata["source_color_mode"], "P")
        self.assertIn("mode:rgb", result.tags)

    def test_converts_palette_png_with_transparency_for_output(self) -> None:
        image = Image.new("P", (18, 18))
        image.putpalette([0, 0, 0, 255, 0, 0] + [0, 0, 0] * 254)
        image.info["transparency"] = 0
        buffer = BytesIO()
        buffer.name = "palette-alpha.png"
        image.save(buffer, format="PNG", transparency=0)
        buffer.seek(0)

        result = process_portfolio_image(buffer)

        with Image.open(BytesIO(result.output_bytes)) as output_image:
            self.assertEqual(output_image.mode, "RGBA")
        self.assertEqual(result.output_format, "PNG")
        self.assertEqual(result.metadata["color_mode"], "RGBA")
        self.assertEqual(result.metadata["source_color_mode"], "P")
        self.assertIn("mode:rgba", result.tags)

    def test_rejects_invalid_path(self) -> None:
        with self.assertRaises(InvalidImageInputError):
            process_portfolio_image("/does/not/exist.jpg")

    def test_rejects_unsupported_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.bmp"
            Image.new("RGB", (10, 10), color="blue").save(image_path, format="BMP")

            with self.assertRaises(UnsupportedImageFormatError):
                process_portfolio_image(image_path)

    def test_rejects_corrupt_image_data(self) -> None:
        buffer = BytesIO(b"not-an-image")
        buffer.name = "broken.jpg"

        with self.assertRaises(CorruptImageError):
            process_portfolio_image(buffer)

    def test_allows_file_like_objects_without_seekable_size(self) -> None:
        image = Image.new("RGB", (16, 8), color="green")
        data = BytesIO()
        image.save(data, format="PNG")
        payload = data.getvalue()

        class NonSeekableSizeBuffer(BytesIO):
            name = "stream.png"

            def seek(self, offset, whence=0):  # type: ignore[override]
                if whence == 2:
                    raise OSError("size unavailable")
                return super().seek(offset, whence)

        result = process_portfolio_image(NonSeekableSizeBuffer(payload))

        self.assertIsNone(result.source_size_bytes)
        self.assertEqual(result.source_format, "PNG")


if __name__ == "__main__":
    unittest.main()
