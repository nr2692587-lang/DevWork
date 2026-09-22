# DevWork

This repository contains a small Python utility for generating web-friendly
portfolio image derivatives and catalog metadata.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Usage

```python
from pathlib import Path

from portfolio_image import process_portfolio_image

result = process_portfolio_image(
    Path("Capture1.JPG"),
    output_path=Path("build/capture1-web.jpg"),
    max_size=(1280, 1280),
    category="portfolio",
    extra_tags=["featured"],
    description="Add a human-reviewed scene description here when needed.",
)

print(result.output_dimensions)
print(result.tags)
print(result.metadata["alt_text"])
```

## Notes

- Supported source formats: JPEG/JPG, PNG, TIFF, and WebP when Pillow provides
  the codec.
- EXIF orientation is normalized before derivative sizing.
- The utility does not infer scene content from pixels. For the bundled
  `Capture1.JPG`, the default metadata only includes technical facts that are
  safe to determine automatically; pass `description=` to supply a reviewed
  subject description for cataloging.
- Run tests with:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
