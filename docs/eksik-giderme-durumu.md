# 31 Eksiklik İçin Sürümlenmiş Mühendislik Takibi

Son denetim: 20 Ekim 2026. Kaynak: Kullanıcının 31 maddelik inceleme listesi. Kullanıcı mesajında `32` yazmasına rağmen kaynak listede **7 P0 + 17 P1 + 7 P2 = 31** madde vardır. Bu kayda doğrulanmamış bir 32. madde eklenmeyecektir.

## Kanıt ve durum sınıfları
- `KOD_YAZILDI`: Değişiklik GitHub dalında var; testlerin tümü geçtiği anlamına gelmez.
- `KISMİ_KOD`: Bir alt parça geliştirildi; sorun bütünüyle çözülmedi.
- `HOLD`: Yeterli kod, kullanıcı onayı, gerçek veri veya test kanıtı yok.
- `KABUL_PASS`: Güncel commit için olumlu, bağımsız ve tekrarlanabilir test kanıtı gerekir.
- `MERGE_HOLD`: Bağımsız PR incelemesi ve bütün gerekli CI testleri geçmeden birleştirme yok.

## Eksiklerin tek tek mevcut durumu

| No | Öncelik | Konu | Durum | Kalan kabul koşulu |
|---:|:---:|---|---|---|
| 1 | P0 | Python başlangıç importları | KOD_YAZILDI | Temiz Python 3.11/3.14 backend kabul |
| 2 | P0 | Beş eksik frontend API modülü | KOD_YAZILDI | Güncel HEAD frontend ve uçtan uca API kabulü |
| 3 | P0 | Frontend/Docker paketleme | KOD_YAZILDI | Güncel HEAD Docker build ve gerçek container açılışı |
| 4 | P0 | S3/MinIO gerçek saklama | KISMİ_KOD | Unit test, çalışan MinIO, kesinti/yetki kabulü |
| 5 | P0 | Analiz kaynaklarının sahibi/yetkisi | KISMİ_KOD | 256-bit capability + 4 korumalı uç nokta ve negatif 403 testleri PASS; kullanıcı hesabı ve rol/oturum yönetimi eksik |
| 6 | P0 | Görsel silme ve ilişkili kayıtlar | KISMİ_KOD | Silme sırasında PROCESSING için 409 kilidi eklendi; eşzamanlı yarış/çökme ve gerçek S3 tutarlılığı bekliyor |
| 7 | P0 | Gerçek motif dedektörü (mAP50=0) | HOLD | Yeni bağımsız gerçek veri holdout; başarı eşiği tanımlanıp karşılanmalı |
| 8 | P1 | VLM şema uyumu | HOLD | Gerçek yerel model ile yeni bağımsız ölçüm |
| 9 | P1 | Gerçek motif veri kapsamı | HOLD | Hakları doğrulanmış, etiketli, gruplanmış veri seti |
| 10 | P1 | İkinci marka katalog aktivasyonu | HOLD | Resmî kaynak izni ve gerçek ürün verisi |
| 11 | P1 | Eksik Style DNA profilleri | HOLD | Eksik fotoğraflar ve ayrı doğrulama |
| 12 | P1 | Motif kültürel bilgi/hikâye genişletme | HOLD | Bilimsel kanıt, uzman denetimi |
| 13 | P1 | Tarihî referans görsel kapsamı | HOLD | Hakları uygun görsel ve müze kaynağı |
| 14 | P1 | Kalıcı ve tekrar denenebilir iş kuyruğu | HOLD | Kuyruk, at-least-once/idempotency, restart kabulü |
| 15 | P1 | Küratör üretim auth entegrasyonu | HOLD | Güvenilir gateway/rol ve audit testleri |
| 16 | P1 | Compose güvenli varsayılanlar | KOD_YAZILDI | Secrets, TLS ve üretim ortamı testi |
| 17 | P1 | Dağıtık rate limiting | KOD_YAZILDI | Redis atomik paylaşım ve negatif fail-closed testleri CI PASS; çok-instance/ters-proxy/yük kabulü bekliyor |
| 18 | P1 | Yüklenen görsel EXIF gizliliği | KISMİ_KOD | Dosya saklama ve uç nokta negatif testleri |
| 19 | P1 | Retention/silme politikası | KOD_YAZILDI | Yeni 7 gün TTL, Alembic 019, saatlik worker ve regresyon testleri yazıldı; gerçek GDPR/KVKK, eski veri, üretim cleanup kabulü bekliyor |
| 20 | P1 | GET sonucunda veritabanına yazma | KOD_YAZILDI | Yan etkisiz GET regresyon testi |
| 21 | P1 | Alembic tek şema yönetimi | KOD_YAZILDI | PostgreSQL 16 sıfırdan Alembic geçişi PASS; var olan DB yükseltme/geri yükleme bekliyor |
| 22 | P1 | GitHub CI kalite kapıları | KISMİ_KOD | Full backend, PostgreSQL, güvenlik ve Windows/Edge PASS |
| 23 | P1 | Frontend unit/E2E testleri | HOLD | Vitest + Playwright ve gerçek Edge |
| 24 | P1 | PostgreSQL/üretim kabulü | KISMİ_KOD | PostgreSQL 16 + Alembic şema smoke PASS; üretim API uçtan uca ve veri koruma kabulü bekliyor |
| 25 | P2 | Deterministik Python bağımlılık kilidi | KISMİ_KOD | npm lock onarıldı; Python lock/SBOM eksik |
| 26 | P2 | Bellek güvenli upload sınırı | KOD_YAZILDI | Her iki upload uç noktası 1 MiB parçalı okuma kullanıyor; reverse proxy gövde sınırı ve yük testi bekliyor |
| 27 | P2 | Polling hata/backoff/yeniden dene | KOD_YAZILDI | Frontend E2E ve ağ kesintisi testi |
| 28 | P2 | Sunucu tarafı güvenilir kullanıcı geçmişi | HOLD | Kimlik/sahiplik modeli, saklama kontrolü |
| 29 | P2 | Kısmi toplu silme hatası | KOD_YAZILDI | Çoklu silme E2E ve yanlış başarı mesajı testi |
| 30 | P2 | README güncelliği/lisans bağlantısı | KISMİ_KOD | V2/V3 doğrulama tablosu ve güncel kullanım adımları |
| 31 | P2 | İzlenen generated cache ve geçici dosyalar | KOD_YAZILDI | 176 dosya çıkarıldı, .gitignore eklendi; release arşiv politikası teyidi |

