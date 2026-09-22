from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import ExifTags, Image

from adult_image_catalog import (
    CatalogFilters,
    _sanitize_exif,
    create_catalog_entry,
    extract_technical_metadata,
    filter_catalog,
    sort_catalog,
)


class FakeImage:
    def __init__(self, exif: dict[int, str]) -> None:
        self._exif = exif

    def getexif(self) -> dict[int, str]:
        return self._exif


class AdultImageCatalogTests(unittest.TestCase):
    def test_extract_metadata_accepts_uppercase_jpg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "Sample.JPG"
            Image.new("RGB", (20, 10), color="white").save(image_path)

            metadata = extract_technical_metadata(image_path)

        self.assertEqual(metadata["mime_type"], "image/jpeg")
        self.assertEqual(metadata["orientation"], "landscape")
        self.assertEqual(metadata["filename"], "Sample.JPG")
        self.assertEqual(len(metadata["sha256"]), 64)

    def test_catalog_requires_adult_confirmation_and_valid_consent_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "adult.jpeg"
            Image.new("RGB", (10, 20), color="black").save(image_path)

            with self.assertRaisesRegex(ValueError, "adult_confirmation"):
                create_catalog_entry(
                    image_path,
                    adult_confirmation=False,
                    consent_status="consented",
                    age_range="25-34",
                    skin_visibility="low",
                    garment_position="standard",
                    body_exposure_level="fully_clothed",
                )

            with self.assertRaisesRegex(ValueError, "consent_status"):
                create_catalog_entry(
                    image_path,
                    adult_confirmation=True,
                    consent_status="invalid",  # type: ignore[arg-type]
                    age_range="25-34",
                    skin_visibility="low",
                    garment_position="standard",
                    body_exposure_level="fully_clothed",
                )

            pending_entry = create_catalog_entry(
                image_path,
                adult_confirmation=True,
                consent_status="pending",
                age_range="25-34",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )
            self.assertEqual(pending_entry["consent_status"], "pending")

    def test_sanitize_exif_omits_gps_and_makernote(self) -> None:
        tags_by_name = {name: key for key, name in ExifTags.TAGS.items()}
        fake_image = FakeImage(
            {
                tags_by_name["GPSInfo"]: "gps-data",
                tags_by_name["MakerNote"]: "maker-note",
                tags_by_name["Artist"]: "authorized user",
            }
        )

        safe_exif = _sanitize_exif(fake_image)  # type: ignore[arg-type]

        self.assertNotIn("GPSInfo", safe_exif)
        self.assertNotIn("MakerNote", safe_exif)
        self.assertEqual(safe_exif["Artist"], "authorized user")

    def test_filter_and_sort_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "b.jpg"
            p2 = Path(tmp) / "a.jpg"
            Image.new("RGB", (10, 10), color="blue").save(p1)
            Image.new("RGB", (10, 10), color="green").save(p2)

            e1 = create_catalog_entry(
                p1,
                adult_confirmation=True,
                consent_status="consented",
                age_range="35-44",
                skin_visibility="high",
                garment_position="adjusted",
                body_exposure_level="partial",
                pose="standing",
                setting="studio",
            )
            e2 = create_catalog_entry(
                p2,
                adult_confirmation=True,
                consent_status="consented",
                age_range="25-34",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
                pose="sitting",
                setting="indoor",
            )

        filtered = filter_catalog(
            [e1, e2],
            filters=CatalogFilters(age_range="25-34", skin_visibility="low"),
        )
        sorted_entries = sort_catalog([e1, e2], keys=("age_range", "filename"))

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["technical"]["filename"], "a.jpg")
        self.assertEqual([e["technical"]["filename"] for e in sorted_entries], ["a.jpg", "b.jpg"])

    def test_sort_catalog_rejects_unsupported_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "adult.jpg"
            Image.new("RGB", (10, 10), color="white").save(image_path)
            entry = create_catalog_entry(
                image_path,
                adult_confirmation=True,
                consent_status="consented",
                age_range="25-34",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )

        with self.assertRaisesRegex(ValueError, "Unsupported sort key"):
            sort_catalog([entry], keys=("unsupported_key",))

    def test_sort_catalog_default_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "z.jpg"
            p2 = Path(tmp) / "a.jpg"
            Image.new("RGB", (10, 10), color="red").save(p1)
            Image.new("RGB", (10, 10), color="yellow").save(p2)

            e1 = create_catalog_entry(
                p1,
                adult_confirmation=True,
                consent_status="consented",
                age_range="35-44",
                skin_visibility="medium",
                garment_position="standard",
                body_exposure_level="partial",
            )
            e2 = create_catalog_entry(
                p2,
                adult_confirmation=True,
                consent_status="consented",
                age_range="25-34",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )

        ordered = sort_catalog([e1, e2])
        self.assertEqual([e["technical"]["filename"] for e in ordered], ["a.jpg", "z.jpg"])
        self.assertEqual([e["metadata"]["age_range"] for e in ordered], ["25-34", "35-44"])

    def test_filter_catalog_rejects_invalid_filter_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "adult.jpg"
            Image.new("RGB", (10, 10), color="white").save(image_path)
            entry = create_catalog_entry(
                image_path,
                adult_confirmation=True,
                consent_status="consented",
                age_range="25-34",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )

        with self.assertRaisesRegex(ValueError, "Invalid 'age_range'"):
            filter_catalog(  # type: ignore[arg-type]
                [entry],
                filters=CatalogFilters(age_range="invalid"),
            )

    def test_sort_catalog_uses_controlled_vocabulary_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.jpg"
            p2 = Path(tmp) / "z.jpg"
            Image.new("RGB", (10, 10), color="purple").save(p1)
            Image.new("RGB", (10, 10), color="orange").save(p2)

            younger = create_catalog_entry(
                p2,
                adult_confirmation=True,
                consent_status="consented",
                age_range="18-24",
                skin_visibility="high",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )
            unknown = create_catalog_entry(
                p1,
                adult_confirmation=True,
                consent_status="consented",
                age_range="unknown",
                skin_visibility="low",
                garment_position="standard",
                body_exposure_level="fully_clothed",
            )

        ordered = sort_catalog([unknown, younger], keys=("age_range",))
        self.assertEqual([e["metadata"]["age_range"] for e in ordered], ["18-24", "unknown"])


if __name__ == "__main__":
    unittest.main()
