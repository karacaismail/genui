#!/usr/bin/env python3
"""Assemble the GenUI requirements document from its sources.

Usage:
  python3 docs/src/build.py docs/genui-frontend-gereksinimleri.html [--artifact PATH]

Inputs (next to this script):
  style.css                          page styles
  parts/*.html                       page body in file-name order; placeholders filled here:
                                     {{icon:name}}, {{THEAD}}, {{PHASE_BUTTONS}}, {{TRACE}}, {{KITAP}},
                                     {{SOZLUK}}, {{TEST_PAKETLERI}}, {{TEST_MATRIS}}, {{DILIM_OZET}},
                                     {{CELISKILER}}, {{SZ_*}} (contract appendix)
  icons/*.svg                        Phosphor regular icons (MIT)
  data/karar-kaydi.fixture.json      sanitized decision record (only fields the trace table shows)
  data/kimlik-rehberi.json           decisions of the Keycloak + Headless Frappe identity guide
  data/etkin-kararlar.json           record decisions superseded, closed or extended by a later source
  data/karar-kitabi-yanitlari.json   the owner's decision book answers (export, schemaVersion 1)
  data/karar-kitabi-uygulama.json    how each answer was applied, with target ids in this document
  data/test-baglari.json             test suites (TP), requirement -> test links, AT metadata
  data/sozluk.json                   glossary; first use of each term links to it
  data/celiskiler.json               conflicts: raw answer, proposed solution, what is in force, approval state
  data/sozlesme-fixture.json         contract appendix examples, fingerprint vectors, Run states (checked by sozlesme.py)

Outputs:
  the standalone page given as the first argument
  gereksinimler.json next to it (tool-neutral export of the requirement rows)
  optionally a fragment for the Artifact tool (no doctype/html/head/body)

The build fails when: a requirement has no slice; a MUST has no test link; a test link names an
unknown suite or experiment; an experiment has no metadata; a decision-book answer has no
application record or points to an id that does not exist; a placeholder is left unfilled; a sub-scope
has no test running in its own slice; an experiment proves later-slice work without a part for that slice
or names later-slice features in its own scenario; a conflict record breaks its approval rules or its
links to answers; a contract fingerprint, identity or Run state in the fixture does not check out.
"""
import html as _html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sozlesme  # noqa: E402  contract appendix: canonical JSON, fingerprints, fixture checks
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
esc = _html.escape
errors = []


def load(name):
    return json.loads((HERE / "data" / name).read_text(encoding="utf-8"))


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


# ---- slices (dilim): the vertical slice at whose gate each requirement must be at least O2 ----
DILIM = {}


def _dl(ids, n):
    for i in ids.split():
        DILIM[i] = n


_dl("A1 A2 A3 A4 A5 A6 A7 A8", 1)
_dl("B1 B2 B3 B4 B5 B6 B7 B9 B10 B11 B12", 1)
_dl("B8", 2)
_dl("C1 C2 C3 C4 C5 C6 C7 C8 C9", 1)
_dl("D1 D2 D3 D4 D5 D7 D8 D10", 1)
_dl("D6 D9 D11", 2)
_dl("E1 E2 E3 E4 E5 E6 E7 E8 E9 E10", 1)
_dl("E11", 4)
_dl("F1 F2 F3 F4 F5 F6 F7 F8 F9", 1)
_dl("F10", 4)
_dl("G1 G2 G3 G4 G5 G6 G7 G8", 1)
_dl("H1 H2 H3 H4 H6", 1)
_dl("H5", 4)
_dl("I1 I2 I3 I4 I5 I6 I7 I8 I9 I10", 1)
_dl("I11 I12 I13", 2)
_dl("J1 J2 J3 J4 J5 J6 J7 J9", 1)
_dl("J8 J10", 2)
_dl("K1 K2 K3 K4 K5 K6 K7 K8 K9 K10 K11 K12 K13 K14 K15 K16", 1)
_dl("L1 L3 L4 L5 L7 L10", 2)
_dl("L8 L9", 3)
_dl("L2 L6", 4)
_dl("M1 M2 M3 M4 M5 M6 M7 M8 M9 M10 M11 M12 M13 M14 M16 M17 M18 M19 M20 M22 M23 M24 M25", 1)
_dl("M26", 2)
_dl("M15 M21 M27", 3)

ROW_ID = r"[A-M]\d{1,2}"
TR_RE = rf'<tr id="({ROW_ID})" data-dilim="(\d)"[^>]*>'
TESTS = load("test-baglari.json")
SUITES, RAW_LINKS, ATMETA = TESTS["paketler"], TESTS["baglar"], TESTS["at"]
TERMS = TESTS.get("dilim_terimleri", {})

# a requirement delivered over several slices lists its sub-scopes; LINKS is the union of their tests
LINKS, SUBS = {}, {}
for _rid, _v in RAW_LINKS.items():
    if isinstance(_v, dict):
        SUBS[_rid] = _v["kapsamlar"]
        LINKS[_rid] = list(dict.fromkeys(t for s in _v["kapsamlar"] for t in s["test"]))
    else:
        LINKS[_rid] = _v
for _rid, _subs in SUBS.items():
    _ids = [s["id"] for s in _subs]
    if len(set(_ids)) != len(_ids) or any(not i.startswith(_rid + "-") for i in _ids):
        errors.append(f"{_rid}: sub-scope ids must be unique and start with '{_rid}-'")
    if DILIM.get(_rid) != min(s["dilim"] for s in _subs):
        errors.append(f"{_rid}: row slice {DILIM.get(_rid)} is not the smallest sub-scope slice")
    if len({s['dilim'] for s in _subs}) != len(_subs):
        errors.append(f"{_rid}: two sub-scopes in the same slice")


def scopes(rid):
    """Sub-scopes of a requirement; a single-slice requirement is its own scope."""
    return SUBS.get(rid) or [{"id": rid, "dilim": DILIM.get(rid, 1), "kapsam": "", "test": LINKS.get(rid, [])}]


def dl_label(rid):
    return "dilim " + " · ".join(str(s["dilim"]) for s in scopes(rid))


