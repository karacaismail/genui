# genui

Ant Design + Frappe Framework merkezli, Keycloak kimlikli, yapay zekâ öncelikli (AI-first) bir headless yönetim paneli için GenUI (generative UI, üretken arayüz) frontend gereksinim sözleşmesi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html): karar, açık kararlar, varsayılan yolculuk, katman mimarisi, mekanizma diyagramları, kimlik ve white-label, MUST/SHOULD gereksinimleri (13 grup), teknoloji seçimi, kabul deneyleri (AT-01–AT-23), aşamalı plan, karar izlenebilirliği ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.
- Yayın adresi: https://karacaismail.github.io/genui/

## Temel karar

Frappe iş kurallarının, yetkinin, doğrulamanın ve belge yaşam döngüsünün otoritesidir; frontend Frappe ile yalnızca aynı origin'deki sürümlü API sözleşmesi üzerinden ve DocType metadata'sından üretilen tipli şemalarla konuşur. Ant Design standart sunum aracıdır; antd prop'ları katalog, capability ve görev durumu sözleşmelerine girmez. Model kod, HTML, ham SQL veya serbest URL üretmez; capability manifest'inden eylem, onaylı renderer kataloğundan bileşen seçer.

Her yazma Frappe'de yetkili bir capability çağrısıdır ve üç biçimden biriyle başlar: kullanıcının kendi eylemi, o değişiklik için verilen onay, ya da kullanıcının önceden verdiği sınırlı yetki (grant). İnsan onayı risk sınıfına göre istenir; onaylanan revizyon uygulama anında Frappe içinde yeniden doğrulanır.

## Kimlik, oturum ve white-label

Kimlik Keycloak'ta, oturum ve yetki Frappe'de durur. Giriş her zaman Keycloak sayfasında, yetkilendirme kodu akışı + PKCE ile yapılır; Frappe'ye giriş platformun kendi kimlik köprüsüyle (Frappe custom app) açılır. SPA'lar, Frappe API'si ve köprü aynı origin'de sunulur; tarayıcı token taşımaz, oturum Frappe'nin HttpOnly çerezindedir. Şirket üyeliği, uygulama yetkisi ve KYC/KYB Frappe'de her istekte canlı kontrol edilir.

Giriş ve kayıt ekranları Keycloakify ile aynı tasarım token'larından üretilir; tek token kaynağı panel, giriş, e-posta ve herkese açık içeriği besler. White-label üç seviyede tanımlıdır (ürün markası, müşteri markası, müşteri alan adı); seviye 1 bağlayıcıdır, üst seviyeler tenant modeli kararına bağlıdır. Model kimlik ekranı üretmez, kimlik bilgisine ve KYC belgesine erişmez, adım yükseltmeyi atlayamaz.

## Kaynaklar arası öncelik

Karar kaydındaki seçimler bağlayıcıdır; kaydın önerileri ve kaynağın kendi iç çelişkileri belgede ayrı bir "Açık kararlar" bölümünde durur. Tek istisna kimlik ve oturumdur: daha yeni ve alana özel kimlik rehberinin "Kararlaştırıldı" satırları, karar kaydının "ayrı origin + BFF session" seçiminin yerini alır. Bu istisna ve yeniden açılan tenant modeli, ADR ile kapanana kadar Açık kararlar'da görünür kalır.

Dayanak: Frappe Headless Platform karar kaydı (139 karar, katalog 2026-09-19.2, hedef Frappe v16.35.0) ve Keycloak + Headless Frappe kimlik rehberi (hedef Keycloak 26.7).
