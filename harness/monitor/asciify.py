"""Keep the dashboard HTML pure ASCII: browsers that guess Latin-1 still render it correctly.

Edit static/index.src.html (normal Vietnamese text), then rebuild the served page:
    .venv/bin/python -m harness.monitor.asciify            # writes static/index.html
    .venv/bin/python -m harness.monitor.asciify --check    # exit 1 if index.html is stale or non-ASCII
Non-ASCII becomes \\uXXXX inside <script>, a CSS escape inside <style>, and &#xHHHH; elsewhere.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BLOCK = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)|(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)


def _js(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if code < 128:
            out.append(ch)
        elif code <= 0xFFFF:
            out.append(f"\\u{code:04x}")
        else:
            code -= 0x10000
            out.append(f"\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}")
    return "".join(out)


def _css(text: str) -> str:
    return "".join(ch if ord(ch) < 128 else f"\\{ord(ch):06x}" for ch in text)


def _html(text: str) -> str:
    return "".join(ch if ord(ch) < 128 else f"&#x{ord(ch):x};" for ch in text)


def asciify(source: str) -> str:
    out, last = [], 0
    for match in BLOCK.finditer(source):
        out.append(_html(source[last:match.start()]))
        if match.group(1):
            out.append(match.group(1) + _js(match.group(2)) + match.group(3))
        else:
            out.append(match.group(4) + _css(match.group(5)) + match.group(6))
        last = match.end()
    out.append(_html(source[last:]))
    return "".join(out)


STATIC = Path(__file__).with_name("static")
SOURCE, TARGET = STATIC / "index.src.html", STATIC / "index.html"


def main(argv: list[str]) -> int:
    built = asciify(SOURCE.read_text(encoding="utf-8"))
    bad = sum(ord(c) > 127 for c in built)
    if bad:
        print(f"asciify left {bad} non-ASCII characters")
        return 1
    if "--check" in argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
        if current != built:
            print(f"{TARGET} is stale: run python -m harness.monitor.asciify")
            return 1
        return 0
    TARGET.write_text(built, encoding="ascii")
    print(f"{TARGET}: {len(built)} bytes, ASCII")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
