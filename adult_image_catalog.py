from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence, TypedDict

from PIL import ExifTags, Image, ImageOps


SUPPORTED_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

CONSENT_STATUSES = {"consented", "withdrawn", "restricted", "pending"}
AGE_RANGES = {"18-24", "25-34", "35-44", "45-54", "55+", "unknown"}
SKIN_VISIBILITY = {"low", "medium", "high", "not_recorded"}
GARMENT_POSITION = {"standard", "adjusted", "not_recorded"}
BODY_EXPOSURE_LEVEL = {"fully_clothed", "partial", "swimwear_or_underwear", "not_recorded"}
POSE = {"standing", "sitting", "reclining", "action", "not_recorded"}
SETTING = {"studio", "indoor", "outdoor", "not_recorded"}
LIGHTING = {"natural", "soft", "dramatic", "mixed", "not_recorded"}
BACKGROUND = {"plain", "textured", "environmental", "not_recorded"}
COLOR_PALETTE = {"neutral", "warm", "cool", "high_contrast", "not_recorded"}
IMAGE_QUALITY = {"draft", "standard", "high", "not_recorded"}
SUPPORTED_SORT_KEYS: tuple[str, ...] = (
    "age_range",
    "skin_visibility",
    "garment_position",
    "body_exposure_level",
    "pose",
    "setting",
    "lighting",
    "background",
    "color_palette",
    "image_quality",
    "consent_status",
    "filename",
    "orientation",
)
SORT_PRECEDENCE: dict[str, dict[str, int]] = {
    "age_range": {value: index for index, value in enumerate(["18-24", "25-34", "35-44", "45-54", "55+", "unknown"])},
    "skin_visibility": {value: index for index, value in enumerate(["low", "medium", "high", "not_recorded"])},
    "garment_position": {value: index for index, value in enumerate(["standard", "adjusted", "not_recorded"])},
    "body_exposure_level": {
        value: index for index, value in enumerate(["fully_clothed", "partial", "swimwear_or_underwear", "not_recorded"])
    },
    "pose": {value: index for index, value in enumerate(["standing", "sitting", "reclining", "action", "not_recorded"])},
    "setting": {value: index for index, value in enumerate(["studio", "indoor", "outdoor", "not_recorded"])},
    "lighting": {value: index for index, value in enumerate(["natural", "soft", "dramatic", "mixed", "not_recorded"])},
    "background": {value: index for index, value in enumerate(["plain", "textured", "environmental", "not_recorded"])},
    "color_palette": {value: index for index, value in enumerate(["neutral", "warm", "cool", "high_contrast", "not_recorded"])},
    "image_quality": {value: index for index, value in enumerate(["draft", "standard", "high", "not_recorded"])},
    "consent_status": {value: index for index, value in enumerate(["consented", "pending", "restricted", "withdrawn"])},
}
SAFE_EXIF_FIELDS = {
    "Orientation",
    "ColorSpace",
    "XResolution",
    "YResolution",
    "ResolutionUnit",
    "Compression",
}


class VisualMetadata(TypedDict):
    skin_visibility: Literal["low", "medium", "high", "not_recorded"]
    garment_position: Literal["standard", "adjusted", "not_recorded"]
    body_exposure_level: Literal["fully_clothed", "partial", "swimwear_or_underwear", "not_recorded"]
    age_range: Literal["18-24", "25-34", "35-44", "45-54", "55+", "unknown"]
    pose: Literal["standing", "sitting", "reclining", "action", "not_recorded"]
    setting: Literal["studio", "indoor", "outdoor", "not_recorded"]
    lighting: Literal["natural", "soft", "dramatic", "mixed", "not_recorded"]
    background: Literal["plain", "textured", "environmental", "not_recorded"]
    color_palette: Literal["neutral", "warm", "cool", "high_contrast", "not_recorded"]
    image_quality: Literal["draft", "standard", "high", "not_recorded"]


class TechnicalMetadata(TypedDict):
    filename: str
    mime_type: str
    width: int
    height: int
    orientation: Literal["landscape", "portrait", "square"]
    file_size_bytes: int
    sha256: str
    exif: dict[str, str]


class CatalogEntry(TypedDict):
    technical: TechnicalMetadata
    consent_status: Literal["consented", "withdrawn", "restricted", "pending"]
    metadata: VisualMetadata


