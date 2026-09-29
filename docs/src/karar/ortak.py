"""Karar kitabı için ortak veri yapıları ve bölüm tanımları."""

BOLUMLER = [
    ("urun", "Ürün ve kapsam",
     "Ana projenin ne olduğu, kimin için olduğu ve ilk olarak neyi teslim edeceği. Buradaki cevaplar diğer bölümlerdeki bazı soruları gösterir veya gizler; bu yüzden önce bu bölümü doldur."),
    ("celiski", "Belgedeki çelişkiler",
     "Belgenin iki farklı yerinde iki farklı şey söylediği konular. Seçtiğin kural tek kural olur; diğer metin ona göre düzeltilir."),
    ("yz", "YZ öncelikli deneyim",
     "Yapay zekânın ürünün içinde ne yapacağı, nerede duracağı ve başarısının nasıl ölçüleceği. AI-first iddiasının kanıtı bu bölümde."),
    ("kimlik", "Kimlik ve Keycloak",
     "Keycloak raporundaki R1–R10 bulguları v2.4 ve v2.5'te kapatıldı. Bu bölüm kalan açık kimlik kararlarını, hesap yaşam döngüsünün eksik uçlarını ve kapanan bulguların geri gelmemesi için önlemleri soruyor."),
    ("veri", "Veri ve sözleşmeler",
     "Ekiplerin aynı veri yapısını, aynı yazma yolunu ve aynı kurtarma kuralını kullanması için gereken kararlar. Senin \"önce test, sonra veri şeması\" kuralının şema adımı burada."),
    ("kalite", "Test, ölçüm ve yayın",
     "Bir işin ne zaman \"bitti\" sayılacağı ve yayının neye göre durdurulacağı."),
    ("ekip", "Ekip ve belge düzeni",
     "Kimin yapacağı, kimin karar vereceği ve ana projenin belgelerinin nasıl düzenleneceği."),
    ("kayit", "Karar kaydındaki iddialı seçimler",
     "Karar kaydında 74 kararda seçim kaydın kendi önerisinden farklı ve gerekçesi yazılmamış. En etkili olanlar burada: seçimi koru ya da öneriye dön. Not alanına kısa bir gerekçe yazarsan ADR'ye girer."),
    ("teknik", "Teknik varsayılanlar",
     "Mühendislik ayrıntısı olan kararlar. Önerilen varsayılanı onaylaman yeterli; emin değilsen \"teknik inceleyiciyle sonra karar\" seç."),
]


def O(id, etiket, aciklama, ornek, sonuc):
    """Bir seçenek: kısa ad, ne anlama geldiği, gerçek dünya örneği, seçilirse belgeye etkisi."""
    return {"id": id, "etiket": etiket, "aciklama": aciklama, "ornek": ornek, "sonuc": sonuc}


def S(id, bolum, oncelik, kime, soru, neden, secenekler, oneri=None, oneri_neden="",
      kaynak=(), etkiler=(), tip="tek", serbest=False, goster=None):
    """Bir soru.

    oncelik: P1 (uygulamadan önce çözülmeli) veya P2 (tasarım ve test planı kesinleşirken)
    kime:    "sen" (ürün kararı) veya "teknik" (önerilen teknik varsayılan; onay yeterli)
    tip:     "tek" (tek seçim) veya "cok" (çoklu seçim)
    goster:  {"soru": id, "iceren": seçenek id'si veya listesi}; koşul tutmazsa soru gizlenir
    """
    return {
        "id": id, "bolum": bolum, "oncelik": oncelik, "kime": kime, "soru": soru, "neden": neden,
        "secenekler": list(secenekler), "oneri": list(oneri) if oneri else [], "oneri_neden": oneri_neden,
        "kaynak": list(kaynak), "etkiler": list(etkiler), "tip": tip, "serbest": serbest, "goster": goster,
    }