# ---- conflicts between answers and interpretations awaiting the owner's approval ----
CK = load("celiskiler.json")["celiskiler"]
CK_IDS = [c["id"] for c in CK]
ONAY = {"onay bekliyor", "onaylandı", "değiştirildi", "onay gerekmez"}
pending_by_target = {}
for c in CK:
    o = c["onay"]
    if not c["id"].startswith("ck-"):
        errors.append(f"conflict id must start with ck-: {c['id']}")
    if o["durum"] not in ONAY:
        errors.append(f"{c['id']}: unknown approval state {o['durum']}")
    if o["durum"] in ("onaylandı", "değiştirildi") and not (o.get("onaylayan") and o.get("tarih")):
        errors.append(f"{c['id']}: '{o['durum']}' needs onaylayan and tarih")
    if o["durum"] == "onay bekliyor" and not (o.get("sahip") and o.get("son")):
        errors.append(f"{c['id']}: 'onay bekliyor' needs sahip and son")
    if o["durum"] == "onay gerekmez" and not o.get("gerekce"):
        errors.append(f"{c['id']}: 'onay gerekmez' needs gerekce")
    for f in ("ham_cevap", "sorun", "oneri", "yururluk", "kapsam_farki"):
        if not c.get(f):
            errors.append(f"{c['id']}: missing {f}")
    if o["durum"] == "onay bekliyor":
        for t in c["etkiledigi"]:
            pending_by_target.setdefault(t, []).append(c["id"])
    elif re.search(r"onay bekl|çalışma varsayım|onaya kadar", c["yururluk"], re.I):
        errors.append(f"{c['id']}: '{o['durum']}' but what is in force still reads as pending: move it to onceki_yururluk")
if len(set(CK_IDS)) != len(CK_IDS):
    errors.append("duplicate conflict ids")


def _row(m):
    rid = m.group(1)
    if rid not in DILIM:
        errors.append(f"requirement without a slice: {rid}")
    n = DILIM.get(rid, 1)
    all_sl = " ".join(str(s["dilim"]) for s in scopes(rid))
    return (f'<tr id="{rid}" data-dilim="{n}" data-dilimler="{all_sl}"><td class="id"><a href="#{rid}">{rid}</a>'
            f'<span class="ph">{dl_label(rid)}</span></td>')


body = re.sub(rf'<tr><td class="id">({ROW_ID})</td>', _row, body)


def test_link(t):
    if t.startswith("TP-"):
        if t not in SUITES:
            errors.append(f"unknown test suite {t}")
        return f'<a href="#{t.lower()}">{t}</a>'
    if t not in ATMETA:
        errors.append(f"unknown experiment {t}")
    return f'<a href="#{t}">{t}</a>'


row_levels = {}


def _tests(m):
    row = m.group(0)
    rid = m.group(1)
    lvl = re.search(r'<span class="chip (must|should|may)">', row)
    level = lvl.group(1).upper() if lvl else ""
    row_levels[rid] = level
    tests = LINKS.get(rid, [])
    if level == "MUST" and not tests:
        errors.append(f"MUST without a test link: {rid}")
    span = ""
    if tests:
        span = '<span class="tst">Test: ' + " · ".join(test_link(t) for t in tests) + "</span>"
    if rid in SUBS:
        span += '<span class="kps"><span class="kh">Dilim kapsamı</span>' + "".join(
            f'<span class="kp" id="{s["id"]}"><span class="kd">Dilim {s["dilim"]}</span> <b>{s["id"]}</b>: '
            f'{esc(s["kapsam"])} <span class="kt">Test: {" · ".join(test_link(t) for t in s["test"])}</span></span>'
            for s in SUBS[rid]) + "</span>"
    if rid in pending_by_target:
        span += '<span class="onay">Onay bekleyen yorum: ' + " · ".join(
            f'<a href="#{c}">{c}</a>' for c in pending_by_target[rid]) + "</span>"
    if not span:
        return row
    if '<span class="dec">' in row:
        return row.replace('<span class="dec">', span + '<span class="dec">', 1)
    return row.replace('</td><td class="actor">', span + '</td><td class="actor">', 1)


body = re.sub(rf'{TR_RE}.*?</tr>', _tests, body, flags=re.S)
unknown_links = set(LINKS) - set(DILIM)
if unknown_links:
    errors.append("test links for unknown requirements: " + " ".join(sorted(unknown_links)))

# slice filter buttons come from the slices rows actually carry (every sub-scope slice counts)
slices = sorted({x for v in re.findall(r'data-dilimler="([\d ]+)"', body) for x in v.split()})
PHASE_BUTTONS = '<button type="button" data-dilim="ALL" aria-pressed="true">Tümü</button>\n' + "\n".join(
    f'        <button type="button" data-dilim="{n}" aria-pressed="false">Dilim {n}</button>' for n in slices)
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

# ---- acceptance experiments: anchor ids, a metadata line and per-slice parts, all from test-baglari.json ----
# proves[AT] = [(requirement, sub-scope)] for every sub-scope that lists the experiment
proves = {}
for rid in LINKS:
    for s in scopes(rid):
        for t in s["test"]:
            if t.startswith("AT-"):
                proves.setdefault(t, []).append((rid, s))


def active_slices(at):
    meta = ATMETA[at]
    return {meta["dilim"]} | {p["dilim"] for p in meta.get("parcalar", [])}


# slice alignment: an experiment gating slice N must not depend on work delivered in a later slice
for at, meta in ATMETA.items():
    n = meta["dilim"]
    part_sl = [p["dilim"] for p in meta.get("parcalar", [])]
    if len(set(part_sl)) != len(part_sl) or any(d <= n or d > 4 for d in part_sl):
        errors.append(f"{at}: parts must be in distinct slices after its own slice {n}")
    for rid, s in proves.get(at, []):
        if s["dilim"] > n and s["dilim"] not in part_sl:
            errors.append(f"{at} (Dilim {n}) proves {s['id']} delivered in Dilim {s['dilim']}: "
                          f"the Dilim {n} gate would depend on later work; add a Dilim {s['dilim']} part")
    for d in part_sl:
        if not any(s["dilim"] == d for _, s in proves.get(at, [])):
            errors.append(f"{at}: the Dilim {d} part proves no sub-scope of Dilim {d}")
for rid in LINKS:
    for s in scopes(rid):
        ok = any(t.startswith("TP-") or s["dilim"] in active_slices(t) for t in s["test"] if t in SUITES or t in ATMETA)
        if not ok:
            errors.append(f"{s['id']}: no test runs in its own slice {s['dilim']}")


def term_hits(text, n):
    plain_t = re.sub(r"<[^>]+>", " ", text)
    return [t for t, d in TERMS.items() if d > n and re.search(re.escape(t), plain_t, re.I)]


def sub_link(s):
    return f'<a href="#{s["id"]}">{s["id"]}</a>'


