#!/usr/bin/env python3
"""Assemble the GenUI requirements document from its sources.

Usage:
  python3 docs/src/build.py docs/genui-frontend-gereksinimleri.html [--artifact PATH]

Inputs (next to this script):
  style.css                        page styles
  parts/*.html                     page body in file-name order; {{icon:name}}, {{THEAD}},
                                   {{PHASE_BUTTONS}} and {{TRACE}} are filled in here
  icons/*.svg                      Phosphor regular icons (MIT)
  data/karar-kaydi.fixture.json    sanitized decision record (only fields the trace table shows)
  data/kimlik-rehberi.json         decisions of the Keycloak + Headless Frappe identity guide
  data/etkin-kararlar.json         record decisions superseded or reopened by a later source

Outputs:
  the standalone page given as the first argument
  optionally a fragment for the Artifact tool (no doctype/html/head/body)
"""
import html as _html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
if not args:
    raise SystemExit(__doc__)
REPO_OUT = pathlib.Path(args[0])
ART_OUT = pathlib.Path(args[args.index("--artifact") + 1]) if "--artifact" in args else None

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800'
    '&family=Roboto:wght@300;400;500&family=Roboto+Mono:wght@400&display=swap">'
)
TITLE = "GenUI Frontend Gereksinimleri"

style = (HERE / "style.css").read_text(encoding="utf-8")
body = "\n".join(f.read_text(encoding="utf-8") for f in sorted((HERE / "parts").glob("*.html")))

icons = {}
for p in (HERE / "icons").glob("*.svg"):
    raw = p.read_text(encoding="utf-8")
    inner = re.sub(r"^<svg[^>]*>", "", raw.strip())
    icons[p.stem] = re.sub(r"</svg>$", "", inner).strip()


def icon(m):
    name, cls = m.group(1), m.group(2) or ""
    if name not in icons:
        raise SystemExit(f"unknown icon: {name}")
    extra = f" {cls}" if cls else ""
    return (f'<svg class="ico{extra}" viewBox="0 0 256 256" aria-hidden="true" focusable="false">'
            f"{icons[name]}</svg>")


# phase in which each requirement becomes binding (00 Keşif … 04 Ölçek), per the decision record
PHASE = {}


def _ph(ids, ph):
    for i in ids.split():
        PHASE[i] = ph


_ph("A1 A2 A3 A4 A5 A6 A7 B1 B2 B3 B4 B5 B6 B7 B8 B9 B10 C1 C2 C3 C4 C5 D1 D2 D3 D4 E1 E2 E3 E6 G1 G2 G3 G5 G6 G7 H2 J1 J2 K1 K3 K5 K7 K8 K9 K10", "01")
_ph("C6 C7 C8 C9 D5 D6 D7 D8 D9 D10 D11 E8 J3 J4 J5 J6 J7 J8 K4 L1 L3 L4 L5", "02")
_ph("E4 E5 E7 E9 E10 F1 F2 F3 F4 F5 F6 F7 F8 G4 H1 H3 H4 H5 H6 I1 I2 I3 I4 I5 I6 I7 I8 I9 I10 K2 K6", "03")
_ph("L2 L6 L7 L8 L9", "04")
_ph("M1 M2 M3 M4 M5 M6 M7 M8 M10 M12 M13 M14 M16 M17 M18 M19 M20 M22 M24 K11 K12", "01")
_ph("M9 M11 M15 M23", "02")
_ph("M21", "04")

ROW_ID = r"[A-M]\d{1,2}"
missing_phase = []


# every requirement row becomes an anchor (#A1), its id cell a link to itself, and carries its phase
def _row(m):
    rid = m.group(1)
    if rid not in PHASE:
        missing_phase.append(rid)
    ph = PHASE.get(rid, "01")
    return (f'<tr id="{rid}" data-phase="{ph}"><td class="id"><a href="#{rid}">{rid}</a>'
            f'<span class="ph">faz {ph}</span></td>')


body = re.sub(rf'<tr><td class="id">({ROW_ID})</td>', _row, body)
if missing_phase:
    raise SystemExit("requirements without a phase: " + " ".join(missing_phase))

# phase filter buttons come from the phases that rows actually carry, so no phase can lose its button
phases = sorted(set(re.findall(r'<tr id="[A-M]\d{1,2}" data-phase="(\d\d)">', body)))
PHASE_BUTTONS = '<button type="button" data-phase="ALL" aria-pressed="true">Tümü</button>\n' + "\n".join(
    f'        <button type="button" data-phase="{p}" aria-pressed="false">{p}</button>' for p in phases)
body = body.replace("{{PHASE_BUTTONS}}", PHASE_BUTTONS)