## Kayıtlı CI bulguları

- `4d74b3b` temelinde npm paketi/build FAIL idi; package-lock CI üzerinden yeniden üretildi.
- Daha sonraki CI'da Next.js kalite kontrolleri ve Docker imaj derlemesi **PASS**; backend eski kabul raporunun aksine doğrudan test edildiğinde hata verdi.
- `13c0841` Ubuntu backend testlerinde **544 PASS, 42 FAIL, 1 SKIP**. Başarısızlıklar arasında 35 görüntü/92 gerçek motif yerine yerel veriye bağlı testler, bulunmayan orijinal Windows dosya yolları, kurulu olmayan `torch` ve Style DNA D9 testi vardır. Bunlar gizlenmedi veya sahte test verisiyle PASS yapılmadı.
- Güncel committe Style DNA/OpenCV uyum kodu eklenmiştir; sonucu, güncel CI çalışması bitmeden PASS kabul etmeyin.

## Merge önkoşulları

1. P0 yetkilendirme ve silme sınırları fail-closed.
2. Ubuntu + Windows backend test kapıları PASS.
3. Next.js typecheck + lint + build PASS.
4. PostgreSQL/Alembic migration, S3/MinIO ve Docker E2E kanıtları.
5. Hakları uygun bağımsız gerçek veri ve model değerlendirme; mAP50=0 baseline üretime seçilemez.
6. Bağımsız inceleme, PR-only merge ve Windows/Edge fiziksel kabul.

**MÜHENDİSLİK KARARI: KOD_DÜZELTMELERİ_KISMİ / YETKİLENDİRME_HOLD / GERÇEK_MOTİF_HOLD / BACKEND_CI_HOLD / MERGE_HOLD**

Bu kayıt bir tamamlanma sertifikası değil, eksiksiz izlenebilirlik listesidir.

## 21 Ekim 2026 — Doğrulanmış ek mühendislik kayıtları