seen_at = []
_exp_src = body[body.find('<section id="deneyler">'):]
for blk in re.split(r'(?=<div><div class="t"><span class="n">AT-\d\d</span>)', _exp_src)[1:]:
    _at_id = re.match(r'<div><div class="t"><span class="n">(AT-\d\d)</span>', blk).group(1)
    blk = blk.split("</section>")[0]
    if _at_id in ATMETA:
        hits = term_hits(blk, ATMETA[_at_id]["dilim"])
        if hits:
            errors.append(f"{_at_id} (Dilim {ATMETA[_at_id]['dilim']}) names later-slice features in its own scenario: "
                          + ", ".join(hits) + "; move them to a part")
        for p in ATMETA[_at_id].get("parcalar", []):
            ph = term_hits(p["degisen"] + " " + p["gecer"] + " " + p["onkosul"], p["dilim"])
            if ph:
                errors.append(f"{_at_id} Dilim {p['dilim']} part names later-slice features: " + ", ".join(ph))


def _at(m):
    at, rest, own_rows = m.group(1), m.group(2), m.group(3)
    seen_at.append(at)
    meta = ATMETA.get(at)
    if not meta:
        errors.append(f"experiment without metadata: {at}")
        return m.group(0)
    n = meta["dilim"]
    own = [s for _, s in proves.get(at, []) if s["dilim"] == n]
    earlier = [s for _, s in proves.get(at, []) if s["dilim"] < n]
    parts = meta.get("parcalar", [])
    info = (f'Dilim {n}' + (" (ek parçalar: " + ", ".join(f"Dilim {p['dilim']}" for p in parts) + ")" if parts else "")
            + f' · {esc(meta["tur"])} · sahip: {esc(meta["sahip"])}. Ön koşul: {esc(meta["onkosul"])}.'
            + (" Kanıtladığı: " + " ".join(sub_link(s) for s in own) + "." if own else "")
            + (" Önceki dilimden yeniden sınadığı: " + " ".join(sub_link(s) for s in earlier) + "." if earlier else ""))
    rows_html = "".join(
        f'<div class="row part"><span class="lab">Dilim {p["dilim"]}</span><span>Ön koşul: {esc(p["onkosul"])}. '
        f'<b>Değişen:</b> {esc(p["degisen"])} <b>Geçer:</b> {esc(p["gecer"])} Kanıtladığı: '
        + " ".join(sub_link(s) for _, s in proves.get(at, []) if s["dilim"] == p["dilim"]) + ".</span></div>"
        for p in parts)
    return (f'<div id="{at}"><div class="t"><span class="n">{at}</span>{rest}</div>'
            f'<div class="row"><span class="lab">Künye</span><span>{info}</span></div>{own_rows}{rows_html}</div>')


# every experiment is one line: title div, then its own rows; per-slice parts are appended after them
body = re.sub(r'<div><div class="t"><span class="n">(AT-\d\d)</span>(.*?)</div>(<div class="row">[^\n]*)</div>$',
              _at, body, flags=re.M)
missing_meta = set(ATMETA) - set(seen_at)
if missing_meta:
    errors.append("metadata for experiments not in the document: " + " ".join(sorted(missing_meta)))
gate_at = set(re.findall(r'<div id="(AT-\d\d)"><div class="t">[^\n]*?<span class="chip gate">', body))

# ---- rows: collect for trace, slices summary, test matrix and JSON export ----
rows = []
for m in re.finditer(rf'{TR_RE}(.*?)</tr>', body, re.S):
    rid, n, inner = m.group(1), int(m.group(2)), m.group(3)
    dec = re.search(r'<span class="dec">(.*?)</span>', inner)
    actor = re.search(r'<td class="actor">([^<]+)</td>', inner)
    title = re.search(r'<b class="k">(.*?)</b>', inner, re.S)
    req = re.search(r'<span class="req">(.*?)</span>(?=<span class="(?:note|tst|kps|onay|dec)">|</td>)', inner, re.S)
    note = re.search(r'<span class="note">(.*?)</span>(?=<span class="(?:tst|kps|onay|dec)">|</td>)', inner, re.S)
    tags = [t.strip() for t in dec.group(1).split("·")] if dec else []
    rows.append({"id": rid, "dilim": n, "actor": actor.group(1) if actor else "", "tags": tags,
                 "level": row_levels.get(rid, ""),
                 "title": title.group(1) if title else "", "req": req.group(1) if req else "",
                 "note": note.group(1) if note else ""})


