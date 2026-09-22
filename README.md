# Adult-Only Image Cataloging Tool

This repository provides a **consent-aware, adult-only** image cataloging module for private photography collections.

## Safety and policy constraints

- Cataloging is allowed only when `adult_confirmation=True`.
- Cataloging also requires an explicit `consent_status` value (`consented`, `withdrawn`, `restricted`, or `pending`).
- The tool **does not** infer age or identity from images.
- Sensitive fields are controlled vocabularies entered/reviewed by an authorized user.
- The implementation does **not** include face recognition, age estimation, attractiveness scoring, or automated body/skin/nudity classification.

## Supported image formats

- `.jpg`, `.jpeg` (case-insensitive, including `.JPG` / `.JPEG`)
- `.png`
- `.webp`
- `.tif`, `.tiff`

## What metadata is extracted automatically

`extract_technical_metadata()` returns non-sensitive technical metadata:

- filename
- MIME type
- dimensions
- orientation
- file size
- SHA-256 hash
- EXIF fields with `GPSInfo` and `MakerNote` omitted by default

## Example usage (adult-only + consent-aware)

```python
from adult_image_catalog import (
    CatalogFilters,
    create_catalog_entry,
    filter_catalog,
    sort_catalog,
)

entry = create_catalog_entry(
    "/absolute/path/to/adult_photo.JPG",
    adult_confirmation=True,
    consent_status="consented",
    age_range="25-34",           # caller-provided, not inferred
    skin_visibility="medium",    # controlled vocabulary
    garment_position="standard", # controlled vocabulary
    body_exposure_level="partial",
    pose="standing",
    setting="studio",
    lighting="soft",
    background="plain",
    color_palette="neutral",
    image_quality="high",
)

entries = [entry]

filtered = filter_catalog(
    entries,
    filters=CatalogFilters(age_range="25-34", setting="studio"),
)

sorted_entries = sort_catalog(
    filtered,
    keys=("age_range", "skin_visibility", "filename"),
)
```

## Running tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```