- `e8e794af`: V2-09/V2-10 testlerinin eski kullanıcı bilgisayarına bağımlı kök yolları repo göreli hâle getirildi. Ubuntu ve Windows **572 PASS / 31 FAIL / 1 SKIP**. Böylece 9 koşul daha test ortamında doğrulandı.
- `b98504bd`: 001–014 Alembic migration zincirindeki tekrar eden PostgreSQL enum türlerinin oluşturulması tekilleştirildi. `backend-postgresql-schema` gerçek PostgreSQL 16 işinde **PASS** (`2026_10_21_018` sürümü ve `upload_analyses.owner_token_sha256`).
- `backend-security-smoke`: Analiz durumu, sonucu, görüntüsü ve silme uç noktalarında yetkisiz erişim negatif testleri PASS. Bu, tam oturum/rol sistemi kabulü değildir.
- `motif-evidence-inventory`: Depodaki üç kanıt JSON'u SHA-256 ile doğrulandı. Gerçek YOLO11n deney manifesti eksiktir. Envanter işi PASS olsa da **MODEL_KABUL_HOLD**.
- `data/validation/v2-09b/detector-benchmark-report.json`: 35 gerçek görüntü, 92 motif işaretlemesi üzerinden raporlanan Detect mAP50=0.001 ve OBB mAP50=0.0. 57/57 rapor/bütünlük kontrolünün PASS olması model başarısının PASS olduğu anlamına gelmez.

**GÜNCEL KARAR: ANALİZ_CAPABILITY_TEST_PASS / PG_ŞEMA_SMOKE_PASS / GERÇEK_MODEL_HOLD / FULL_BACKEND_FAIL / MERGE_HOLD.**

## 21 Ekim 2026 — Veri/envanter ve UI durum kapısı

- `apps/api/app/api/v1/model_readiness.py`: /api/v1/system/model-acceptance API'si eksik kaynak anahtarlarını döndürür ve bağımsız model kabulü bulunmadığı için üretim durumunu HOLD tutar.
- `apps/web/app/analysis/new/page.tsx`: analiz başlamadan önce motif modelinin kabul durumunu gösterir; YOLO modelinin üretimde doğrulandığını iddia etmez.
- `docs/manifests/motif_artifact_requirements.json`: kayıtlı model indirme raporundaki ağırlık shard SHA256'larını da içeren **17 gerçek kaynak** envanteri. Beklenen artifact yerine sahte dosya üretilmez.
- `backend-minio-integration`: gerçek S3 nesne yaşam döngüsü; boş sonuç sahte kabul değildir.
- `docker-compose.prod.yml`: MinIO imajı üretimde kullanıcı tarafından seçilmeli, parola ve ayrı S3 servis kimlik bilgileri tanımlanmalıdır.

**Not:** 12 tam backend testinin veri/model bağlı hataları model ağırlıkları, gerçek DB ve hakları uygun benchmark dosyaları olmadan kapanmış sayılmaz. 31 maddeye topluca KABUL_PASS verilmemiştir.

## 21 Ekim 2026 — İşlem devamı (master)

- `c3d8d464` ve `f10f4e45`: 019 migration, yeni analizlerde 7 günlük TTL, 410 yetki kapısı, ayrı saatlik temizleyici; eski NULL TTL kayıtlar otomatik silinmez.
- `e0aec4e8`: Model/gerçek veri yerel arşivden **SHA kontrollü** aktarımı; manifesto eksikse veya hash uyuşmazsa izin verilmez. Denetimde `PRESENT_UNVERIFIED` bilimsel PASS değildir.
- `0600156d`: SQLite oturum rollback regresyon testi düzeltildi; son CI doğrulaması gerekir.
- `895ab059`: İşlem sürerken silmeye HTTP 409 ve negatif regresyon testi eklendi.
- Bu adımlar **gerçek dedektör mAP50>0 kabulü** veya gerçek model ağırlıklarının depoda bulunduğu anlamına gelmez. 12 harici veri/model testi açık kalır.

- `12755e5c`: Gerçek Redis paylaşılmış kota için ayrı `backend-redis-integration` CI PASS. `RATE_LIMIT_BACKEND=redis` üretimde zorunlu; Redis kesintisinde fail-closed 503 testi eklendi.
- `b9dc7ca0`: Model kabul API'si eski 9 kaynak yerine tek SHA manifestindeki 17 kanıta bakıyor; kaynak varlığına başarı etiketi verilmez.