def plain(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


# ---- decision traceability ----
DEC = load("karar-kaydi.fixture.json")
GUIDE = load("kimlik-rehberi.json")["decisions"]
OVR = load("etkin-kararlar.json")["overrides"]

dec_ids = {d["id"] for d in DEC["decisions"]}
guide_ids = {"kimlik:" + g["id"] for g in GUIDE}
unknown_ovr = set(OVR) - dec_ids
if unknown_ovr:
    errors.append("overrides for unknown decisions: " + " ".join(sorted(unknown_ovr)))
by_dec, by_guide, unknown = {}, {}, set()
for r in rows:
    for t in r["tags"]:
        if t in dec_ids:
            by_dec.setdefault(t, []).append(r)
        elif t in guide_ids:
            by_guide.setdefault(t, []).append(r)
        else:
            unknown.add((r["id"], t))


def req_links(mapped):
    return " ".join(f'<a class="rid" href="#{r["id"]}">{r["id"]}</a>' for r in mapped)


tr_rows, unmapped = [], []
counts = {}
n_dev = 0
for d in DEC["decisions"]:
    did = d["id"]
    sel = ", ".join(d["selected"]) or "—"
    n_dev += 1 if d["deviation"] else 0
    mapped = by_dec.get(did, [])
    ovr = OVR.get(did)
    if not d["active"]:
        st, cls = "koşul dışı", "muted"
    elif ovr:
        st = ovr["state"]
        cls = "ok" if st == "kapandı" else "warn" if st in ("yerine geçti", "genişletildi") else "open"
    elif d["status"] == "discovery":
        st, cls = "keşif açık", "open"
    elif mapped:
        st, cls = "eşlendi", "ok"
    else:
        st, cls = "eşlenmedi", "open"
        unmapped.append(did)
    counts[st] = counts.get(st, 0) + 1
    if ovr:
        eff = (f'{esc(ovr["effective"])} <span class="dev">{esc(ovr["source"])}; '
               f'<a href="#{ovr["link"]}">{esc(ovr["link_text"])}</a></span>')
    else:
        eff = "seçim"
    rec_cell = f'<span class="dev">{esc(d["recommended"])}</span>' if d["recommended"] else "aynı"
    owners = ", ".join(sorted({r["actor"] for r in mapped})) or "—"
    first = min((r["dilim"] for r in mapped), default=None)
    tr_rows.append(
        f'<tr><td>{did}</td><td>{esc(d["title"])}</td><td>{esc(sel)}</td><td>{rec_cell}</td>'
        f'<td>{eff}</td><td>{req_links(mapped) or "—"}</td><td>{owners}</td><td>{first or "—"}</td>'
        f'<td><span class="st {cls}">{st}</span></td></tr>')

g_rows, g_unmapped = [], []
g_counts = {}
for g in GUIDE:
    mapped = by_guide.get("kimlik:" + g["id"], [])
    kitap = g.get("kitap")
    if kitap and g.get("kitap_durum") == "ertelendi":
        st, cls = "ertelendi", "open"
    elif kitap:
        st, cls = "kitapla kapandı", "ok"
    elif mapped:
        st, cls = "eşlendi", "ok"
    elif g["status"] != "Kararlaştırıldı":
        st, cls = "açık karar", "open"
    else:
        st, cls = "eşlenmedi", "open"
        g_unmapped.append(g["id"])
    g_counts[st] = g_counts.get(st, 0) + 1
    reqs = req_links(mapped) or '<a class="rid" href="#acik">Açık kararlar</a>'
    kcell = f'<a class="rid" href="#kk-{kitap}">{kitap}</a>' if kitap else "—"
    owners = ", ".join(sorted({r["actor"] for r in mapped})) or "—"
    first = min((r["dilim"] for r in mapped), default=None)
    g_rows.append(
        f'<tr><td>{g["id"]}</td><td>{esc(g["title"])}</td><td>{g["status"]}</td><td>{kcell}</td>'
        f'<td>{reqs}</td><td>{owners}</td><td>{first or "—"}</td><td><span class="st {cls}">{st}</span></td></tr>')

n = len(DEC["decisions"])
dist = ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))
g_dist = ", ".join(f"{v} {k}" for k, v in sorted(g_counts.items(), key=lambda x: -x[1]))
TRACE = f'''<section id="izlenebilirlik">
  <div class="sec-head">
    <div class="title"><h2>Karar izlenebilirliği</h2></div>
    <p>Karar kaydındaki {n} kararın her biri için seçim, farklıysa kaydın önerisi, etkin karar, kararı karşılayan gereksinim satırları, sorumlu, ilk bağlayıcı olduğu dilim ve durum. Tablo her derlemede temizlenmiş karar verisinden ve satırlardaki "karar" etiketlerinden otomatik üretilir. Kaynak seçim tarihçe olarak korunur; sonraki bir kaynakla (kimlik rehberi veya karar kitabı) değişen karar "yerine geçti", kapanan açık karar "kapandı", kapsamı büyüyen karar "genişletildi" olarak işaretlenir ve kaynağına bağlanır. Durum dağılımı: {dist}; {n_dev} kararda seçim öneriden farklı. İkinci tablo kimlik rehberinin {len(GUIDE)} kararını "kimlik:" etiketleriyle ve karar kitabıyla eşler: {g_dist}. Etiket eşleşmesi bir tamlık puanı değildir: bir satırın bir kararı etiketlemesi, kararın o satırda anlamca doğru uygulandığını kanıtlamaz; bunu kabul deneyleri ve inceleme kanıtlar.</p>
  </div>
  <details class="appendix">
    <summary>{n} kararın tablosunu aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Karar</th><th scope="col">Soru</th><th scope="col">Seçim (kaynak)</th><th scope="col">Kaydın önerisi</th><th scope="col">Etkin karar</th><th scope="col">Gereksinim</th><th scope="col">Sorumlu</th><th scope="col">Dilim</th><th scope="col">Durum</th></tr></thead>
      <tbody>
        {chr(10).join(tr_rows)}
      </tbody>
    </table></div>
  </details>
  <details class="appendix">
    <summary>Kimlik rehberinin {len(GUIDE)} kararını aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Karar</th><th scope="col">Rehberdeki karar</th><th scope="col">Rehberdeki durum</th><th scope="col">Karar kitabı</th><th scope="col">Gereksinim</th><th scope="col">Sorumlu</th><th scope="col">Dilim</th><th scope="col">Durum</th></tr></thead>
      <tbody>
        {chr(10).join(g_rows)}
      </tbody>
    </table></div>
  </details>
</section>'''
body = body.replace("{{TRACE}}", TRACE)

# ---- decision book results ----
ANS = load("karar-kitabi-yanitlari.json")
APP = load("karar-kitabi-uygulama.json")["uygulama"]
if ANS.get("kind") != "genui-karar-kitabi-yanitlari" or ANS.get("schemaVersion") != 1:
    errors.append("decision book answers: unexpected kind or schemaVersion")
answers = {a["id"]: a for a in ANS["answers"]}
if set(answers) != set(APP):
    errors.append("decision book: answers without application " + " ".join(sorted(set(answers) - set(APP)))
                  + " / application without answer " + " ".join(sorted(set(APP) - set(answers))))
STATUS_OK = {"answered": {"uygulandı", "çelişki notuyla", "uygulanmaz"}, "deferred": {"ertelendi"},
             "not_applicable": {"uygulanmaz"}}
CHAPTERS = {"urun": "Ürün", "celiski": "Çelişki", "yz": "YZ", "kimlik": "Kimlik", "veri": "Veri",
            "kalite": "Kalite", "ekip": "Ekip", "kayit": "Karar kaydı", "teknik": "Teknik"}
k_rows, k_counts, k_targets = [], {}, []
k_pending = 0


def short(s, lim=320):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= lim else s[:lim].rsplit(" ", 1)[0] + " …"


