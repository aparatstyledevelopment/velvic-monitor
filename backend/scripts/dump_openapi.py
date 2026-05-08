"""Dump the FastAPI OpenAPI schema to a JSON file.

Usage:
    python scripts/dump_openapi.py [output_path]

Used by `make openapi` to keep `shared/openapi/spec.json` in sync with the
running backend before regenerating TypeScript types.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import create_app


def main(out_path: Path) -> None:
    spec = create_app().openapi()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    target = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../shared/openapi/spec.json")
    )
    main(target)