# stable ids for requirement groups so the contents rail can deep-link to them
body = re.sub(
    r'<div class="group">(\s*<div class="group-head"><h3><span class="k">([A-M])</span>)',
    lambda m: f'<div class="group" id="g-{m.group(2).lower()}">{m.group(1)}',
    body,
)

THEAD = ('<thead><tr><th scope="col">ID</th><th scope="col">Seviye</th>'
         '<th scope="col">Gereksinim</th><th scope="col">Aktör</th></tr></thead>')
body = body.replace("{{THEAD}}", THEAD)

# ---- decision traceability ----
DEC = json.loads((HERE / "data" / "karar-kaydi.fixture.json").read_text(encoding="utf-8"))
GUIDE = json.loads((HERE / "data" / "kimlik-rehberi.json").read_text(encoding="utf-8"))["decisions"]
OVR = json.loads((HERE / "data" / "etkin-kararlar.json").read_text(encoding="utf-8"))["overrides"]

rows = []
for m in re.finditer(rf'<tr id="({ROW_ID})" data-phase="(\d\d)">(.*?)</tr>', body, re.S):
    rid, ph, inner = m.group(1), m.group(2), m.group(3)
    dec = re.search(r'<span class="dec">(.*?)</span>', inner)
    actor = re.search(r'<td class="actor">([^<]+)</td>', inner)
    tags = [t.strip() for t in dec.group(1).split("·")] if dec else []
    rows.append((rid, ph, actor.group(1) if actor else "", tags))

dec_ids = {d["id"] for d in DEC["decisions"]}
guide_ids = {"kimlik:" + g["id"] for g in GUIDE}
unknown_ovr = set(OVR) - dec_ids
if unknown_ovr:
    raise SystemExit("overrides for unknown decisions: " + " ".join(sorted(unknown_ovr)))
by_dec, by_guide, unknown = {}, {}, set()
for rid, ph, actor, tags in rows:
    for t in tags:
        if t in dec_ids:
            by_dec.setdefault(t, []).append((rid, ph, actor))
        elif t in guide_ids:
            by_guide.setdefault(t, []).append((rid, ph, actor))
        else:
            unknown.add((rid, t))


def req_links(mapped):
    return " ".join(f'<a class="rid" href="#{r}">{r}</a>' for r, _, _ in mapped)


tr_rows, unmapped = [], []
counts = {"eşlendi": 0, "eşlenmedi": 0, "keşif açık": 0, "koşul dışı": 0,
          "yerine geçti": 0, "yeniden açıldı": 0, "koşullu": 0}
n_dev = 0
for d in DEC["decisions"]:
    did = d["id"]
    sel = ", ".join(d["selected"]) or "—"
    n_dev += 1 if d["deviation"] else 0
    mapped = by_dec.get(did, [])
    ovr = OVR.get(did)
    if not d["active"]:
        st, cls = "koşul dışı", ""
    elif d["status"] == "discovery":
        st, cls = "keşif açık", "open"
    elif ovr:
        st, cls = ovr["state"], "open"
    elif mapped:
        st, cls = "eşlendi", "ok"
    else:
        st, cls = "eşlenmedi", "open"
        unmapped.append(did)
    counts[st] += 1
    if ovr:
        eff = (f'{_html.escape(ovr["effective"])} <span class="dev">{_html.escape(ovr["source"])}; '
               f'<a href="#{ovr["adr"]}">ADR bekliyor</a></span>')
    else:
        eff = "seçim"
    rec_cell = f'<span class="dev">{_html.escape(d["recommended"])}</span>' if d["recommended"] else "aynı"
    owners = ", ".join(sorted({a for _, _, a in mapped})) or "—"
    phase = min((p for _, p, a in mapped), default="—")
    tr_rows.append(
        f'<tr><td>{did}</td><td>{_html.escape(d["title"])}</td><td>{_html.escape(sel)}</td><td>{rec_cell}</td>'
        f'<td>{eff}</td><td>{req_links(mapped) or "—"}</td><td>{owners}</td><td>{phase}</td>'
        f'<td><span class="st {cls}">{st}</span></td></tr>')

g_rows, g_unmapped = [], []
g_counts = {"eşlendi": 0, "açık karar": 0, "eşlenmedi": 0}
for g in GUIDE:
    mapped = by_guide.get("kimlik:" + g["id"], [])
    if mapped:
        st, cls = "eşlendi", "ok"
    elif g["status"] != "Kararlaştırıldı":
        st, cls = "açık karar", "open"
    else:
        st, cls = "eşlenmedi", "open"
        g_unmapped.append(g["id"])
    g_counts[st] += 1
    reqs = req_links(mapped) or '<a class="rid" href="#acik">Açık kararlar</a>'
    owners = ", ".join(sorted({a for _, _, a in mapped})) or "—"
    phase = min((p for _, p, _ in mapped), default="—")
    g_rows.append(
        f'<tr><td>{g["id"]}</td><td>{_html.escape(g["title"])}</td><td>{g["status"]}</td>'
        f'<td>{reqs}</td><td>{owners}</td><td>{phase}</td><td><span class="st {cls}">{st}</span></td></tr>')

