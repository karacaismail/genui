# genui

Ant Design + Frappe Framework merkezli, Keycloak kimlikli, yapay zekâ öncelikli (AI-first) bir headless yönetim paneli için GenUI (generative UI, üretken arayüz) frontend gereksinim sözleşmesi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html) (v2.6): okuma yolu ve sözlük, karar, açık kararlar ve karar çelişkileri, karar kitabı sonuçları, varsayılan yolculuk, katman mimarisi, mekanizma diyagramları, kimlik ve white-label, ürün ailesi ve cihaz matrisi, 151 MUST/SHOULD gereksinimi (13 grup, her biri bir dikey dilime ve teste bağlı), teknoloji seçimi, test stratejisi, sözleşme eki, DocType kataloğu, API ve hata kataloğu, kabul deneyleri (AT-01–AT-39), dilim planı ve olgunluk seviyeleri, karar izlenebilirliği, değişiklik günlüğü ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.
- [docs/gereksinimler.json](docs/gereksinimler.json): gereksinimlerin ve kabul deneylerinin araçtan bağımsız JSON dökümü; iş takibi aracı seçilince (karar kitabı E05) aktarım buradan yapılır.
- [Karar Kitabı](docs/karar-kitabi.html): v2.5'teki belirsizlik, eksik ve çelişkileri kapatan 104 soru. Her seçenekte gerçek dünya örneği ve belgeye etkisi yazılıdır; cevaplar JSON olarak dışa aktarılır. Proje sahibinin 29 Eylül 2026 tarihli cevapları v2.6'ya işlendi; cevap dosyası `docs/src/data/karar-kitabi-yanitlari.json`, her cevabın belgeye nasıl işlendiği `docs/src/data/karar-kitabi-uygulama.json`. Yayın adresi: https://karacaismail.github.io/genui/karar-kitabi.html
- [docs/src](docs/src): belgeyi ve karar kitabını üreten kaynaklar, temizlenmiş karar verisi ve kontrol betikleri.
- Yayın adresi: https://karacaismail.github.io/genui/

## Temel karar

Ürün sıfırdan kurulan, Zoho benzeri bir uygulama ailesidir; Desk'ten geçiş yoktur. Frappe iş kurallarının, yetkinin, doğrulamanın ve belge yaşam döngüsünün otoritesidir (yalnız v16); frontend Frappe ile yalnızca aynı origin'deki sürümlü API sözleşmesi üzerinden ve DocType metadata'sından üretilen tipli şemalarla konuşur. Ant Design yalnızca `@genui/ui` paketinin içinde kullanılır; uygulama kodu antd'yi doğrudan görmez. Model kod, HTML, ham SQL veya serbest URL üretmez; capability manifest'inden eylem, onaylı renderer kataloğundan bileşen seçer. Faz yoktur: iş dört dikey dilimle ilerler, ilk dilim 3 ayda pilota çıkar; her hedefin dilim sonundaki olgunluk seviyesi (O1–O4) planda yazılıdır.

Her yazma Frappe'de yetkilendirilir ve üç biçimden biriyle başlar: kullanıcının kendi eylemi (doğrudan Frappe REST), o değişiklik için verilen onay, ya da kullanıcının önceden verdiği küçük ve kısa süreli yetki (grant; en fazla 50 kayıt, 4 saat). Son ikisi platformun capability yürütücüsünden geçer. İnsan onayı risk sınıfına göre istenir; onaylanan revizyon uygulama anında Frappe içinde yeniden doğrulanır; yasal belge gönderimi her belge için ayrı insan onayı ister.

## Kimlik, oturum ve white-label