@dataclass(frozen=True)
class CatalogFilters:
    consent_status: Literal["consented", "withdrawn", "restricted", "pending"] | None = None
    age_range: Literal["18-24", "25-34", "35-44", "45-54", "55+", "unknown"] | None = None
    skin_visibility: Literal["low", "medium", "high", "not_recorded"] | None = None
    garment_position: Literal["standard", "adjusted", "not_recorded"] | None = None
    body_exposure_level: Literal["fully_clothed", "partial", "swimwear_or_underwear", "not_recorded"] | None = None
    pose: Literal["standing", "sitting", "reclining", "action", "not_recorded"] | None = None
    setting: Literal["studio", "indoor", "outdoor", "not_recorded"] | None = None
    lighting: Literal["natural", "soft", "dramatic", "mixed", "not_recorded"] | None = None
    background: Literal["plain", "textured", "environmental", "not_recorded"] | None = None
    color_palette: Literal["neutral", "warm", "cool", "high_contrast", "not_recorded"] | None = None
    image_quality: Literal["draft", "standard", "high", "not_recorded"] | None = None


def _validate_choice(field: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        options = ", ".join(sorted(allowed))
        raise ValueError(f"Invalid {field!r}: {value!r}. Allowed values: {options}")


def _orientation(width: int, height: int) -> Literal["landscape", "portrait", "square"]:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _sanitize_exif(image: Image.Image) -> dict[str, str]:
    safe_exif: dict[str, str] = {}
    raw_exif = image.getexif()
    for key, value in raw_exif.items():
        field_name = ExifTags.TAGS.get(key, str(key))
        if field_name not in SAFE_EXIF_FIELDS:
            continue
        safe_exif[field_name] = str(value)
    return safe_exif


def _sha256_file(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_technical_metadata(image_path: str | Path) -> TechnicalMetadata:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.is_symlink():
        raise ValueError(f"Symlinked paths are not allowed: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported image type: {path.suffix}")

    with Image.open(path) as image:
        exif = _sanitize_exif(image)
        normalized_image = ImageOps.exif_transpose(image)
        width, height = normalized_image.size

    return {
        "filename": path.name,
        "mime_type": SUPPORTED_MIME_TYPES[suffix],
        "width": width,
        "height": height,
        "orientation": _orientation(width, height),
        "file_size_bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "exif": exif,
    }


def create_catalog_entry(
    image_path: str | Path,
    *,
    adult_confirmation: bool,
    consent_status: Literal["consented", "withdrawn", "restricted", "pending"],
    age_range: Literal["18-24", "25-34", "35-44", "45-54", "55+", "unknown"],
    skin_visibility: Literal["low", "medium", "high", "not_recorded"],
    garment_position: Literal["standard", "adjusted", "not_recorded"],
    body_exposure_level: Literal["fully_clothed", "partial", "swimwear_or_underwear", "not_recorded"],
    pose: Literal["standing", "sitting", "reclining", "action", "not_recorded"] = "not_recorded",
    setting: Literal["studio", "indoor", "outdoor", "not_recorded"] = "not_recorded",
    lighting: Literal["natural", "soft", "dramatic", "mixed", "not_recorded"] = "not_recorded",
    background: Literal["plain", "textured", "environmental", "not_recorded"] = "not_recorded",
    color_palette: Literal["neutral", "warm", "cool", "high_contrast", "not_recorded"] = "not_recorded",
    image_quality: Literal["draft", "standard", "high", "not_recorded"] = "not_recorded",
) -> CatalogEntry:
    """
    Create an adult-only catalog entry from user-provided metadata.

    This function does not infer age, nudity, body traits, or identity from pixels.
    Sensitive visual fields are controlled vocabularies entered by an authorized user.
    """
    if not adult_confirmation:
        raise ValueError("adult_confirmation must be True for adult-only cataloging")

    _validate_choice("consent_status", consent_status, CONSENT_STATUSES)

    _validate_choice("age_range", age_range, AGE_RANGES)
    _validate_choice("skin_visibility", skin_visibility, SKIN_VISIBILITY)
    _validate_choice("garment_position", garment_position, GARMENT_POSITION)
    _validate_choice("body_exposure_level", body_exposure_level, BODY_EXPOSURE_LEVEL)
    _validate_choice("pose", pose, POSE)
    _validate_choice("setting", setting, SETTING)
    _validate_choice("lighting", lighting, LIGHTING)
    _validate_choice("background", background, BACKGROUND)
    _validate_choice("color_palette", color_palette, COLOR_PALETTE)
    _validate_choice("image_quality", image_quality, IMAGE_QUALITY)

    technical = extract_technical_metadata(image_path)
    metadata: VisualMetadata = {
        "skin_visibility": skin_visibility,
        "garment_position": garment_position,
        "body_exposure_level": body_exposure_level,
        "age_range": age_range,
        "pose": pose,
        "setting": setting,
        "lighting": lighting,
        "background": background,
        "color_palette": color_palette,
        "image_quality": image_quality,
    }

    return {
        "technical": technical,
        "consent_status": consent_status,
        "metadata": metadata,
    }


def filter_catalog(entries: Iterable[CatalogEntry], *, filters: CatalogFilters) -> list[CatalogEntry]:
    """Filter catalog entries by exact metadata matches using deterministic rules."""
    if filters.consent_status is not None:
        _validate_choice("consent_status", filters.consent_status, CONSENT_STATUSES)
    if filters.age_range is not None:
        _validate_choice("age_range", filters.age_range, AGE_RANGES)
    if filters.skin_visibility is not None:
        _validate_choice("skin_visibility", filters.skin_visibility, SKIN_VISIBILITY)
    if filters.garment_position is not None:
        _validate_choice("garment_position", filters.garment_position, GARMENT_POSITION)
    if filters.body_exposure_level is not None:
        _validate_choice("body_exposure_level", filters.body_exposure_level, BODY_EXPOSURE_LEVEL)
    if filters.pose is not None:
        _validate_choice("pose", filters.pose, POSE)
    if filters.setting is not None:
        _validate_choice("setting", filters.setting, SETTING)
    if filters.lighting is not None:
        _validate_choice("lighting", filters.lighting, LIGHTING)
    if filters.background is not None:
        _validate_choice("background", filters.background, BACKGROUND)
    if filters.color_palette is not None:
        _validate_choice("color_palette", filters.color_palette, COLOR_PALETTE)
    if filters.image_quality is not None:
        _validate_choice("image_quality", filters.image_quality, IMAGE_QUALITY)

    filtered: list[CatalogEntry] = []
    for entry in entries:
        metadata = entry["metadata"]
        if filters.consent_status and entry["consent_status"] != filters.consent_status:
            continue
        if filters.age_range and metadata["age_range"] != filters.age_range:
            continue
        if filters.skin_visibility and metadata["skin_visibility"] != filters.skin_visibility:
            continue
        if filters.garment_position and metadata["garment_position"] != filters.garment_position:
            continue
        if filters.body_exposure_level and metadata["body_exposure_level"] != filters.body_exposure_level:
            continue
        if filters.pose and metadata["pose"] != filters.pose:
            continue
        if filters.setting and metadata["setting"] != filters.setting:
            continue
        if filters.lighting and metadata["lighting"] != filters.lighting:
            continue
        if filters.background and metadata["background"] != filters.background:
            continue
        if filters.color_palette and metadata["color_palette"] != filters.color_palette:
            continue
        if filters.image_quality and metadata["image_quality"] != filters.image_quality:
            continue
        filtered.append(entry)
    return filtered


def sort_catalog(
    entries: Iterable[CatalogEntry],
    *,
    keys: Sequence[str] = ("age_range", "skin_visibility", "body_exposure_level", "filename"),
) -> list[CatalogEntry]:
    """
    Deterministically sort catalog entries by selected metadata keys.

    Supported keys: age_range, skin_visibility, garment_position,
    body_exposure_level, pose, setting, lighting, background,
    color_palette, image_quality, consent_status, filename, orientation.
    """

    for key in keys:
        if key not in SUPPORTED_SORT_KEYS:
            raise ValueError(f"Unsupported sort key: {key}")

    def sort_key(entry: CatalogEntry) -> tuple[Any, ...]:
        values: list[Any] = []
        for key in keys:
            if key in {"filename", "orientation"}:
                raw_value = entry["technical"][key]
                if key == "filename":
                    values.append(raw_value.lower())
                else:
                    values.append(raw_value)
            else:
                if key == "consent_status":
                    raw_value = entry["consent_status"]
                else:
                    raw_value = entry["metadata"][key]
                precedence = SORT_PRECEDENCE.get(key)
                if precedence is None:
                    values.append(raw_value)
                else:
                    values.append(precedence[raw_value])
        return tuple(values)

    return sorted(entries, key=sort_key)
