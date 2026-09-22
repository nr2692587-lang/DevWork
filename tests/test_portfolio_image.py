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
    from PIL import Image
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
        self.assertIn("portrait-oriented jpeg", result.metadata["alt_text"].lower())

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

    def test_applies_exif_orientation_before_resizing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "rotated.jpg"
            image = Image.new("RGB", (90, 40), color="red")
            exif = Image.Exif()
            exif[274] = 6
            image.save(image_path, format="JPEG", exif=exif)

            result = process_portfolio_image(image_path, max_size=(80, 80))

        self.assertEqual(result.original_dimensions, (90, 40))
        self.assertEqual(result.output_dimensions, (36, 80))
        self.assertIn("orientation:portrait", result.tags)

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


if __name__ == "__main__":
    unittest.main()