for a in ANS["answers"]:
    ap = APP.get(a["id"])
    if not ap:
        continue
    if ap["durum"] not in STATUS_OK.get(a["status"], set()):
        errors.append(f'decision book {a["id"]}: answer status {a["status"]} vs application {ap["durum"]}')
    k_counts[ap["durum"]] = k_counts.get(ap["durum"], 0) + 1
    labels = "; ".join(a.get("selectedLabels") or []) or {"deferred": "Ertelendi", "not_applicable": "Uygulanmaz"}.get(a["status"], "—")
    extra = " ".join(x for x in [a.get("customText") or "", a.get("note") or ""] if x.strip())
    extra_html = f'<br><span class="dev">Not: {esc(short(extra))}</span>' if extra.strip() else ""
    targets = []
    for t in ap["hedef"]:
        k_targets.append((a["id"], t))
        targets.append(f'<a class="rid" href="#{t}">{t}</a>')
    cls = {"uygulandı": "ok", "çelişki notuyla": "warn", "ertelendi": "open", "uygulanmaz": "muted"}[ap["durum"]]
    refs = [c for c in CK if a["id"] in c["cevaplar"]]
    for c in refs:
        if c["id"] not in ap["hedef"]:
            errors.append(f'{c["id"]} names {a["id"]} but the application of {a["id"]} does not point to it')
    for t in ap["hedef"]:
        if t.startswith("ck-") and t not in CK_IDS:
            errors.append(f'decision book {a["id"]}: unknown conflict {t}')
        elif t.startswith("ck-") and a["id"] not in next(c for c in CK if c["id"] == t)["cevaplar"]:
            errors.append(f'decision book {a["id"]} points to {t}, but {t} does not name {a["id"]}')
    if ap["durum"] == "çelişki notuyla" and not refs:
        errors.append(f'decision book {a["id"]}: "çelişki notuyla" but no conflict record names it')
    pend = [c["id"] for c in refs if c["onay"]["durum"] == "onay bekliyor"]
    st_html = f'<span class="st {cls}">{ap["durum"]}</span>'
    if pend:
        k_pending += 1
        st_html += '<br><span class="st warn">onay bekliyor</span> ' + " ".join(f'<a class="rid" href="#{c}">{c}</a>' for c in pend)
    k_rows.append(
        f'<tr id="kk-{a["id"]}"><td>{a["id"]}</td><td>{CHAPTERS.get(a["chapter"], a["chapter"])}</td>'
        f'<td>{esc(a["question"])}</td><td>{esc(labels)}{extra_html}</td><td>{esc(ap["ozet"])}</td>'
        f'<td>{" ".join(targets)}</td><td>{st_html}</td></tr>')
s = ANS["summary"]
KITAP = f'''<div class="kitap-ozet"><span><b>{len(ANS["answers"])}</b> soru</span><span><b>{k_counts.get("uygulandı", 0)}</b> uygulandı</span><span><b>{k_counts.get("çelişki notuyla", 0)}</b> çelişki notuyla uygulandı</span><span><b>{k_pending}</b> cevabın yorumu onay bekliyor</span><span><b>{k_counts.get("ertelendi", 0)}</b> ertelendi</span><span><b>{k_counts.get("uygulanmaz", 0)}</b> uygulanmaz</span><span><b>{s["differsFromRecommendation"]}</b> cevap öneriden farklı</span><span>Dışa aktarım: {esc(ANS["exportedAt"])}</span></div>
  <details class="appendix">
    <summary>{len(ANS["answers"])} sorunun uygulama tablosunu aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Soru</th><th scope="col">Bölüm</th><th scope="col">Soru metni</th><th scope="col">Cevap</th><th scope="col">Belgeye etkisi</th><th scope="col">Madde</th><th scope="col">Durum</th></tr></thead>
      <tbody>
        {chr(10).join(k_rows)}
      </tbody>
    </table></div>
  </details>'''
body = body.replace("{{KITAP}}", KITAP)

# ---- conflicts: raw answer, proposed solution, what is in force, approval state (data/celiskiler.json) ----
ck_rows = []
for c in CK:
    o = c["onay"]
    st_cls = {"onay bekliyor": "warn", "onaylandı": "ok", "değiştirildi": "ok", "onay gerekmez": "muted"}[o["durum"]]
    if o["durum"] == "onay bekliyor":
        who = f'Sahip: {esc(o.get("sahip") or "—")}. Son: {esc(o.get("son") or "—")}.'
    elif o["durum"] == "onay gerekmez":
        who = esc(o.get("gerekce") or "—")
    else:
        who = f'{esc(o.get("onaylayan") or "—")}, {esc(o.get("tarih") or "—")}' + (f'. {esc(o["not"])}' if o.get("not") else "")
    q_links = " ".join(f'<a class="rid" href="#kk-{q}">{q}</a>' for q in c["cevaplar"])
    t_links = " ".join(f'<a class="rid" href="#{t}">{t}</a>' for t in c["etkiledigi"])
    for t in c["etkiledigi"]:
        k_targets.append((c["id"], t))
    ck_rows.append(
        f'<tr id="{c["id"]}"><td><b>{esc(c["baslik"])}</b><br><span class="dev">{c["id"]}</span><br>{q_links}</td>'
        f'<td>{esc(c["ham_cevap"])}<br><span class="dev">Sorun: {esc(c["sorun"])}</span></td>'
        f'<td>{esc(c["oneri"])}</td><td>{esc(c["yururluk"])}'
        + (f'<br><span class="dev gecmis">Önceki durum: {esc(c["onceki_yururluk"])}</span>' if c.get("onceki_yururluk") else "")
        + f'</td><td>{esc(c["kapsam_farki"])}</td>'
        f'<td><span class="st {st_cls}">{o["durum"]}</span><br>{who}</td><td>{t_links}</td></tr>')
n_pend = sum(1 for c in CK if c["onay"]["durum"] == "onay bekliyor")
CELISKILER = f'''<p class="ck-ozet" style="margin-top:.4rem"><b>{len(CK)}</b> kayıt: <b>{n_pend}</b> onay bekliyor, <b>{sum(1 for c in CK if c["onay"]["durum"] == "onay gerekmez")}</b> onay gerektirmiyor, <b>{sum(1 for c in CK if c["onay"]["durum"] in ("onaylandı", "değiştirildi"))}</b> onaylandı veya değiştirildi. Kaynak: <code>docs/src/data/celiskiler.json</code>.</p>
  <div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose ck">
    <thead><tr><th scope="col">Çelişki ve cevaplar</th><th scope="col">Ham cevap ve sorun</th><th scope="col">Çözüm (onaylanmadıysa öneri)</th><th scope="col">Yürürlükte olan</th><th scope="col">Kapsam farkı</th><th scope="col">Onay</th><th scope="col">Etkilediği</th></tr></thead>
    <tbody>
      {chr(10).join(ck_rows)}
    </tbody>
  </table></div>'''
body = body.replace("{{CELISKILER}}", CELISKILER)

