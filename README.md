# genui

Ant Design + Frappe Framework merkezli, yapay zekâ öncelikli (AI-first) bir headless yönetim paneli için GenUI (generative UI, üretken arayüz) frontend gereksinim sözleşmesi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html): karar, katman mimarisi, mekanizma diyagramları, MUST/SHOULD gereksinimleri (11 grup), teknoloji seçimi, kabul deneyleri, aşamalı plan ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.
- Yayın adresi: https://karacaismail.github.io/genui/

## Temel karar

Frappe iş kurallarının, yetkinin ve verinin otoritesidir; frontend Frappe'ye yalnızca sürümlü BFF gateway üzerinden ve DocType metadata'sından üretilen tipli sözleşmeyle bağlanır. Ant Design tek bileşen kütüphanesidir ama uygulamaya yalnızca domain bileşen katmanı (`@pim/ui`) üzerinden girer. Model kod, HTML, SQL veya URL üretmez; capability manifest'inden eylem, onaylı renderer kataloğundan bileşen seçer. Yazma eylemleri ChangeSet olarak revizyona bağlı insan onayından geçer.

Dayanak: Frappe Headless Platform karar kaydı (138 karar, katalog 2026-09-19.2).
