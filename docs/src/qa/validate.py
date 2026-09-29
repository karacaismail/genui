#!/usr/bin/env python3
"""Static checks for the built requirements page.

Usage: python3 docs/src/qa/validate.py docs/genui-frontend-gereksinimleri.html

Checks: balanced tags, duplicate ids, local #fragment links that point nowhere, requirement rows
with a valid slice (dilim 1-4), sub-scopes that match the row's slices, every MUST row linked to a test,
full 64-digit fingerprints in the contract appendix, an approval state on every conflict record, every AT-xx and TP-xx mention
resolving to an experiment or test suite, every acronym defined in the glossary, the closed-findings
regression list (docs/src/qa/kapanan-bulgular.json), and the inline script's syntax (needs `node`).
Exits 1 on any failure. These checks cover the document only; they do not run the product's tests
or the identity integration tests.
"""
import collections
import html
import html.parser
import json
import pathlib
import re
import subprocess
import sys
import tempfile

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
        "path", "line", "rect", "circle", "polyline", "polygon", "ellipse", "stop", "use"}
HERE = pathlib.Path(__file__).resolve().parent


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


def plain_text(fragment):
    fragment = re.sub(r"<(script|style|svg|code|pre)\b[^>]*>.*?</\1>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def main(path, findings_path=HERE / "kapanan-bulgular.json"):
    src = pathlib.Path(path).read_text(encoding="utf-8")
    p = Parser()
    p.feed(src)
    results = []
    results.append(("tags balanced", not p.errors and not p.stack, "; ".join(p.errors[:3]) or str(p.stack[:3])))
    dups = sorted(k for k, v in p.ids.items() if v > 1)
    results.append(("no duplicate ids", not dups, " ".join(dups)))
    missing = sorted({h for h in p.hrefs if h not in p.ids})
    results.append(("local links resolve", not missing, " ".join(missing)))

    # every requirement row is found independently of its slice attribute, then each must carry a valid slice
    req_rows = re.findall(r'<tr id="([A-M]\d{1,2})"([^>]*)>(.*?)</tr>', src, re.S)
    bad = [rid for rid, attrs, _ in req_rows if not re.search(r'\bdata-dilim="[1-4]"', attrs)]
    results.append(("every requirement row carries a valid slice", len(req_rows) > 0 and not bad,
                    f"{len(req_rows)} rows; missing or invalid: {' '.join(bad)}" if bad else f"{len(req_rows)} rows"))
    untested = [rid for rid, _, inner in req_rows
                if 'class="chip must"' in inner and not re.search(r'<span class="tst">Test: <a href="#', inner)]
    results.append(("every MUST row links to a test", len(req_rows) > 0 and not untested, " ".join(untested)))

    # a requirement delivered over several slices lists one sub-scope per slice; the row slice is the smallest
    bad_sl = []
    for rid, attrs, inner in req_rows:
        dm = re.search(r'\bdata-dilim="([1-4])"', attrs)
        dl = re.search(r'\bdata-dilimler="([1-4](?: [1-4])*)"', attrs)
        if not (dm and dl):
            bad_sl.append(rid)
            continue
        sls = [int(x) for x in dl.group(1).split()]
        kps = re.findall(r'<span class="kp" id="([^"]+)"><span class="kd">Dilim (\d)</span>', inner)
        if int(dm.group(1)) != min(sls) or ((len(sls) > 1 or kps) and sorted(int(d) for _, d in kps) != sorted(sls)) \
                or any(not k.startswith(rid + "-") for k, _ in kps):
            bad_sl.append(rid)
    results.append(("slice scopes are consistent", len(req_rows) > 0 and not bad_sl, " ".join(bad_sl)))

    # contract appendix: fingerprints are full 64-digit SHA-256 values, never shortened
    sec = re.search(r'<section id="sozlesme-eki">(.*?)</section>', src, re.S)
    short_fp = []
    if sec:
        body_sz = html.unescape(sec.group(1))
        short_fp = re.findall(r'"[a-z_]*fingerprint"\s*:\s*"(?![0-9a-f]{64}")[^"]*"', body_sz, re.I)
        short_fp += re.findall(r"[0-9a-f]{4}…[0-9a-f]{4}", body_sz)
        short_fp += [h for h in re.findall(r'<code class="hash">([^<]*)</code>', body_sz) if not re.fullmatch(r"[0-9a-f]{64}", h)]
    results.append(("contract appendix shows full fingerprints", bool(sec) and not short_fp, " ".join(short_fp[:3])))

    # conflict records: every row carries an approval state; a pending one names its owner and deadline
    ck = re.findall(r'<tr id="(ck-[a-z0-9-]+)">(.*?)</tr>', src, re.S)
    bad_ck = [cid for cid, inner in ck
              if not re.search(r'<span class="st [a-z]+">(onay bekliyor|onay gerekmez|onaylandı|değiştirildi)</span>', inner)
              or ("onay bekliyor</span>" in inner and not re.search(r"Sahip: .+?\. Son: .+?\.", inner))]
    results.append(("conflict records carry an approval state", len(ck) > 0 and not bad_ck, " ".join(bad_ck)))

    main_html = src.split("<main", 1)[-1].split("</main>", 1)[0]
    text = plain_text(main_html)
    # every experiment and suite mentioned resolves
    at_refs = set(re.findall(r"\bAT-\d\d\b", text))
    tp_refs = set(re.findall(r"\bTP-\d\d\b", text))
    bad_refs = sorted(r for r in at_refs if r not in p.ids) + sorted(r for r in tp_refs if r.lower() not in p.ids)
    results.append(("every AT-xx and TP-xx mention resolves", bool(at_refs) and not bad_refs, " ".join(bad_refs)))

    # glossary: every acronym in the body is defined; sources are citations and are exempt
    gloss = re.findall(r'<dt id="t-[^"]+" data-esanlam="([^"]*)">', src)
    defined = set()
    for variants in gloss:
        for v in html.unescape(variants).split("|"):
            defined.add(v)
            defined.update(re.findall(r"[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9]+", v))
    try:
        common = set(json.loads((HERE.parent / "data" / "sozluk.json").read_text(encoding="utf-8")).get("yaygin", []))
    except FileNotFoundError:
        common = set()
    body_wo_sources = re.sub(r'<section id="kaynaklar".*?</section>', " ", main_html, flags=re.S)
    body_wo_sources = re.sub(r'<span class="dec">.*?</span>', " ", body_wo_sources, flags=re.S)
    tokens = re.findall(r"(?<![\w-])([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ]+[0-9]*[a-z]?[A-ZÇĞİÖŞÜ0-9]*)(?![\w])(?!-\d)",
                        plain_text(body_wo_sources))
    undefined = sorted({t for t in tokens if t not in defined and t not in common
                        and re.sub(r"\d+$", "", t) not in defined})
    results.append(("every acronym is in the glossary", bool(gloss) and not undefined,
                    f"{len(gloss)} terms" if not undefined else "undefined: " + " ".join(undefined)))

    # closed findings must not come back; required statements must stay. Sections that quote sources
    # verbatim (decision book answers, traceability, changelog, sources) are history, not statements.
    current = main_html
    for sec in ("kitap-sonuc", "izlenebilirlik", "gunluk", "kaynaklar"):
        current = re.sub(rf'<section id="{sec}".*?</section>', " ", current, flags=re.S)
    current_text = plain_text(current)
    findings = json.loads(pathlib.Path(findings_path).read_text(encoding="utf-8"))["bulgular"]
    regress = []
    for f in findings:
        for rx in f.get("yasak", []):
            m = re.search(rx, current_text)
            if m:
                regress.append(f'{f["id"]} yasak "{m.group(0)[:60]}"')
        for rx in f.get("zorunlu", []):
            if not re.search(rx, current_text):
                regress.append(f'{f["id"]} eksik /{rx[:50]}/')
    results.append(("closed findings stay closed", not regress, f"{len(findings)} findings" if not regress else "; ".join(regress)))

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
