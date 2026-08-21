# Gerçek Halı Görseli Motif Etiketleme Kılavuzu (v1.0.0)

**Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) — Tüm Hakları Saklıdır.**

Bu kılavuz, Türk/Anadolu ve Doğu halılarındaki görsel motiflerin YOLOv11 ve VLM destekli dedektör eğitimleri için standart, tutarlı ve tekrarlanabilir biçimde etiketlenmesini (annotation) sağlamak amacıyla hazırlanmıştır.

---

## 1. Genel Etiketleme Kuralları ve Protokolü

1. **Tam Kapsama Kuralı (Bounding Box Tightness)**:
   - Sınırlayıcı kutu (bounding box), motifin en uç piksellerini (çıkıntı, kanca, yaprak ucu) tam olarak kapsamalıdır.
   - Aşırı boşluk bırakılmamalı, motifin dışındaki arka plan veya komşu motifler kutu içine minimum düzeyde dahil edilmelidir.

2. **Görünürlük ve Kısmi Kırpılma Kuralı (%50 Eşiği)**:
   - Halı kenarlarında, yıpranmış alanlarda veya bordür kesimlerinde motifin **%50'sinden azı** görünüyorsa o motif **etiketlenmez** (atlanır).
   - %50 ve üzeri görünen motifler tam olarak kutulanır.

3. **Bordür ve Şerit Tekrarları (Vine Scroll & Band Rule)**:
   - Kıvrım dal, sarmaşık ve bordür akışları (`vine_scroll_like`), tekil yapraklar yerine bordür boyunca devam eden ritmik dal/akış segmentleri halinde etiketlenir.
   - Ancak bordür içerisindeki bağımsız rozet (`rosette_like`) veya yıldız (`star_like`) madalyonları net şekilde ayrışıyorsa tekil olarak da etiketlenebilir.

4. **Yönlülük ve Oryantasyon (Directional Semantics)**:
   - Mihrap (`niche_like`), Hayat Ağacı (`tree_like`) ve İnsan Figürü (`human_figure_like_geometric`) motifleri dikey ve doğal yönünde değerlendirilir. Ters dönmüş mimari yapılar veya kemer harici formlar mihrap olarak etiketlenemez.

5. **Kültürel Değil, Saf Geometrik-Görsel Ayrım**:
   - Etiketleyici sembolik/mistik anlamlara göre değil, halı üzerindeki morfolojik ve geometrik hatlara göre karar vermelidir.

---

## 2. 17 Motif Sınıfı: Tanımlar, Ayırt Edici Kurallar ve Örnekler

Aşağıda 17 sınıfın YOLO etiketleme sırasıyla Türkçe tanımları, ayırt edici morfolojik kuralları, örnek görsel referansları ve sınır-vaka (edge-case) notları yer almaktadır:

---

### Sınıf 0: `cloud_band_like` (Bulut Motifi / Bulut Şeridi)
- **Tanım**: Uzakdoğu ve Osmanlı saray halılarında görülen, kıvrımlı, S veya dalga formundaki asimetrik bulut şeritleri.
- **Ayırt Edici Kural**: Sarmal uçlu, şerit halinde uzanan ve içinde boşluk barındıran kıvrımlı hatlar.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/cloud_band_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/cloud_band_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Sarmaşık (`vine_scroll_like`) bordür şeridi ile karıştırılmamalıdır; `cloud_band_like` bağımsız, küt uçlu ve karakteristik "Çin bulutu" boğumlarına sahiptir.

---

### Sınıf 1: `comb_like` (Tarak Motifi / El-Tarak)
- **Tanım**: Bir gövde üzerinden paralel uzanan 3 veya daha fazla diş/çubuk barındıran tarak formundaki geometrik şekiller.
- **Ayırt Edici Kural**: Tek bir omurgadan çıkan belirgin paralel parmak/diş dizilimi.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/comb_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/comb_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: İnsan figürü el parmakları veya saç tarağı ile koçboynuzu uçları karışabilir. Çıkıntılar paralel ve düz ise `comb_like`, dairesel içe kıvrılıyorsa `horn_like` etiketlenmelidir.

---

### Sınıf 2: `hook_like` (Çengel / Kanca Motifi)
- **Tanım**: Uçları sivri veya içe/dışa doğru 90°-180° kancalanan geometrik veya organik çengel uzantıları (ör. Bergama/Yuntdağ kancaları).
- **Ayırt Edici Kural**: Baklava veya sekizgenlerin dış sınırlarına eklemlenen tekil veya sıralı kanca çıkıntıları.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/hook_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/hook_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Bir baklavanın etrafındaki kancalar baklavayla bir bütünse ve merkez doluysa `lozenge_like` kapsayabilir; ancak kancalı hat bağımsız bir yürüyüş sergiliyorsa `hook_like` etiketlenir.

---