# ---- test strategy tables ----
suite_use = {}
for rid, tests in LINKS.items():
    for t in tests:
        suite_use.setdefault(t, []).append(rid)
tp_rows = []
for tid, sp in SUITES.items():
    tp_rows.append(
        f'<tr id="{tid.lower()}"><td>{tid}</td><td>{esc(sp["ad"])}</td><td>{esc(sp["katman"])}</td>'
        f'<td>{esc(sp["sinar"])}</td><td>{esc(sp["arac"])}</td><td>{esc(sp["siklik"])}</td>'
        f'<td>{len(suite_use.get(tid, []))}</td></tr>')
unused = [t for t in SUITES if t not in suite_use]
if unused:
    errors.append("test suites linked to no requirement: " + " ".join(unused))
TEST_PAKETLERI = f'''<div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose">
    <thead><tr><th scope="col">Kimlik</th><th scope="col">Paket</th><th scope="col">Katman</th><th scope="col">Ne sınar</th><th scope="col">Araç</th><th scope="col">Sıklık</th><th scope="col">Bağlı gereksinim</th></tr></thead>
    <tbody>
      {chr(10).join(tp_rows)}
    </tbody>
  </table></div>'''
body = body.replace("{{TEST_PAKETLERI}}", TEST_PAKETLERI)
n_must = sum(1 for r in rows if r["level"] == "MUST")
m_rows = [f'<tr><td><a class="rid" href="#{r["id"]}">{r["id"]}</a></td><td>{r["level"]}</td>'
          f'<td>{" · ".join(str(x["dilim"]) for x in scopes(r["id"]))}</td>'
          f'<td>{" · ".join(test_link(t) for t in LINKS.get(r["id"], [])) or "—"}</td></tr>' for r in rows]
TEST_MATRIS = f'''<p style="margin-top:.4rem;color:var(--ink-2)">{len(rows)} gereksinimin {n_must}'i MUST'tır ve her biri en az bir otomatik test paketine veya kabul deneyine bağlıdır; bağsız MUST derlemeyi kırar (K14). Tablo her derlemede <code>docs/src/data/test-baglari.json</code> dosyasından üretilir.</p>
  <details class="appendix">
    <summary>{len(rows)} gereksinimin test bağını aç</summary>
    <div class="tbl-wrap"><table class="trace">
      <thead><tr><th scope="col">Gereksinim</th><th scope="col">Seviye</th><th scope="col">Dilim</th><th scope="col">Testler</th></tr></thead>
      <tbody>
        {chr(10).join(m_rows)}
      </tbody>
    </table></div>
  </details>'''
body = body.replace("{{TEST_MATRIS}}", TEST_MATRIS)

# ---- slice summary: every requirement scope delivered in the slice and every experiment active in it ----
o_rows, o_details = [], []
level_of = {r["id"]: r["level"] for r in rows}
for sl in slices:
    sl = int(sl)
    in_sl = [(r["id"], x) for r in rows for x in scopes(r["id"]) if x["dilim"] == sl]
    must = sum(1 for rid, _ in in_sl if level_of[rid] == "MUST")
    should = len(in_sl) - must
    whole = sum(1 for rid, x in in_sl if x["id"] == rid)
    ats = [a for a in ATMETA if sl in active_slices(a)]

    def at_ref(a):
        tag = "" if ATMETA[a]["dilim"] == sl else " (parça)"
        return f'<a class="rid" href="#{a}">{a}</a>{tag}'
    gates = " ".join(at_ref(a) for a in ats if a in gate_at) or "—"
    others = " ".join(at_ref(a) for a in ats if a not in gate_at) or "—"
    o_rows.append(f'<tr><td>Dilim {sl}</td><td>{must} MUST, {should} SHOULD kapsam ({whole} tek dilimli satır, {len(in_sl) - whole} alt kapsam)</td><td>{gates}</td><td>{others}</td></tr>')
    o_details.append(f'<p style="margin-top:.5rem"><b>Dilim {sl}:</b> ' + " ".join(
        f'<a class="rid" href="#{x["id"]}">{x["id"]}</a>' for _, x in in_sl) + "</p>")
DILIM_OZET = f'''<div class="tbl-wrap" style="margin-top:1rem"><table class="matrix prose">
    <thead><tr><th scope="col">Dilim</th><th scope="col">Teslim edilen kapsam</th><th scope="col">Yayın kapısı deneyleri</th><th scope="col">Diğer deneyler</th></tr></thead>
    <tbody>
      {chr(10).join(o_rows)}
    </tbody>
  </table></div>
  <details class="appendix">
    <summary>Dilimlere göre kapsam listesini aç</summary>
    <div style="padding:0 1rem 1rem">{"".join(o_details)}</div>
  </details>'''
body = body.replace("{{DILIM_OZET}}", DILIM_OZET)

# ---- contract appendix: examples, fingerprint vectors and Run states from one fixture, re-verified here ----
FX = load("sozlesme-fixture.json")
_e5 = re.search(r'<tr id="E5".*?İstemcinin ayırt ettiği durumlar: ([a-z_, ]+)\.', body, re.S)
E5_STATES = _e5.group(1).split(", ") if _e5 else []
if not E5_STATES:
    errors.append("E5 state list not found")
ERROR_CODES = set(re.findall(r'<tr><td>([a-z_]+)</td><td>\d{3}</td>', body))
errors.extend(sozlesme.verify(FX, E5_STATES, ERROR_CODES))


def pre_json(obj, head=""):
    txt = (head + "\n" if head else "") + json.dumps(obj, ensure_ascii=False, indent=2)
    return f"<pre><code>{esc(txt)}</code></pre>"


API = "POST /api/v2/method/genui.api.v1."
body = body.replace("{{SZ_MANIFEST}}", pre_json(FX["manifest"]))
body = body.replace("{{SZ_CONTEXT}}", pre_json(FX["context"]))
body = body.replace("{{SZ_START}}", pre_json(FX["start_req"], API + "runs.start") + pre_json(FX["start_res"], "Yanıt (202)"))
body = body.replace("{{SZ_CHANGESET}}", pre_json(FX["changeset"], "GET /api/v2/method/genui.api.v1.changesets.get?changeset_id=CS-2026-00418"))
body = body.replace("{{SZ_APPROVE}}", pre_json(FX["approve_req"], API + "changesets.approve") + pre_json(FX["approve_res"], "Yanıt (200)"))
body = body.replace("{{SZ_RESULT}}", pre_json(FX["result"], "GET /api/v2/method/genui.api.v1.runs.get?run_id=RUN-2026-00418"))
body = body.replace("{{SZ_SPEC}}", pre_json(FX["spec"]))
_P = sozlesme.projections(FX)
_vals = {"schema_fingerprint": sozlesme.fp(_P["schema"]()), "context_manifest_fingerprint": sozlesme.fp(_P["context"]()),
         "params_fingerprint": sozlesme.fp(_P["params"]()), "changeset fingerprint": sozlesme.fp(_P["changeset"]()),
         "approval_fingerprint": sozlesme.fp(_P["approval"]()), "quote_fingerprint": "alıntı tablosunda"}