Kimlik Keycloak'ta, oturum ve yetki Frappe'de durur. Giriş her zaman Keycloak sayfasında, yetkilendirme kodu akışı + PKCE ile yapılır; Frappe'ye giriş platformun kendi kimlik köprüsüyle (Frappe custom app) açılır. SPA sunan her hostta SPA'lar, Frappe API'si ve köprü aynı origin'dedir; app ve www ayrı origin'lerdir ve çerez paylaşmaz. Tarayıcı token taşımaz, oturum Frappe'nin host-only HttpOnly çerezindedir. Şirket üyeliği, uygulama yetkisi ve KYC/KYB Frappe'de her istekte canlı kontrol edilir.

Sosyal hesap, e-posta eşitliğiyle mevcut hesaba kendiliğinden bağlanmaz; mevcut hesabın kontrolü yeniden doğrulanır, ayrıcalıklı Frappe kullanıcıları yalnızca kontrollü göçle bağlanır. Göç dışındaki ilk bağ, bağlama anında alınan taze ve tek kullanımlık bir kanıt ister; Keycloak'taki eski e-posta doğrulaması yetmez. Tek çıkışta logout token'ı ID token'dan ayrı kurallarla doğrulanır. Frappe oturumunun iki sınırı vardır: etkinlikle uzayan boşta kalma süresi ve yalnızca Keycloak yeniden doğrulamasıyla yenilenen mutlak bitiş; kaçan çıkış bildiriminin azami etkisi mutlak bitiştir. Çıkış, devre dışı bırakma ve üyelik iptali sunucuda yürürlüğe girer; devre dışı bırakma dağıtık atomik bir işlem değil, önce erişimi kesen, yeniden denenen ve uzlaştırılan bir orkestrasyondur. Açık realtime bağlantılarını soket servisi periyodik yeniden doğrulamayla keser; azami gecikme 60 saniyedir. Oturum süreleri rol bazlıdır (ör. yönetici 30 dakika boşta, 8 saat mutlak).

Giriş ve kayıt ekranları Keycloakify ile aynı tasarım token'larından üretilir; tek token kaynağı panel, giriş, e-posta ve herkese açık içeriği besler. White-label üç seviyede tanımlıdır (ürün markası, müşteri markası, müşteri alan adı); seviye 2 (müşteri markası, platform alan adında) ilk teslimdedir ve tenant modeli hibrittir (varsayılan paylaşımlı site, büyük veya regüle müşteri ayrı site). Altyapı markaları ekrandan kaldırılır; Google ve Apple giriş düğmeleri ile lisans bildirimleri korunur. Model kimlik ekranı üretmez, kimlik doğrulama sırlarına ve oturuma erişmez; KYC/KYB belgeleri veri sınıfı tablosundaki kurala göre işlenir (gerçek kişi KYC belgesi dış model sağlayıcısına hiçbir zaman gitmez; kendi sunucumuzdaki modelle alan çıkarımı şirket panelden açarsa yapılır).

## Kaynaklar arası öncelik

Karar kaydındaki seçimler bağlayıcıdır; kaydın önerileri belgede ayrı bir "Açık kararlar" bölümünde durur. Kimlik ve oturumda daha yeni ve alana özel kimlik rehberinin "Kararlaştırıldı" satırları, karar kaydının "ayrı origin + BFF session" seçiminin yerini alır. En yeni kaynak karar kitabıdır: kayıtla veya rehberle çatıştığında karar kitabı geçerlidir; değişen her karar izlenebilirlik tablosunda "yerine geçti", "kapandı" veya "genişletildi" olarak görünür. Karar kitabı cevaplarının birbiriyle veya güvenlik duruşuyla çatıştığı yerler (ör. yasal belge gönderimi, dış inceleme, çöküşte tekrar, 3 aylık ilk teslim) belgedeki "Karar çelişkileri" tablosunda çözümüyle yazılıdır.

Dayanak: Frappe Headless Platform karar kaydı (139 karar, katalog 2026-09-19.2, hedef Frappe v16.35.0), Keycloak + Headless Frappe kimlik rehberi (hedef Keycloak 26.7) ve karar kitabı cevapları (29 Eylül 2026).

