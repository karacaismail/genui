# genui

Ant Design merkezli, AI-first UX zorunlu bir SaaS yönetim paneli için GenUI (generative UI, üretken arayüz) frontend mimarisi.

## Belgeler

- [GenUI Frontend Gereksinimleri](docs/genui-frontend-gereksinimleri.html): karar, katman mimarisi, MUST/SHOULD gereksinimleri, teknoloji seçimi, kabul deneyleri ve kaynaklar. Tek dosya HTML; tarayıcıda doğrudan açılır.

## Temel karar

Ant Design tek bileşen kütüphanesidir ama uygulamaya yalnızca tek sarmalayıcı paket (`@pim/ui`) üzerinden girer. Model kod, HTML veya URL üretmez; sürümlenmiş bir bileşen kataloğundan seçer. Yetkilendirme ve iş kuralı sunucudadır; yazma eylemleri öneri + insan onayı ile geçer. A2UI, AG-UI ve json-render yalnızca değiştirilebilir adaptörlerdir.
