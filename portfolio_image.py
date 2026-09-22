from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable, Union

ImageInput = Union[str, Path, BinaryIO]

SUPPORTED_INPUT_FORMATS = {"JPEG", "PNG", "TIFF", "WEBP"}
SUPPORTED_OUTPUT_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageProcessingError(Exception):
    """Base exception for portfolio image processing errors."""


class MissingImageDependencyError(ImageProcessingError):
    """Raised when Pillow or an optional image codec is unavailable."""


class InvalidImageInputError(ImageProcessingError):
    """Raised when an input path or file-like object is invalid."""


class UnsupportedImageFormatError(ImageProcessingError):
    """Raised when an image format is not supported by this utility."""


class CorruptImageError(ImageProcessingError):
    """Raised when an image cannot be decoded successfully."""


class OutputImageError(ImageProcessingError):
    """Raised when a derivative image cannot be encoded or written."""


@dataclass(frozen=True)
class ProcessedPortfolioImage:
    source_name: str | None
    source_format: str
    source_size_bytes: int | None
    original_dimensions: tuple[int, int]
    output_format: str
    output_dimensions: tuple[int, int]
    output_size_bytes: int
    tags: tuple[str, ...]
    metadata: dict[str, str]
    output_bytes: bytes
    output_path: str | None


def process_portfolio_image(
    image_input: ImageInput,
    *,
    output_path: str | Path | None = None,
    max_size: tuple[int, int] = (1280, 1280),
    output_format: str | None = None,
    quality: int = 85,
    description: str | None = None,
    extra_tags: Iterable[str] | None = None,
    category: str | None = None,
) -> ProcessedPortfolioImage:
    """
    Create a web-friendly derivative for a portfolio image without altering the source.

    The function accepts a filesystem path or a binary file-like object, applies EXIF
    orientation when present, resizes the image to fit within ``max_size``, and
    returns the derivative bytes together with catalog metadata and tags.
    """

    image_module = _load_pillow()
    Image = image_module["Image"]
    ImageOps = image_module["ImageOps"]
    UnidentifiedImageError = image_module["UnidentifiedImageError"]
    features = image_module["features"]

    source, source_name, source_size = _open_source(image_input)

    try:
        with Image.open(source) as opened_image:
            source_format = (opened_image.format or "").upper()
            if source_format not in SUPPORTED_INPUT_FORMATS:
                raise UnsupportedImageFormatError(
                    f"Unsupported image format: {source_format or 'unknown'}"
                )

            normalized = ImageOps.exif_transpose(opened_image)
            original_dimensions = normalized.size
            derivative = normalized.copy()
            derivative.thumbnail(max_size, Image.Resampling.LANCZOS)

            chosen_output_format = _choose_output_format(
                requested_format=output_format,
                source_format=source_format,
                source_image=normalized,
                features=features,
            )
            prepared = _prepare_for_output(derivative, chosen_output_format)
    except FileNotFoundError as exc:
        raise InvalidImageInputError(f"Image path does not exist: {image_input}") from exc
    except UnidentifiedImageError as exc:
        raise CorruptImageError("Unable to decode image data.") from exc
    except OSError as exc:
        raise CorruptImageError("Image file appears to be corrupt or unreadable.") from exc
    finally:
        if source is not image_input and hasattr(source, "close"):
            source.close()

    try:
        buffer = BytesIO()
        _ensure_output_codec_available(chosen_output_format, features)
        save_kwargs = _build_save_kwargs(chosen_output_format, quality)
        prepared.save(buffer, format=chosen_output_format, **save_kwargs)
    except OSError as exc:
        raise OutputImageError("Unable to encode derivative image output.") from exc

    output_bytes = buffer.getvalue()
    resolved_output_path = _write_output(output_bytes, output_path)
    tags = _generate_tags(
        source_format=source_format,
        image_mode=prepared.mode,
        dimensions=normalized.size,
        extra_tags=extra_tags,
        category=category,
    )
    metadata = _build_metadata(
        source_name=source_name,
        source_format=source_format,
        dimensions=normalized.size,
        color_mode=prepared.mode,
        source_color_mode=normalized.mode,
        description=description,
        category=category,
    )

    return ProcessedPortfolioImage(
        source_name=source_name,
        source_format=source_format,
        source_size_bytes=source_size,
        original_dimensions=original_dimensions,
        output_format=chosen_output_format,
        output_dimensions=prepared.size,
        output_size_bytes=len(output_bytes),
        tags=tags,
        metadata=metadata,
        output_bytes=output_bytes,
        output_path=resolved_output_path,
    )


def _load_pillow() -> dict[str, object]:
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError, features
    except ImportError as exc:
        raise MissingImageDependencyError(
            "Pillow is required to process portfolio images. "
            "Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    return {
        "Image": Image,
        "ImageOps": ImageOps,
        "UnidentifiedImageError": UnidentifiedImageError,
        "features": features,
    }


