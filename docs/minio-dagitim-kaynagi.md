# MinIO görseli — dağıtım kaynağı ve lisans kapısı

21 Ekim 2026 itibarıyla resmî `minio/minio` Docker Hub kaynağından temiz kurulumda imaj çekilemeyebiliyor. Bu nedenle üretim Compose dosyası **MINIO_IMAGE** değerini zorunlu tutar. Otomatik olarak doğrulanmamış imaj seçmez.

Yerel/CI S3 entegrasyon testi için geçici üçüncü taraf MinIO aynası kullanılır: `dappros/minio:RELEASE.2025-09-07T16-13-09Z`. Bu **üretim lisans/güvenlik onayı değildir**. Aynanın kaynak zinciri, SHA256 manifest/digest, AGPLv3 yükümlülükleri ve güncelleme riski üretim dağıtımından önce ayrıca onaylanmalıdır.

Windows PowerShell örneği:

```powershell
$env:MINIO_IMAGE = "KURUMCA_ONAYLANMIS_KAYNAK/minio@sha256:ONAYLANMIS_DIGEST"
$env:POSTGRES_PASSWORD = "ORNEK_YERINE_GERCEK_GIZLI_DEGER"
$env:MINIO_ROOT_PASSWORD = "ORNEK_YERINE_GERCEK_GIZLI_DEGER"
docker compose -f docker-compose.prod.yml config --quiet
```

Kaynak ve digest onaylanmadan üretim dağıtımına geçmeyin. CI birim testi PASS olsa da eksik gerçek motif ağırlığı ve holdout model kabulünü etkiler.
