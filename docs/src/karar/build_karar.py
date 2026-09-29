#!/usr/bin/env python3
"""Karar kitabını soru bankasından üretir ve doğrular.

Kullanım:
  python3 docs/src/karar/build_karar.py docs/karar-kitabi.html

Girdiler (bu klasörde): ortak.py (bölümler, S ve O), sorular_1.py, sorular_2.py, sorular_3.py,
sablon.html, kitap.css, kitap.js; ikonlar ../icons/*.svg (Phosphor, MIT).
Çıktı: tek dosyalık HTML. Soru bankası sayfaya JSON olarak gömülür; sayfa cevapları
"genui-karar-kitabi-yanitlari" türünde JSON olarak dışa aktarır.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ortak import BOLUMLER  # noqa: E402
import sorular_1, sorular_2, sorular_3  # noqa: E402

KITAP_SURUM = "1.0"
TARIH = "29 Eylül 2026"
BELGE_SURUM = "v2.5"
KAYNAK_COMMIT = "c19bfca"

SORULAR = sorular_1.SORULAR + sorular_2.SORULAR + sorular_3.SORULAR

SOZLUK = [
    ("ADR", "Mimari karar kaydı: bir kararın ne olduğu, neden alındığı ve alternatifleri. Bu kitaptaki not alanları ADR'lere girer."),
    ("AT (kabul deneyi)", "Bir gereksinimin gerçekten sağlandığını gösteren deney. Örnek: AT-18 kimlik köprüsünün kurcalanmış girişleri reddettiğini sınar."),
    ("BFF", "Backend for frontend: tarayıcı ile Frappe arasındaki kenar katmanı. Bu projede ayrı bir servis değil; aynı adresteki ters vekil, API sözleşmesi ve kimlik köprüsü."),
    ("Capability (yetenek)", "Sistemin yapabildiği, izinle korunan tek bir iş. Örnek: \"seçili ürünlerin açıklamasını güncelle\". Kullanıcı, YZ ve ajan aynı yeteneği çağırır."),
    ("ChangeSet", "YZ'nin önerdiği değişikliklerin listesi: hangi kayıtta hangi alan eskiden neydi, ne olacak. Kullanıcı bunu görüp onaylar."),
    ("CI", "Kod gönderildiğinde testleri otomatik çalıştıran süreç (bu projede GitHub Actions)."),
    ("Colima", "Mac'te container çalıştırmak için kullandığın hafif araç; Docker Desktop yerine."),
    ("Desk", "Frappe'nin hazır yönetim arayüzü. Yeni arayüz bunun yerine geçiyor."),
    ("DocType", "Frappe'de bir veri tablosunun tanımı. Örnek: Ürün, Müşteri, Fatura."),
    ("Frappe", "Backend çatısı: veri, iş kuralları, yetki ve belge yaşam döngüsü buradadır."),
    ("Grant", "Kullanıcının YZ'ye önceden verdiği sınırlı yetki. Örnek: \"bu hafta, en fazla 50 üründe açıklama alanını onaysız düzeltebilirsin\"."),
    ("Hook", "Frappe'de bir kayıt kaydedilince otomatik çalışan iş kuralı (bildirim göndermek, stok düşmek gibi)."),
    ("Kill switch", "YZ özelliklerini tek hamlede kapatan acil düğme; klasik ekranlar çalışmaya devam eder."),
    ("KYC / KYB", "Müşterini tanı: kişinin (KYC) veya şirketin (KYB) kimliğini belgeyle doğrulama."),
    ("MUST / SHOULD / MAY", "Zorunlu / güçlü öneri / isteğe bağlı. RFC 2119 standardındaki seviye adları."),
    ("Origin", "Protokol, alan adı ve portun üçü birden. app.alanadın ve www.alanadın farklı origin'lerdir."),
    ("P1 / P2", "Bu kitaptaki öncelik: P1 uygulamaya başlamadan çözülmeli; P2 tasarım ve test planı kesinleşirken çözülebilir."),
    ("Passkey", "Parola yerine telefonun veya bilgisayarın parmak izi, yüz tanıma ya da PIN kilidiyle giriş."),
    ("PKCE", "Giriş akışında çalınan kodun başkası tarafından kullanılmasını önleyen güvenlik adımı."),
    ("Run", "Uzun süren bir YZ işinin kaydı: adımları, durumu ve sonucu. Sekme kapansa da sürer."),
    ("Stub (taklit)", "Test için gerçeğinin yerine konan basit parça. Örnek: her seferinde aynı cevabı veren sahte model."),
    ("Tenant", "Sistemi kullanan müşteri şirket. Tenant modeli, müşterilerin birbirinden nasıl ayrıldığıdır."),
    ("Tekrar koruması (idempotency)", "Aynı istek iki kez gelse bile işlemin bir kez yapılması. Örnek: ödeme düğmesine iki kez basınca tek ödeme."),
    ("UI Spec", "YZ'nin ürettiği ekran tanımı. Kod değil, onaylı bileşen listesinden seçim yapan bir JSON belgesi."),
    ("White-label", "Ürünün müşterinin markasıyla görünmesi: logo, renk, ad, gerekirse alan adı."),
    ("YZ", "Yapay zekâ."),
]

ICON_JS = ["star", "lightbulb", "info", "hourglass-medium", "note-pencil", "check-circle", "circle-dashed"]

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800'
    '&family=Roboto:wght@300;400;500&family=Roboto+Mono:wght@400&display=swap">'
)

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def fail(msg):
    raise SystemExit("karar kitabı doğrulaması başarısız: " + msg)


def validate():
    ids = set()
    chapters = {b[0] for b in BOLUMLER}
    for q in SORULAR:
        qid = q["id"]
        if qid in ids:
            fail(f"yinelenen soru kimliği {qid}")
        ids.add(qid)
        if q["bolum"] not in chapters:
            fail(f"{qid}: bilinmeyen bölüm {q['bolum']}")
        if q["oncelik"] not in ("P1", "P2") or q["kime"] not in ("sen", "teknik") or q["tip"] not in ("tek", "cok"):
            fail(f"{qid}: öncelik, karar sahibi veya tip geçersiz")
        for field in ("soru", "neden"):
            if not q[field].strip():
                fail(f"{qid}: {field} boş")
        if not q["kaynak"]:
            fail(f"{qid}: kaynak yok")
        if len(q["secenekler"]) < 2:
            fail(f"{qid}: en az iki seçenek gerekir")
        oids = [o["id"] for o in q["secenekler"]]
        if len(set(oids)) != len(oids):
            fail(f"{qid}: yinelenen seçenek kimliği")
        for o in q["secenekler"]:
            for field in ("etiket", "aciklama", "ornek", "sonuc"):
                if not o[field].strip():
                    fail(f"{qid}/{o['id']}: {field} boş (her seçeneğin gerçek dünya örneği ve etkisi olmalı)")
        for r in q["oneri"]:
            if r not in oids:
                fail(f"{qid}: önerilen seçenek {r} yok")
        if q["tip"] == "tek" and len(q["oneri"]) > 1:
            fail(f"{qid}: tek seçimli soruda birden çok öneri")
        if not q["oneri"] and not q["oneri_neden"]:
            fail(f"{qid}: öneri yoksa nedeni yazılmalı")
        text = json.dumps(q, ensure_ascii=False)
        if EMOJI.search(text):
            fail(f"{qid}: emoji kullanılmamalı")
    for q in SORULAR:
        g = q["goster"]
        if g:
            dep = next((x for x in SORULAR if x["id"] == g["soru"]), None)
            if not dep:
                fail(f"{q['id']}: koşul sorusu {g['soru']} yok")
            for v in [g["iceren"]] if isinstance(g["iceren"], str) else g["iceren"]:
                if v not in [o["id"] for o in dep["secenekler"]]:
                    fail(f"{q['id']}: koşul seçeneği {v} {g['soru']} içinde yok")
    for b in BOLUMLER:
        if not any(q["bolum"] == b[0] for q in SORULAR):
            fail(f"bölüm {b[0]} boş")


def icon_svg(name, extra=""):
    raw = (HERE.parent / "icons" / f"{name}.svg").read_text(encoding="utf-8").strip()
    inner = re.sub(r"</svg>$", "", re.sub(r"^<svg[^>]*>", "", raw)).strip()
    return f'<svg class="ico{extra}" viewBox="0 0 256 256" aria-hidden="true" focusable="false">{inner}</svg>'


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out = pathlib.Path(sys.argv[1])
    validate()
    meta = {
        "title": "GenUI Karar Kitabı", "bookVersion": KITAP_SURUM, "date": TARIH,
        "basedOn": {"document": "GENUI-FE-REQ " + BELGE_SURUM, "sourceCommit": KAYNAK_COMMIT,
                    "reports": ["Claude v2.5 zayıflık raporu", "Codex v2.5 yeterlilik raporu (D01–D15)",
                                "Keycloak v2.3 inceleme raporu (R1–R10)"]},
        "questionCount": len(SORULAR),
    }
    veri = {
        "meta": meta,
        "bolumler": [{"id": b[0], "baslik": b[1], "aciklama": b[2]} for b in BOLUMLER],
        "sorular": SORULAR,
        "ikonlar": {n: icon_svg(n) for n in ICON_JS},
    }
    veri_json = json.dumps(veri, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    sozluk = "\n".join(
        f'    <div><dt>{html.escape(t)}</dt><dd>{html.escape(a)}</dd></div>' for t, a in SOZLUK)
    page = (HERE / "sablon.html").read_text(encoding="utf-8")
    repl = {
        "{{FONTS}}": FONTS,
        "{{STYLE}}": (HERE / "kitap.css").read_text(encoding="utf-8"),
        "{{SCRIPT}}": (HERE / "kitap.js").read_text(encoding="utf-8"),
        "{{VERI}}": veri_json,
        "{{SOZLUK}}": sozluk,
        "{{KITAP_SURUM}}": KITAP_SURUM, "{{TARIH}}": TARIH, "{{BELGE_SURUM}}": BELGE_SURUM,
        "{{KAYNAK_COMMIT}}": KAYNAK_COMMIT, "{{SORU_SAYISI}}": str(len(SORULAR)),
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    page = re.sub(r"\{\{icon:([a-z0-9-]+)\}\}", lambda m: icon_svg(m.group(1)), page)
    left = re.findall(r"\{\{[A-Za-z_:-]+\}\}", page)
    if left:
        fail("doldurulmamış yer tutucu: " + " ".join(left))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    per = {}
    for q in SORULAR:
        per.setdefault(q["bolum"], [0, 0])
        per[q["bolum"]][0 if q["oncelik"] == "P1" else 1] += 1
    print(f"sorular: {len(SORULAR)}  P1: {sum(1 for q in SORULAR if q['oncelik'] == 'P1')}  "
          f"koşullu: {sum(1 for q in SORULAR if q['goster'])}  önerisiz: {sum(1 for q in SORULAR if not q['oneri'])}")
    print("bölüm başına (P1, P2):", per)
    print(f"yazıldı: {out} ({len(page.encode('utf-8'))} bayt)")


if __name__ == "__main__":
    main()
