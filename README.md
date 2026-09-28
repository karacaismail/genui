# genui

Ant Design + Frappe Framework merkezli, Keycloak kimlikli, yapay zekâ öncelikli (AI-first) bir headless yönetim paneli için GenUI (generative UI, üretken arayüz) frontend gereksinim sözleşmesi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html): karar, açık kararlar, varsayılan yolculuk, katman mimarisi, mekanizma diyagramları, kimlik ve white-label, 131 MUST/SHOULD gereksinimi (13 grup), teknoloji seçimi, kabul deneyleri (AT-01–AT-25), aşamalı plan, karar izlenebilirliği ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.
- [docs/src](docs/src): belgeyi üreten kaynaklar, temizlenmiş karar verisi ve kontrol betikleri.
- Yayın adresi: https://karacaismail.github.io/genui/

## Temel karar

Frappe iş kurallarının, yetkinin, doğrulamanın ve belge yaşam döngüsünün otoritesidir; frontend Frappe ile yalnızca aynı origin'deki sürümlü API sözleşmesi üzerinden ve DocType metadata'sından üretilen tipli şemalarla konuşur. Ant Design standart sunum aracıdır; antd prop'ları katalog, capability ve görev durumu sözleşmelerine girmez. Model kod, HTML, ham SQL veya serbest URL üretmez; capability manifest'inden eylem, onaylı renderer kataloğundan bileşen seçer.

Her yazma Frappe'de yetkili bir capability çağrısıdır ve üç biçimden biriyle başlar: kullanıcının kendi eylemi, o değişiklik için verilen onay, ya da kullanıcının önceden verdiği sınırlı yetki (grant). İnsan onayı risk sınıfına göre istenir; onaylanan revizyon uygulama anında Frappe içinde yeniden doğrulanır.

## Kimlik, oturum ve white-label

Kimlik Keycloak'ta, oturum ve yetki Frappe'de durur. Giriş her zaman Keycloak sayfasında, yetkilendirme kodu akışı + PKCE ile yapılır; Frappe'ye giriş platformun kendi kimlik köprüsüyle (Frappe custom app) açılır. SPA sunan her hostta SPA'lar, Frappe API'si ve köprü aynı origin'dedir; app ve www ayrı origin'lerdir ve çerez paylaşmaz. Tarayıcı token taşımaz, oturum Frappe'nin host-only HttpOnly çerezindedir. Şirket üyeliği, uygulama yetkisi ve KYC/KYB Frappe'de her istekte canlı kontrol edilir.

Sosyal hesap, e-posta eşitliğiyle mevcut hesaba kendiliğinden bağlanmaz; mevcut hesabın kontrolü yeniden doğrulanır, ayrıcalıklı Frappe kullanıcıları yalnızca kontrollü göçle bağlanır. Tek çıkışta logout token'ı ID token'dan ayrı kurallarla doğrulanır. Çıkış, devre dışı bırakma ve üyelik iptali sunucuda yürürlüğe girer; açık realtime bağlantıları için mekanizma ve azami gecikme üretim kapısıdır.

Giriş ve kayıt ekranları Keycloakify ile aynı tasarım token'larından üretilir; tek token kaynağı panel, giriş, e-posta ve herkese açık içeriği besler. White-label üç seviyede tanımlıdır (ürün markası, müşteri markası, müşteri alan adı); seviye 1 bağlayıcıdır ve yalnızca ürün markasını teslim eder, üst seviyeler tenant modeli kararına bağlıdır. Altyapı markaları ekrandan kaldırılır; Google ve Apple giriş düğmeleri ile lisans bildirimleri korunur. Model kimlik ekranı üretmez, kimlik doğrulama sırlarına ve oturuma erişmez; KYC/KYB belgeleri veri sınıfı tablosundaki kurala göre işlenir (gerçek kişi KYC belgesi varsayılan olarak hiçbir modele gitmez).

## Kaynaklar arası öncelik

Karar kaydındaki seçimler bağlayıcıdır; kaydın önerileri ve kaynağın kendi iç çelişkileri belgede ayrı bir "Açık kararlar" bölümünde durur. Tek istisna kimlik ve oturumdur: daha yeni ve alana özel kimlik rehberinin "Kararlaştırıldı" satırları, karar kaydının "ayrı origin + BFF session" seçiminin yerini alır. Bu istisna ve yeniden açılan tenant modeli, ADR ile kapanana kadar Açık kararlar'da görünür kalır.

Dayanak: Frappe Headless Platform karar kaydı (139 karar, katalog 2026-09-19.2, hedef Frappe v16.35.0) ve Keycloak + Headless Frappe kimlik rehberi (hedef Keycloak 26.7).

## Derleme ve kontrol

Belge `docs/src` altındaki kaynaklardan üretilir; `docs/genui-frontend-gereksinimleri.html` elle düzenlenmez.

```sh
python3 docs/src/build.py docs/genui-frontend-gereksinimleri.html
python3 docs/src/qa/validate.py docs/genui-frontend-gereksinimleri.html
cd docs/src/qa && npm ci && CHROME_PATH=/yol/chromium node check.js ../../genui-frontend-gereksinimleri.html
```

`CHROME_PATH` verilmezse `check.js` kurulu Chrome'u kullanır. `validate.py` etiket dengesini, yinelenen kimlikleri, kırık yerel bağlantıları ve satır içi betiğin sözdizimini; `check.js` filtreleri, faz düğmelerini, dar ekran taşmasını, odak halkasını, azaltılmış hareketi ve izlenebilirlikteki etkin karar durumunu tarayıcıda denetler.

Karar kaydının kendisi repoda değildir. `docs/src/data/karar-kaydi.fixture.json` yalnızca izlenebilirlik tablosunda zaten yayımlanan alanları (kimlik, soru, seçim, farklıysa önerinin başlığı, durum) taşır. Sonraki bir kaynakla değişen veya yeniden açılan kararlar `docs/src/data/etkin-kararlar.json` dosyasındadır; kaynak seçim tarihçe olarak korunur.

Bu kontrollerin geçmesi yalnızca belgenin doğru üretildiğini gösterir. Belgede yazılı kabul deneyleri (AT-01–AT-25), özellikle kimlik entegrasyonu (AT-18–AT-25), çalışan bir Keycloak, Frappe ve OTP ortamı gerektirir ve bu repoda koşulmamıştır.
