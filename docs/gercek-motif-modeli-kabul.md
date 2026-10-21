# Gerçek motif modeli ve veri kanıt kapısı

**Durum: HOLD.** CI'da 20–21 Ekim 2026'da çalışan tam backend testlerinin son doğrulanmış sonucu: Ubuntu ve Windows için 550 PASS / 40 FAIL / 1 SKIP. Bunlardan 40'ı, farklı algoritma başarısızlıkları ilan etmeden önce aşağıdaki bağımlılıklar bakımından ayrıştırılmalıdır.

## Doğrulanan engel kümeleri

- Beş `test_v2_07_visual_retrieval.py` vakası, depo içindeki `apps/api/carpet_db.sqlite` dosyasının beklenen gerçek katalog tablolarını içermemesi nedeniyle başarısız. Bunlar sentetik testte sıfır tablo ile taklit edilemez.
- Dokuz `test_v2_09_full_catalog_batch.py` vakası yerel Windows dosya yoluna sabitlenmiş sonuç dosyaları olmadan doğrulanamıyor. Kaynak dosyaların bulunduğu yetkili konumla depo göreli yol eşlemesi yapılmalı.
- Beş `test_v2_09b_detector_benchmark.py` vakasında lisans, gerçek veri ve deney manifesti eksik. Eksik belge uydurulmayacak.
- On dokuz `test_v2_09c_1_runtime_smoke.py` vakası, yerel R0 model dizini ve PyTorch/cihaz bağımlılıkları olmadan çalışamıyor.
- İki `test_v2_10_final_e2e_acceptance.py` vakası üretim araştırma ayrımı ve kürasyon JSON dosyalarını bulamıyor.

Bu 40 testin başarısız olması gerekçesiyle otomatik `skip` uygulanmadı. Tam test kapısı FAIL kalır.

## Veriye dokunmadan yeniden üretim protokolü

1. Hakları uygun özgün veri ve model ağırlıklarını yerelde yetkili dizine alın. Veri seti, dosya SHA256 ve kullanım izinleri kayıt altına alınmalı.
2. `docs/manifests/motif_artifact_requirements.json` içindeki repo göreli yolları gerçek dosyalara işaret edecek şekilde doğrulayın. Eksik dosyanın yerine sahte JSON oluşturmayın.
3. `python scripts/motif_evidence_audit.py --strict --output artifacts/motif-evidence-audit.json` ile dosya bütünlüğü, boş olmayan SHA256 ve eksikler incelenir. **Dosya mevcut olması model başarılı demek değildir.**
4. GPU profili, Python/PyTorch/CUDA sürümü, tam veri bölüşümü, başlangıç tohumu, hyperparametre, model checkpoint SHA256 ve inference logları saklanır.
5. Bağımsız gerçek holdout kümesinde sınıf başı precision/recall, mAP50, mAP50-95, F1, yanlış pozitif, abstention ve belirsizlik kayıtları ayrı raporlanır.
6. En son Windows/Edge gerçek ortam kabulü yapılır. Önceki `mAP50=0` baseline'ı üretim için geçer sayılmaz.

## Veri sızıntısı ve deney tekrarlanabilirliği

Aynı halının fotoğrafı, yakın kopyası, kaydırılmış kırpması veya aynı kaynak nesnenin farklı görseli train/val/test içinde çapraz bölünmemelidir (ürün/nesne/grup bazlı ayırım). Holdout seçiminden sonra hiperparametre ayarı yapılmaz. Hash, lisans ve etiket ontolojisi sürümü aynı manifest içinde eşleştirilir.

## Güvenlik kabul notu

Yeni analiz access-token altyapısı üretimde kayıt bazlı yetki gerektirir; **gerçek oturum açma/kullanıcı profili/rol sistemi değildir**. Geliştirme ve test ortamındaki eski yetkisiz fixture davranışı üretime taşınmamalıdır. Frontend'deki yerel saklama XSS tehdidine açıktır; oturum açma ve güvenilir sahiplik kimliği üretim kapsamı öncesi ayrı kapıdır.

**KARAR: VERİ_ENVANTERİ_HOLD / MODEL_DOĞRULUĞU_HOLD / TAM_BACKEND_CI_HOLD / MERGE_HOLD**
