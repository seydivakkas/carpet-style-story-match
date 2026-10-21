# Carpet Style & Story Match

**Özel lisans — tüm hakları saklıdır.** Ayrıntılar: [LICENSE](LICENSE).

Halıların 9 boyutlu görsel karakterini (Style DNA), görsel benzerliğini ve kaynaklı tarihî bağlantılarını ayrı ayrı ele alan FastAPI + Next.js uygulaması. **Motif tanıma modeli henüz bilimsel üretim kabulünden geçmemiştir.** Halı motifi önerileri uzman onayı veya bağımsız gerçek veri değerlendirmesi yerine geçmez.

## Mimari

- `apps/api/`: FastAPI, SQLAlchemy, Alembic ve modüler analiz.
- `apps/web/`: Next.js, TypeScript, analiz yükleme ve beş kartlık sonuç ekranı.
- `packages/`: Ortak sözleşmeler, deneysel motif doğrulama araçları.
- `docs/`: Sürüm kayıtları, deney kanıtları, eksik/geliştirme takibi.
- `docker-compose.prod.yml`: PostgreSQL, API, Next.js ve opsiyonel S3/MinIO altyapısı.

## Çalışan ve bekleyen yetenekler

| Alan | Mühendislik durumu |
|---|---|
| Next.js typecheck / lint / build | CI PASS |
| Backend Python 3.11 smoke ve pytest | Son baz: 591 PASS / 12 FAIL / 1 SKIP; son commit tekrar doğrulanmalı |
| PostgreSQL 16 + Alembic sıfırdan geçiş | CI PASS |
| Analiz bazlı 256-bit erişim kanıtı, negatif API testleri | Hedefli CI PASS; kullanıcı hesap sistemi henüz yok |
| Gerçek S3 API yükle/oku/sil testi | Ayrı MinIO CI doğrulaması |
| Gerçek motif dedektörü, holdout metrikleri | **HOLD** (üretim onayı yok) |
| Kalıcı iş kuyruğu, gerçek Edge kabul, çok markalı veri | **HOLD** |

**Erişim güvenliği sınırı:** Tek kullanıcının yüklediği analizin erişim anahtarı tarayıcıda saklanır. Bu yapı, gerçek çok kullanıcılı kimlik doğrulama ve rol yönetiminin yerini almaz. Geliştirme ortamını güvenilmeyen ağa açmayın.

## Windows üzerinde geliştirme

Gereksinimler: Python 3.11, Node.js 20 ve üzeri, npm; veri tabanı için PostgreSQL 16. API kurulumunda paketler kök klasörden yüklenebilir.