## Derleme ve kontrol

Belge `docs/src` altındaki kaynaklardan üretilir; `docs/genui-frontend-gereksinimleri.html` elle düzenlenmez.

Komutlar repo kökünden çalıştırılır:

```sh
python3 docs/src/build.py docs/genui-frontend-gereksinimleri.html
python3 docs/src/qa/validate.py docs/genui-frontend-gereksinimleri.html
python3 docs/src/karar/build_karar.py docs/karar-kitabi.html
cd docs/src/qa && npm ci && CHROME_PATH=/yol/chromium node check.js ../../genui-frontend-gereksinimleri.html && CHROME_PATH=/yol/chromium node check_karar.js ../../karar-kitabi.html
```

`check.js` göreli veya mutlak dosya yolunu (boşluk içeren dahil) dosya URL'sine çevirir; `http(s)://` ve `file://` adreslerini olduğu gibi kullanır; argüman yoksa veya dosya bulunamazsa 2 koduyla çıkar, bir kontrol başarısız olursa 1 koduyla. `CHROME_PATH` verilmezse kurulu Chrome'u kullanır. `docs/src/qa` içinde `npm run check` aynı kontrolü çalıştırır. `validate.py` etiket dengesini, yinelenen kimlikleri, kırık yerel bağlantıları ve satır içi betiğin sözdizimini; `check.js` filtreleri, dilim düğmelerini, karar kitabı tablosunu, sözlük bağlantılarını, test satırlarını, dar ekran taşmasını, odak halkasını, azaltılmış hareketi ve izlenebilirlikteki etkin karar durumunu tarayıcıda denetler.

`build.py` her gereksinime bir dilim (1–4) atar, her MUST satırına test bağını (`docs/src/data/test-baglari.json`) ekler ve bağsız MUST'ta, bilinmeyen test veya deneyde, uygulama kaydı olmayan karar kitabı cevabında ya da var olmayan bir maddeye giden cevapta kırılır; sözlükteki (`docs/src/data/sozluk.json`) her terimin ilk kullanımını sözlüğe bağlar ve `docs/gereksinimler.json` dökümünü yazar. `validate.py` gereksinim satırlarını dilim özniteliğinden bağımsız bulur ve her birinin geçerli bir dilim taşıdığını, her MUST'ın bir teste bağlı olduğunu, her AT-xx ve TP-xx göndermesinin hedefine gittiğini, her kısaltmanın sözlükte olduğunu ve kapanan bulguların (`docs/src/qa/kapanan-bulgular.json`: yasak ve zorunlu ifadeler) geri gelmediğini denetler; bozulmuş bir kopyada kırmızı döner. `build_karar.py` soru bankasını (`docs/src/karar/sorular_*.py`) derlerken her sorunun kaynağı, her seçeneğin gerçek dünya örneği ve etkisi, önerilerin ve koşulların geçerliliğini denetler. `check_karar.js` seçim, erteleme, toplu doldurma, JSON indirme ve geri yükleme, koşullu sorular, dar ekran ve koyu temayı tarayıcıda sınar.

Karar kaydının kendisi repoda değildir. `docs/src/data/karar-kaydi.fixture.json` yalnızca izlenebilirlik tablosunda zaten yayımlanan alanları (kimlik, soru, seçim, farklıysa önerinin başlığı, durum) taşır. Sonraki bir kaynakla değişen veya yeniden açılan kararlar `docs/src/data/etkin-kararlar.json` dosyasındadır; kaynak seçim tarihçe olarak korunur.

Bu kontrollerin geçmesi yalnızca belgenin doğru üretildiğini gösterir. Belgede yazılı kabul deneyleri (AT-01–AT-39) ve otomatik test paketleri (TP-01–TP-20) ana projenin reposunda, çalışan bir Keycloak, Frappe, model ve OTP ortamında koşar; bu repoda koşulmamıştır.