### Sınıf 3: `horn_like` (Koçboynuzu Motifi)
- **Tanım**: İki yana simetrik veya tekil olarak helezonik/yay şeklinde kıvrılan boynuz formları.
- **Ayırt Edici Kural**: Uç kısımları içeriye veya dışarıya doğru belirgin dairesel kıvrım yapan C/S formundaki kollar.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/horn_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/horn_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Kancalı baklavanın uçları ile koçboynuzu ayrımı: Boynuz helezonu belirgin bir spiral yay çiziyorsa `horn_like` seçilmelidir.

---

### Sınıf 4: `human_figure_like_geometric` (İnsan / Çocuk / Eli Belinde Figürü)
- **Tanım**: Gövde, baş ve iki yana açılan kol/bacak uzantılarından oluşan stilize geometrik antropomorfik figürler.
- **Ayırt Edici Kural**: Dikey simetri ekseninde baş-gövde-uzuv hiyerarşisi sergileyen stilize insan/figür yapısı.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/human_figure_like_geometric_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/human_figure_like_geometric_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Eli-belinde dişilik motifi ile tarak motifi karışabilir. Gövdeden iki yana simetrik bükülen kollar varsa `human_figure_like_geometric` etiketlenir.

---

### Sınıf 5: `lattice_like` (Kafes / Izgara / Şebeke Motifi)
- **Tanım**: Birbirini kesen diyagonal veya dikey çizgilerden oluşan ağ, kafes veya petek dokulu zemin bölümleri.
- **Ayırt Edici Kural**: En az 2x2 hücre oluşturan kesişim çizgileri ve ızgara yapısı.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/lattice_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/lattice_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Tek bir izole baklava `lozenge_like` iken, halı zeminini veya bordürü kaplayan sürekli baklava ızgarası `lattice_like` olarak etiketlenir.

---

### Sınıf 6: `lotus_like` (Lotus / Nilüfer Motifi)
- **Tanım**: Su damlası veya kadeh formunda yukarıya doğru açılan katmanlı taç yapraklı çiçek motifi.
- **Ayırt Edici Kural**: Tabanı dar, üst kısmı genişleyen katmanlı kadeh yapısı.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/lotus_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/lotus_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Palmet (`palmette_like`) ile ayrım: Lotus daha dairesel/yumuşak katmanlara sahipken palmet yelpaze şeklinde sivrilen yaprak dizilimine sahiptir.

---

### Sınıf 7: `lozenge_like` (Baklava / Eşkenar Dörtgen Motifi)
- **Tanım**: Dört kenarı birbirine eşit, köşeleri sivri eşkenar dörtgen geometrik formlar.
- **Ayırt Edici Kural**: Karakteristik 4 köşeli elmas/baklava geometrisi (içi iç içe katmanlı veya basamaklı olabilir).
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/lozenge_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/lozenge_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Köşeleri pahlanmış veya 8 köşeli hale gelmiş baklavalar `octagonal_form` veya `medallion_like` sınıfına girer. Sadece 4 ana köşesi belirgin olanlar `lozenge_like` olarak etiketlenmelidir.

---

### Sınıf 8: `medallion_like` (Merkezi Madalyon / Göbek)
- **Tanım**: Halının merkezinde veya ana ekseninde yer alan, halı yüzeyinin belirgin bir alanını kaplayan büyük ölçekli merkezi kompozisyon odağı (oval, yuvarlak veya çokgen).
- **Ayırt Edici Kural**: Halı kompozisyonunun ana merkezinde yer alması, büyük alan kaplaması (>%5 zemin alanı) ve hiyerarşik olarak diğer motifleri çevrelemesi.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/medallion_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/medallion_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: `medallion_like` vs `octagonal_form`: Küçük boyutlu, tekrar eden sekizgenler `octagonal_form` iken; halının merkezini domine eden ana göbek `medallion_like` olarak etiketlenir.

---

### Sınıf 9: `niche_like` (Mihrap / Kemer / Niş Motifi)
- **Tanım**: Seccade halılarında yer alan, üst kısmı sivri veya basamaklı kemer şeklinde sonlanan mimari niş alanı.
- **Ayırt Edici Kural**: Üst tarafında tepe noktası (kubbe/kemer) olan, aşağı doğru açılan U veya kemer şeklindeki alan.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/niche_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/niche_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Mihrabın içindeki kandil veya ibrik ayrı birer obje olabilir; ancak kemerin kendisi ve ana seccade nişi `niche_like` olarak sınırlandırılmalıdır.

---