def _open_source(image_input: ImageInput) -> tuple[BinaryIO, str | None, int | None]:
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise InvalidImageInputError(f"Image path does not exist: {path}")
        return path.open("rb"), path.name, path.stat().st_size

    if hasattr(image_input, "read"):
        source_name = getattr(image_input, "name", None)
        return image_input, _basename(source_name), _file_like_size(image_input)

    raise InvalidImageInputError(
        "image_input must be a filesystem path or a binary file-like object."
    )


def _basename(source_name: object) -> str | None:
    if not source_name:
        return None
    return Path(str(source_name)).name


def _file_like_size(file_object: BinaryIO) -> int | None:
    if not hasattr(file_object, "tell") or not hasattr(file_object, "seek"):
        return None

    try:
        current_position = file_object.tell()
        file_object.seek(0, 2)
        size = file_object.tell()
        file_object.seek(current_position)
        return size
    except OSError:
        return None


def _choose_output_format(
    *, requested_format: str | None, source_format: str, source_image, features
) -> str:
    if requested_format:
        chosen = requested_format.upper()
    elif source_format in SUPPORTED_OUTPUT_FORMATS:
        chosen = source_format
    elif _has_alpha(source_image):
        chosen = "PNG"
    else:
        chosen = "JPEG"

    if chosen not in SUPPORTED_OUTPUT_FORMATS:
        raise UnsupportedImageFormatError(f"Unsupported output format: {chosen}")

    if chosen == "WEBP" and not features.check("webp"):
        raise MissingImageDependencyError(
            "This Pillow build does not include WebP support."
        )

    return chosen


def _has_alpha(image) -> bool:
    return image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )


def _prepare_for_output(image, output_format: str):
    if output_format == "JPEG" and image.mode not in {"RGB", "L"}:
        return image.convert("RGB")

    if output_format in {"PNG", "WEBP"} and image.mode == "P":
        return image.convert("RGBA" if "transparency" in image.info else "RGB")

    return image


def _build_save_kwargs(output_format: str, quality: int) -> dict[str, object]:
    if output_format == "JPEG":
        return {"quality": quality, "optimize": True}

    if output_format == "WEBP":
        return {"quality": quality, "method": 6}

    return {"optimize": True}


def _ensure_output_codec_available(output_format: str, features) -> None:
    codec_checks = {
        "JPEG": lambda: features.check_codec("jpg"),
        "PNG": lambda: features.check_codec("zlib"),
        "WEBP": lambda: features.check("webp"),
    }
    checker = codec_checks.get(output_format)
    if checker and not checker():
        raise MissingImageDependencyError(
            f"This Pillow build does not include {output_format} output support."
        )


def _write_output(output_bytes: bytes, output_path: str | Path | None) -> str | None:
    if output_path is None:
        return None

    try:
        resolved = Path(output_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(output_bytes)
        return str(resolved)
    except OSError as exc:
        raise OutputImageError("Unable to write derivative image output.") from exc


def _generate_tags(
    *,
    source_format: str,
    image_mode: str,
    dimensions: tuple[int, int],
    extra_tags: Iterable[str] | None,
    category: str | None,
) -> tuple[str, ...]:
    tags = {
        "portfolio",
        f"format:{source_format.lower()}",
        f"orientation:{_orientation(dimensions)}",
        f"mode:{image_mode.lower()}",
    }

    if category:
        tags.add(f"category:{_slugify(category)}")

    if extra_tags:
        for tag in extra_tags:
            if tag:
                tags.add(_slugify(tag))

    return tuple(sorted(tags))


def _build_metadata(
    *,
    source_name: str | None,
    source_format: str,
    dimensions: tuple[int, int],
    color_mode: str,
    source_color_mode: str,
    description: str | None,
    category: str | None,
) -> dict[str, str]:
    orientation = _orientation(dimensions)
    stem = Path(source_name).stem if source_name else "portfolio-image"
    metadata = {
        "title": stem.replace("_", " ").replace("-", " ").strip() or "portfolio-image",
        "alt_text": description
        or _default_description(
            source_name=source_name,
            source_format=source_format,
            orientation=orientation,
        ),
        "orientation": orientation,
        "color_mode": color_mode,
        "source_color_mode": source_color_mode,
    }

    if category:
        metadata["category"] = category

    return metadata


def _default_description(
    *, source_name: str | None, source_format: str, orientation: str
) -> str:
    if source_name:
        return (
            f"{source_name}: {orientation}-oriented "
            f"{source_format.lower()} portfolio image"
        )

    return f"{orientation.title()} {source_format.lower()} portfolio image"


def _orientation(dimensions: tuple[int, int]) -> str:
    width, height = dimensions
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _slugify(value: str) -> str:
    compact = "-".join(value.strip().lower().split())
    return "".join(character for character in compact if character.isalnum() or character in {"-", ":"})