def _val_cell(v):
    return f'<code class="hash">{v}</code>' if sozlesme.HEX64.match(v) else esc(v)


pj_rows = "".join(f'<tr><td>{esc(n)}</td><td>{esc(g)}</td><td>{esc(f)}</td><td>{esc(k)}</td><td>{_val_cell(_vals[n])}</td></tr>'
                  for n, g, f, k in sozlesme.PROJECTION_DOC)
body = body.replace("{{SZ_PROJEKSIYON}}", f'''<div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose">
    <thead><tr><th scope="col">Parmak izi</th><th scope="col">Girdi</th><th scope="col">Giren alanlar</th><th scope="col">Sıralama ve eksik alan</th><th scope="col">Bu örnekteki değer</th></tr></thead>
    <tbody>{pj_rows}</tbody>
  </table></div>''')
q_rows = "".join(
    f'<tr><td>{esc(q["source"])} s. {q["page"]}</td><td><code>{esc(sozlesme.jcs(_P["quote"](q)))}</code></td>'
    f'<td><code class="hash">{sozlesme.fp(_P["quote"](q))}</code></td></tr>' for q in FX["alintilar"])
body = body.replace("{{SZ_ALINTI}}", f'''<p style="margin-top:.8rem">Kanonik metin örneği: alıntı parmak izinin girdisi ve sonucu. Bir uygulama bu üç satırı birebir üretmiyorsa kanonikleştirmesi yanlıştır.</p>
  <div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose">
    <thead><tr><th scope="col">Alıntı</th><th scope="col">RFC 8785 kanonik metni</th><th scope="col">SHA-256</th></tr></thead>
    <tbody>{q_rows}</tbody>
  </table></div>''')
g_rows = "".join(f'<tr><td>{esc(g["yapi"])}</td><td>{esc(g["degisiklik"])}</td><td>{esc(g["hata"])}</td><td>{esc(g["not"])}</td></tr>'
                 for g in FX["gecersiz"])
body = body.replace("{{SZ_GECERSIZ}}", f'''<div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose">
    <thead><tr><th scope="col">Yapı</th><th scope="col">Geçerli örnekten farkı</th><th scope="col">Beklenen hata kodu</th><th scope="col">Not</th></tr></thead>
    <tbody>{g_rows}</tbody>
  </table></div>''')
r_rows = "".join(f'<tr><td>{esc(r["durum"])}</td><td>{esc(r["anlam"])}</td><td>{esc(r["kim"])}</td>'
                 f'<td>{esc(", ".join(r["sonraki"]) or "—")}</td><td>{esc(r["arayuz"])}</td></tr>' for r in FX["run_durumlari"])
body = body.replace("{{SZ_RUN}}", f'''<div class="tbl-wrap" style="margin-top:.6rem"><table class="matrix prose">
    <thead><tr><th scope="col">Durum</th><th scope="col">Anlamı</th><th scope="col">Kim geçirir</th><th scope="col">Sonraki durumlar</th><th scope="col">Arayüz</th></tr></thead>
    <tbody>{r_rows}</tbody>
  </table></div>
  <p style="margin-top:.5rem">Bu örneğin yolu: {" → ".join(FX["ornek_yol"])}.</p>''')

# ---- glossary ----
SOZ = load("sozluk.json")
terms = sorted(SOZ["terimler"], key=lambda t: t["terim"].replace("İ", "I").replace("Ş", "S").replace("Ç", "C").replace("Ö", "O").replace("Ü", "U").replace("Ğ", "G").lower())


def slug(s):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return "t-" + re.sub(r"[^a-z0-9]+", "-", s.translate(tr).lower()).strip("-")


seen_slugs = set()
dl_items = []
for t in terms:
    t["slug"] = slug(t["terim"])
    if t["slug"] in seen_slugs:
        errors.append(f"duplicate glossary slug {t['slug']}")
    seen_slugs.add(t["slug"])
    variants = [t["terim"]] + t.get("esanlam", [])
    cok = '<span class="cok">çok anlamlı</span>' if t.get("cok_anlamli") else ""
    dl_items.append(f'<div><dt id="{t["slug"]}" data-esanlam="{esc("|".join(variants))}">{esc(t["terim"])}{cok}</dt>'
                    f'<dd>{esc(t["tanim"])}</dd></div>')
SOZLUK = f'''<details class="appendix" id="sozluk-kutu">
    <summary>Sözlüğü aç ({len(terms)} terim)</summary>
    <dl class="sozluk" id="sozluk">
      {chr(10).join(dl_items)}
    </dl>
  </details>'''
body = body.replace("{{SOZLUK}}", SOZLUK)

# first use of each term after the reading section links to its glossary entry
SKIP_TAGS = {"a", "code", "pre", "script", "style", "svg", "h1", "h2", "h3", "h4", "button", "summary", "label",
             "th", "abbr", "dt", "textarea", "title", "b"}
SKIP_CLASSES = {"dec", "ph", "tst", "kps", "onay", "chip", "n", "lab", "st", "v", "rid", "k", "docid"}
variant_map = {}
for t in terms:
    for v in [t["terim"]] + t.get("esanlam", []):
        variant_map[v] = t
pending = dict(variant_map)
start = body.find('<section id="karar">')
end = body.find("</main>")
head_part, mid, tail_part = body[:start], body[start:end], body[end:]
tokens = re.split(r"(<[^>]+>)", mid)
stack = []
linked = 0


def boundary_re(vs):
    alts = "|".join(re.escape(v) for v in sorted(vs, key=len, reverse=True))
    return re.compile(rf"(?<![\w@/.#-])({alts})(?![\w-])")


