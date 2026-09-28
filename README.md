# genui

Ant Design + Frappe Framework merkezli, yapay zekâ öncelikli (AI-first) bir headless yönetim paneli için GenUI (generative UI, üretken arayüz) frontend gereksinim sözleşmesi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html): karar, açık kararlar, varsayılan yolculuk, katman mimarisi, mekanizma diyagramları, MUST/SHOULD gereksinimleri (12 grup), teknoloji seçimi, kabul deneyleri, aşamalı plan, karar izlenebilirliği ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.
- Yayın adresi: https://karacaismail.github.io/genui/

## Temel karar

Frappe iş kurallarının, yetkinin, doğrulamanın ve belge yaşam döngüsünün otoritesidir; frontend Frappe'ye yalnızca sürümlü BFF gateway üzerinden ve DocType metadata'sından üretilen tipli sözleşmeyle bağlanır. Ant Design standart sunum aracıdır; antd prop'ları katalog, capability ve görev durumu sözleşmelerine girmez. Model kod, HTML, ham SQL veya serbest URL üretmez; capability manifest'inden eylem, onaylı renderer kataloğundan bileşen seçer.

Her yazma Frappe'de yetkili bir capability çağrısıdır ve üç biçimden biriyle başlar: kullanıcının kendi eylemi, o değişiklik için verilen onay, ya da kullanıcının önceden verdiği sınırlı yetki (grant). İnsan onayı risk sınıfına göre istenir; onaylanan revizyon uygulama anında Frappe içinde yeniden doğrulanır.

Karar kaydındaki seçimler bağlayıcıdır; kaydın önerileri ve kaynağın kendi iç çelişkileri belgede ayrı bir "Açık kararlar" bölümünde durur.

Dayanak: Frappe Headless Platform karar kaydı (139 karar, katalog 2026-09-19.2, hedef Frappe v16.35.0).
