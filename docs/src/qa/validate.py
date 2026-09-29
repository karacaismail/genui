#!/usr/bin/env python3
"""Static checks for the built requirements page.

Usage: python3 docs/src/qa/validate.py docs/genui-frontend-gereksinimleri.html

Checks: balanced tags, duplicate ids, local #fragment links that point nowhere,
requirement rows with a phase, and the inline script's syntax (needs `node`).
Exits 1 on any failure. These checks cover the document only; they do not run
the identity integration tests AT-18–AT-25.
"""
import collections
import html.parser
import pathlib
import re
import subprocess
import sys
import tempfile

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
        "path", "line", "rect", "circle", "polyline", "polygon", "ellipse", "stop", "use"}


class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors, self.hrefs = [], [], []
        self.ids = collections.Counter()

    def _attrs(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids[d["id"]] += 1
        if tag == "a" and d.get("href", "").startswith("#") and len(d["href"]) > 1:
            self.hrefs.append(d["href"][1:])

    def handle_starttag(self, tag, attrs):
        self._attrs(tag, attrs)
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        self._attrs(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"extra </{tag}> at {self.getpos()}")
            return
        top, pos = self.stack.pop()
        if top != tag:
            self.errors.append(f"<{top}> opened at {pos} closed by </{tag}> at {self.getpos()}")


def main(path):
    src = pathlib.Path(path).read_text(encoding="utf-8")
    p = Parser()
    p.feed(src)
    results = []
    results.append(("tags balanced", not p.errors and not p.stack, "; ".join(p.errors[:3]) or str(p.stack[:3])))
    dups = sorted(k for k, v in p.ids.items() if v > 1)
    results.append(("no duplicate ids", not dups, " ".join(dups)))
    missing = sorted({h for h in p.hrefs if h not in p.ids})
    results.append(("local links resolve", not missing, " ".join(missing)))
    # every requirement row is found independently of its phase attribute, then each must carry a valid phase
    req_rows = re.findall(r'<tr id="([A-M]\d{1,2})"([^>]*)>', src)
    bad = [rid for rid, attrs in req_rows if not re.search(r'\bdata-phase="0[1-4]"', attrs)]
    results.append(("every requirement row carries a valid phase", len(req_rows) > 0 and not bad,
                    f"{len(req_rows)} rows; missing or invalid: {' '.join(bad)}" if bad else f"{len(req_rows)} rows"))
    scripts = re.findall(r"<script>(.*?)</script>", src, re.S)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(scripts[-1] if scripts else "")
    try:
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        results.append(("inline script syntax", r.returncode == 0, r.stderr.strip()[:200]))
    except FileNotFoundError:
        results.append(("inline script syntax", None, "node not found"))
    failed = False
    for name, ok, detail in results:
        status = "not_run" if ok is None else "pass" if ok else "fail"
        failed |= ok is False
        print(f"{status:7} {name}" + (f" — {detail}" if detail and status != "pass" else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/genui-frontend-gereksinimleri.html"))