rx = boundary_re(pending) if pending else None
out = []
for tok in tokens:
    if tok.startswith("<"):
        mt = re.match(r"<\s*(/)?\s*([a-zA-Z0-9]+)([^>]*)>", tok)
        if mt:
            closing, tag, attrs = mt.group(1), mt.group(2).lower(), mt.group(3)
            void = tag in {"br", "hr", "img", "input", "meta", "link", "path", "line", "rect", "circle",
                           "polyline", "polygon", "ellipse", "stop", "use", "col", "wbr", "source"} or attrs.rstrip().endswith("/")
            if closing:
                while stack:
                    t_, _ = stack.pop()
                    if t_ == tag:
                        break
            elif not void:
                cls = re.search(r'class="([^"]*)"', attrs)
                classes = set(cls.group(1).split()) if cls else set()
                skip = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES) or (tag == "td" and "id" in classes)
                stack.append((tag, skip))
        out.append(tok)
        continue
    if not tok.strip() or any(sk for _, sk in stack) or not pending:
        out.append(tok)
        continue
    pos, piece = 0, []
    while rx is not None:
        m = rx.search(tok, pos)
        if not m:
            break
        v = m.group(1)
        t = variant_map[v]
        piece.append(tok[pos:m.start()])
        piece.append(f'<a class="terim" href="#{t["slug"]}" title="{esc(t["tanim"])}">{v}</a>')
        linked += 1
        pos = m.end()
        for vv in [t["terim"]] + t.get("esanlam", []):
            pending.pop(vv, None)
        rx = boundary_re(pending) if pending else None
    piece.append(tok[pos:])
    out.append("".join(piece))
body = head_part + "".join(out) + tail_part

# ---- icons and placeholders ----
body = re.sub(r"\{\{icon:([a-z0-9-]+)(?:\|([a-z0-9 -]+))?\}\}", icon, body)
leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", body)
if leftover:
    errors.append("unfilled placeholders: " + " ".join(leftover))

# approval wording outside the conflict table must point to a record that is still pending
PENDING = {c["id"] for c in CK if c["onay"]["durum"] == "onay bekliyor"}
_scan = body
for _sec in ("celiskiler-bolum", "kitap-sonuc", "gunluk"):
    _scan = re.sub(rf'<(section|div) id="{_sec}".*?</\1>', " ", _scan, flags=re.S)
_scan = re.sub(r'<h3 id="celiskiler".*?</table></div>', " ", _scan, flags=re.S)
for _m in re.finditer(r"onay bekl\w*", _scan):
    # records named after the wording must still be pending
    _refs = re.findall(r"ck-[a-z0-9-]+", _scan[_m.start():_m.start() + 220])
    _stale = [r for r in _refs if r not in PENDING and r in CK_IDS]
    # an annotation such as "(ck-x, onay bekliyor)" must name a pending record on either side
    _annot = re.match(r"onay bekliyor\)|onay bekliyor</a>|onay bekleyen öneri \(", _scan[_m.start():_m.start() + 40])
    _near = re.findall(r"ck-[a-z0-9-]+", _scan[max(0, _m.start() - 160):_m.start() + 220])
    if _stale or (_annot and not any(r in PENDING for r in _near)):
        errors.append("stale approval wording: " + re.sub(r"<[^>]+>", "", _scan[max(0, _m.start() - 80):_m.start() + 60]).strip())

# references to the contract appendix ("ek N: Başlık") must name the right example
_ek_titles = {n: t for n, t in re.findall(r'<h3 id="ek-(\d)"[^>]*>\d · ([^<]+)</h3>', body)}
for _n, _t in re.findall(r'<a href="#ek-(\d)">ek \d: ([^<]+)</a>', body):
    if _ek_titles.get(_n, "").strip() != _t.strip():
        errors.append(f"appendix reference 'ek {_n}: {_t}' does not match heading '{_ek_titles.get(_n)}'")

# every decision-book target must exist in the final page
ids = set(re.findall(r'\sid="([^"]+)"', body))
bad_targets = [f"{q}->{t}" for q, t in k_targets if t not in ids]
if bad_targets:
    errors.append("decision book targets not found: " + " ".join(bad_targets))

print("requirements:", len(rows), "MUST:", n_must, "slices:", " ".join(slices),
      "rows by first slice:", {sl: sum(1 for r in rows if r["dilim"] == int(sl)) for sl in slices},
      "scopes per slice:", {sl: sum(1 for r in rows for x in scopes(r["id"]) if x["dilim"] == int(sl)) for sl in slices})
print("conflicts:", len(CK), "pending approval:", sum(1 for c in CK if c["onay"]["durum"] == "onay bekliyor"),
      "contract fixture fingerprints verified")
print("experiments:", len(seen_at), "gates:", len(gate_at))
print("trace:", counts, "deviations:", n_dev)
print("guide trace:", g_counts)
print("decision book:", k_counts)
print("glossary terms:", len(terms), "first-use links:", linked)
if unmapped:
    print("UNMAPPED decisions:", " ".join(unmapped))
if g_unmapped:
    print("UNMAPPED guide decisions:", " ".join(g_unmapped))
if unknown:
    print("UNKNOWN dec tags:", sorted(unknown))
if errors:
    raise SystemExit("build failed:\n  " + "\n  ".join(errors))

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

# tool-neutral requirement export (decision book E05: the tracker is still open)
export = {
    "kind": "genui-gereksinimler", "schemaVersion": 1, "source": REPO_OUT.name,
    "requirements": [{
        "id": r["id"], "group": r["id"][0], "level": r["level"], "slice": r["dilim"],
        "slices": [x["dilim"] for x in scopes(r["id"])], "actor": r["actor"],
        "title": plain(r["title"]), "requirement": plain(r["req"]), "note": plain(r["note"]),
        "tests": LINKS.get(r["id"], []), "decisions": r["tags"],
        "scopes": [{"id": x["id"], "slice": x["dilim"], "scope": x["kapsam"], "tests": x["test"]} for x in SUBS.get(r["id"], [])],
        "pendingApprovals": pending_by_target.get(r["id"], []),
    } for r in rows],
    "experiments": [{"id": a, **ATMETA[a], "gate": a in gate_at,
                     "proves": [x["id"] for _, x in proves.get(a, [])]} for a in seen_at],
    "conflicts": CK,
}
json_out = REPO_OUT.parent / "gereksinimler.json"
json_out.write_text(json.dumps(export, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {json_out}")
if ART_OUT:
    ART_OUT.write_text(f"{head_common}\n{body}\n", encoding="utf-8")
    print(f"wrote {ART_OUT}")
