"""Quick URL validation checks (no network required for most cases)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from url_utils import UrlValidationError, validate_url


CASES = [
    ("https://example.com/page", True),
    ("example.com/page", True),  # scheme added
    ("", False),
    ("ftp://example.com", False),
    ("javascript:alert(1)", False),
    ("http://localhost/secret", False),
    ("not a url", False),
]


def main() -> None:
    failed = 0
    for value, should_pass in CASES:
        try:
            out = validate_url(value)
            ok = should_pass
            print(f"PASS expected={should_pass} input={value!r} -> {out}")
            if not ok:
                failed += 1
                print("  but should have failed")
        except UrlValidationError as exc:
            ok = not should_pass
            print(f"{'PASS' if ok else 'FAIL'} expected={should_pass} input={value!r} err={exc}")
            if not ok:
                failed += 1

    if failed:
        raise SystemExit(f"{failed} case(s) failed")
    print("url validation checks passed")


if __name__ == "__main__":
    main()
