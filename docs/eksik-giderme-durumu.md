# Eksik giderme süreci — 20 Ekim 2026

## Durum

İlk incelemede **31** eksik tespit edilmiştir (7 P0, 17 P1, 7 P2).
Kullanıcı 32 sayısını belirtmiş olsa da gönderilen maddelerin toplamı 31'dir.

Bu dal, `master` üzerine doğrudan yazmadan kademeli düzeltme içerir.
Tüm maddeler giderildi / PASS iddiası **yoktur**.

## İlk kod paketindeki hedefler

- [x] P0-01: Eksik Python tip importları
- [ ] P0-02: Frontend API modülleri (ayrı kod paketi)
- [x] P0-03: Docker public klasörü ve API kopyalama/kurulum sırası
- [ ] P0-04: S3/MinIO somut implementasyonu
- [ ] P0-05: Kayıt sahibi kontrolü ve kimlik doğrulama
- [x] P0-06: Görsel silme metodu ve hata propagasyonu
- [ ] P0-07: Gerçek motif benchmark kabulü; son kayıt mAP50=0

## İlgili iyileştirmeler

- P1-18: Yeni yüklenen görseller ham EXIF yerine temizlenmiş JPEG ile saklanacak
- P1-20: GET sonuç yolu read-only
- P2-26: 1 MiB bloklarla boyut sınırlı okuma
- P2-30: README lisans bağlantısı düzeltildi
- P1-21: `create_all` ile Alembic çakışması ayrı doğrulanacak

## Kabul disiplini

Bu dalda kod değişiklikleri yapılmıştır; Windows/Edge, Docker Compose,
gerçek PostgreSQL, eğitilmiş motif modeli, gerçek veri ve üretim güvenliği
testleri henüz bu dal için çalıştırılmamıştır. Her maddede
`KOD_HAZIR`, `TEST_PASS`, `BLOCKED`, `HOLD` ayrımı korunacaktır.