```powershell
python -m pip install -e "./apps/api[dev,s3]"
cd apps/api
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

İkinci PowerShell penceresinde:

```powershell
cd apps/web
npm ci
npm run dev
```

- Uygulama: http://localhost:3000
- Geliştirme API belgesi: http://localhost:8000/docs
- Gerçek model kanıt durumu: http://localhost:8000/api/v1/system/model-acceptance
- Analiz ekranı: http://localhost:3000/analysis/new

## Kabul ve test

```powershell
cd apps/api
python -m pytest tests/ -q
cd ../web
npm run typecheck
npm run lint
npm run build
```

`python scripts/motif_evidence_audit.py --strict --output artifacts/motif-evidence-audit.json` komutu **depo kökünde** çalıştırılır. Gerçek ve lisanslı dosyalar bulunmadığında çıkış kodu `2` döndürür; sahte kanıt oluşturulmaz. Gerekli dosyaların tam listesi: [motif kanıt manifesti](docs/manifests/motif_artifact_requirements.json). Gerçek model için ayrı deney kuralları: [kabul belgesi](docs/gercek-motif-modeli-kabul.md).

Eksiklerin güncel, madde bazlı kaydı: [31 eksiklik takibi](docs/eksik-giderme-durumu.md).

## Gerçek verilerin yerel aktarımı

Gerçek model ağırlıklarını ve özgün dataset kayıtlarını GitHub'a eklemeden, doğrulanmış Windows klasöründen proje içine aktarabilirsiniz. Kaynağın repo alt klasör yapısını koruması gerekir. Dosyalar ve raporlar otomatik uydurulmaz; bilinen modellerin SHA-256 ve byte uzunluğu denetlenir.

```powershell
# Proje depo kökünde:
python scripts/stage_motif_evidence.py --source-root "C:\\Kendi_Arsivim\\carpet-style-story-match"
# Yalnız doğru kaynak doğrulandığında gerçek kopyalama:
python scripts/stage_motif_evidence.py --source-root "C:\\Kendi_Arsivim\\carpet-style-story-match" --apply
# Model ve kaynak envanteri: eksik veya doğrulanmamış kanıtta exit 2
python scripts/motif_evidence_audit.py --strict --output artifacts/motif-evidence-audit.json
```

`PRESENT_UNVERIFIED` durumu gerçek dosya bulunduğu ancak kaynak manifestinde beklenen SHA-256 bulunmadığı anlamına gelir; bu **model başarısı değildir**. Orijinal veri kullanım hakları ve bağımsız holdout ayrıca belgelenmelidir.

## Saklama ve silme

Yeni oluşturulan analizler varsayılan **7 gün** saklanır. `ANALYSIS_RETENTION_DAYS` 1–365 arasında ayarlanabilir. Saklama süresi sona eren analizlere geçerli erişim kanıtıyla bile HTTP `410 GONE` döner. Üretim Compose dağıtımında `retention` servisi her saat silme işlemini dener; görsel silinemezse veritabanı kaydı korunur ve sonraki turda tekrar denenir. Eski `expires_at=NULL` kayıtları kullanıcı kararı olmadan otomatik silinmez. Yerelde tek defalık denetim:

```powershell
cd apps/api
python -m app.scripts.cleanup_expired_analyses --once
```

Analiz **PROCESSING** durumundaysa kullanıcı silmesi HTTP `409` döner; işlem bitince yeniden denenebilir. Bu önlem arka plan işçisinin silinmiş analiz için tekrar dosya oluşturma yarışını engeller.

## Paylaşımlı hız sınırı

Üretimde tüm FastAPI worker'ları ortak Redis 7 üzerinden atomik 60 saniyelik IP kotası kullanır. `RATE_LIMIT_BACKEND=redis` ve `REDIS_URL` zorunludur; Redis erişilemiyorsa güvenlik denetimi sessizce atlanmaz (HTTP 503). Geliştirme ortamı için `memory` modu hâlâ kullanılabilir. Redis yalnız Docker iç ağına açıktır.

Ters proxy IP adresini maskeliyorsa kota proxy IP'sine uygulanır; güvenilir proxy zinciri belirlenmeden istemciden gelen `X-Forwarded-For` başlığına körü körüne güvenilmez. Dağıtık yük ve saldırı dayanımı fiziksel kabul aşamasında ölçülecek.

## Üretim yapılandırması

`docker-compose.prod.yml` şifreleri otomatik üretmez ve gerçek güvenlik ayarı yerine örnek parola kullanmaz. `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` ve onaylı **`MINIO_IMAGE`** ortam değişkenleri zorunludur. `STORAGE_BACKEND=s3` kullanılırsa `S3_ACCESS_KEY`, `S3_SECRET_KEY` ve var olan bir `S3_BUCKET_NAME` de gereklidir. Portlar yerel arayüze bağlıdır. TLS, reverse proxy, hesap oturumu ve veri saklama politikası ayrıca tamamlanmalıdır.

MinIO imaj kaynağı için [dağıtım/tedarik kapısı](docs/minio-dagitim-kaynagi.md) belgesini inceleyin. Üçüncü taraf test aynası otomatik üretim onayı değildir.

## Lisans

**ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR.** Telif Hakkı © 2026 Seydi Eryılmaz (@seydivakkas). Kullanım koşulları için [LICENSE](LICENSE) dosyasına bakın.