### Sınıf 10: `octagonal_form` (Sekizgen / Holbein-Güldalı Sekizgeni)
- **Tanım**: 8 kenarlı ve 8 köşeli geometrik çokgen formlar (Holbein, Memling veya Türkmen gülleri).
- **Ayırt Edici Kural**: Net 8 kenarlı simetrik çokgen yapısı.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/octagonal_form_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/octagonal_form_example_2.png`
- **Sınır-Vaka (Edge-Case)**: 8 köşeli yıldızlar `star_like` iken; köşeleri içeri çökmeyen dışbükey sekizgenler `octagonal_form` etiketlenir.

---

### Sınıf 11: `palmette_like` (Palmet Motifi)
- **Tanım**: Yelpaze veya palmiye yaprağı biçiminde simetrik olarak iki yana açılan stilize floral motif.
- **Ayırt Edici Kural**: Merkezi bir damar etrafında simetrik dizilmiş sivri yaprak dilimleri.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/palmette_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/palmette_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Dairesel rozet (`rosette_like`) ile ayrım: Palmet dikey simetriye sahip yelpaze şeklindedir; rozet ise merkezden her yöne 360° radyal dağılır.

---

### Sınıf 12: `rosette_like` (Rozet / Gülce Motifi)
- **Tanım**: Merkezdeki bir dairesel çekirdekten 360 derece radyal olarak yayılan dairesel çiçek formları.
- **Ayırt Edici Kural**: Radyal simetrik, dairemsi veya çok yapraklı çiçek görünümü.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/rosette_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/rosette_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Radyal sivri uçlu yıldızlar `star_like`; yuvarlak yaprak dilimli olanlar `rosette_like` etiketlenir.

---

### Sınıf 13: `star_like` (Yıldız Motifi / 8-Köşeli Selçuklu Yıldızı)
- **Tanım**: Merkezden dışa doğru sivri ışınlar/köşeler uzatan yıldız formları (özellikle 8 veya 6 köşeli geometrik yıldızlar).
- **Ayırt Edici Kural**: İçe doğru çöken açılar ve dışa doğru sivrilen üçgen ışınlar.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/star_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/star_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Uçları yuvarlak yaprak ise `rosette_like`; uçları keskin açılı üçgen ise `star_like`.

---

### Sınıf 14: `tree_like` (Hayat Ağacı / Servi / Ağaç Motifi)
- **Tanım**: Belirgin bir gövde/kök üzerinden yükselen ve yanlara dallar veya yapraklar veren dikey ağaç kompozisyonu.
- **Ayırt Edici Kural**: Dikey ana omurga/gövde ve gövdeden ayrılan hiyerarşik dallanma.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/tree_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/tree_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Bordür boyunca yatay uzanan yapraklı dal `vine_scroll_like` iken; bağımsız olarak dikey kök salıp yükselen ağaç `tree_like` etiketlenir.

---

### Sınıf 15: `unmapped_visual_motif` (Haritalanmamış / Serbest Görsel Motif)
- **Tanım**: Halı üzerinde net bir görsel tekrar, figüratif çizim veya ayırt edici süsleme oluşturan, ancak yukarıdaki 16 sınıftan hiçbirine (geometrik veya organik kriterler bakımından) girmeyen belirgin motifler (ör. akrep, ejderha, kuş, ibrik, muska, bereket sembolü).
- **Ayırt Edici Kural**: Arka plan dokusu veya rastgele düğüm hatası OLMAYAN; net bir şekilsel sınır ve kontura sahip olan özgün motifler.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/unmapped_visual_motif_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/unmapped_visual_motif_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Rastgele yıpranma izleri veya belirsiz renk lekeleri etiketlenmez. Yalnızca 16 sınıfa uymayan ama insan gözüyle açıkça ayırt edilen formlar `unmapped_visual_motif` olarak etiketlenir.

---

### Sınıf 16: `vine_scroll_like` (Kıvrım Dal / Sarmaşık / Bordür Şeridi)
- **Tanım**: Bordürlerde veya zemin dolgusunda bir çizgi boyunca kıvrılarak ilerleyen, yaprak ve filizlerle süslü dal akışı.
- **Ayırt Edici Kural**: Sürekli bir dal çizgisi ve bu çizgiye bağlı kıvrımlı organik dalga hareketi.
- **Örnekler**:
  - Örnek 1: `docs/labeling-guide-v1-examples/vine_scroll_like_example_1.png`
  - Örnek 2: `docs/labeling-guide-v1-examples/vine_scroll_like_example_2.png`
- **Sınır-Vaka (Edge-Case)**: Dal boyunca sıralanan çiçekler küçükse tüm şerit `vine_scroll_like` olarak tek bir uzun kutu ile etiketlenebilir; büyük ve bağımsız rozetler varsa dal `vine_scroll_like`, rozetler ise `rosette_like` olarak etiketlenir.

---

## 3. CVAT / Roboflow Ayarları ve Sınıf Listesi

Etiketleme araçlarına aktarılacak standart `classes.txt` dosyası sırası:

```text
0: cloud_band_like
1: comb_like
2: hook_like
3: horn_like
4: human_figure_like_geometric
5: lattice_like
6: lotus_like
7: lozenge_like
8: medallion_like
9: niche_like
10: octagonal_form
11: palmette_like
12: rosette_like
13: star_like
14: tree_like
15: unmapped_visual_motif
16: vine_scroll_like
```