n = len(DEC["decisions"])
TRACE = f'''<section id="izlenebilirlik">
  <div class="sec-head">
    <div class="title"><h2>Karar izlenebilirliği</h2></div>
    <p>Karar kaydındaki {n} kararın her biri için seçim, farklıysa kaydın önerisi, etkin karar, kararı karşılayan gereksinim satırları, sorumlu, bağlayıcı olduğu faz ve durum. Tablo her derlemede temizlenmiş karar verisinden ve satırlardaki "karar" etiketlerinden otomatik üretilir. Kaynak seçim tarihçe olarak korunur; sonraki bir kaynakla değişen karar "yerine geçti", yeniden açılan karar "yeniden açıldı" olarak işaretlenir ve ADR satırına bağlanır. Durum dağılımı: {counts["eşlendi"]} eşlendi, {counts["yerine geçti"]} yerine geçti, {counts["yeniden açıldı"]} yeniden açıldı, {counts["koşullu"]} koşullu, {counts["eşlenmedi"]} eşlenmedi, {counts["keşif açık"]} keşif açık, {counts["koşul dışı"]} koşul dışı; {n_dev} kararda seçim öneriden farklı. İkinci tablo kimlik rehberinin {len(GUIDE)} kararını "kimlik:" etiketleriyle eşler: {g_counts["eşlendi"]} eşlendi, {g_counts["açık karar"]} açık karar, {g_counts["eşlenmedi"]} eşlenmedi. Etiket eşleşmesi bir tamlık puanı değildir: bir satırın bir kararı etiketlemesi, kararın o satırda anlamca doğru uygulandığını kanıtlamaz; bunu kabul deneyleri ve inceleme kanıtlar.</p>
  </div>
  <details class="appendix">
    <summary>{n} kararın tablosunu aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Karar</th><th scope="col">Soru</th><th scope="col">Seçim (kaynak)</th><th scope="col">Kaydın önerisi</th><th scope="col">Etkin karar</th><th scope="col">Gereksinim</th><th scope="col">Sorumlu</th><th scope="col">Faz</th><th scope="col">Durum</th></tr></thead>
      <tbody>
        {chr(10).join(tr_rows)}
      </tbody>
    </table></div>
  </details>
  <details class="appendix">
    <summary>Kimlik rehberinin {len(GUIDE)} kararını aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Karar</th><th scope="col">Rehberdeki karar</th><th scope="col">Rehberdeki durum</th><th scope="col">Gereksinim</th><th scope="col">Sorumlu</th><th scope="col">Faz</th><th scope="col">Durum</th></tr></thead>
      <tbody>
        {chr(10).join(g_rows)}
      </tbody>
    </table></div>
  </details>
</section>'''
body = body.replace("{{TRACE}}", TRACE)
print("requirements:", len(rows), "phases:", " ".join(phases))
print("trace:", counts, "deviations:", n_dev)
print("guide trace:", g_counts)
if unmapped:
    print("UNMAPPED decisions:", " ".join(unmapped))
if g_unmapped:
    print("UNMAPPED guide decisions:", " ".join(g_unmapped))
if unknown:
    print("UNKNOWN dec tags:", sorted(unknown))

body = re.sub(r"\{\{icon:([a-z0-9-]+)(?:\|([a-z0-9 -]+))?\}\}", icon, body)
leftover = re.findall(r"\{\{[A-Z_]+\}\}", body)
if leftover:
    raise SystemExit("unfilled placeholders: " + " ".join(leftover))

head_common = f"<title>{TITLE}</title>\n{FONTS}\n<style>\n{style}\n</style>"
full = (
    "<!doctype html>\n"
    '<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Ant Design + Frappe Framework merkezli, Keycloak kimlikli, yapay zekâ öncelikli GenUI frontend için gereksinim ve mimari sözleşmesi.">\n'
    f"{head_common}\n</head>\n<body>\n{body}\n</body>\n</html>\n"
)
REPO_OUT.parent.mkdir(parents=True, exist_ok=True)
REPO_OUT.write_text(full, encoding="utf-8")
print(f"wrote {REPO_OUT} ({len(full.encode('utf-8'))} bytes)")
if ART_OUT:
    ART_OUT.write_text(f"{head_common}\n{body}\n", encoding="utf-8")
    print(f"wrote {ART_OUT}")
