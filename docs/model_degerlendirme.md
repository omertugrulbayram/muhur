# Koordinasyon modeli — teknik değerlendirme (lr-v1)

Tarih: 2026-11-24
Kaynaklar:
- `python -m app.ml.train_coordination` → `backend/app/ml/models/coordination_eval.json`
- `python -m app.ml.robustness` → `backend/app/ml/models/robustness.json`

> **Tüm sonuçlar sentetik veridir.** Gerçek kullanıcı verisiyle test yapılmadı.
> Gerçek kullanıcılarla test için ayrıca izin ve gizlilik planı gerekir (bkz. son bölüm).

## Özet

| | Bu model | Bağlama bakmayan basit kural |
|---|---|---|
| F1 (görülmemiş test dünyaları) | **0.91** | 0.36 |
| Uyarıya düşen normal öğrenci | **%2.4** | %40 |
| Kulüp duyurusu / etkinlik paylaşımında yanlış alarm | **%0 / %0** | %83 / %79 |
| Para alan gerçek öğrencileri yakalama | **%56** | %25 |
| Kamufle saldırı (eğitimde hiç görülmedi) | **%75** | — |

En büyük zayıflık: kampanyaların yaklaşık üçte biri **aday kümeye bile girmiyor**.
Eşiği ne kadar düşürürsek düşürelim, tespit oranı %69'un üstüne çıkmıyor.

## 1. Ne ölçüyoruz?

Eski modelin 0.989 F1 değeri, tek tek hesapları "bot / insan" diye ayıran ve
botların kendi içinde yoğun takipleştiği kolay bir sentetik ağda ölçülmüştü.
Bu değerlendirme iki açıdan daha zor:

1. **Birim hesap değil, küme.** Model "şu hesaplar birlikte, koordineli mi
   davranıyor?" sorusunu cevaplar. Bir hesaba "bot" etiketi yapıştırmaz.
2. **Masum ama şüpheli görünen durumlar da var.** Yanlış alarmı en çok bunlar
   üretir.

| Senaryo | Tür | Neden zor? |
|---|---|---|
| Etkinlik sonrası ortak paylaşım | masum | Onlarca öğrenci aynı etkinlik adıyla, aynı etiketle, aynı saatte yazar |
| Kulüp duyurusu | masum | Üyeler duyuruyu **birebir kopyalar** |
| Yurt arkadaşları | masum | Birbirini yoğun takip eden grup aynı akşam aynı konuda yazar |
| Sınav gecesi | masum | Aynı bölümden çok kişi aynı ders hakkında, etiketle yazar |
| Bot ağı | koordineli | Yeni açılmış hesaplar dakikalar içinde aynı metni basar |
| Satın alınmış hesaplar | koordineli | Eski, köklü ama uzun süre sessiz hesaplar birden aynı metni paylaşır |
| Ücretli gerçek kişiler | koordineli | **Mühürlü, gerçek öğrenciler** farklı cümlelerle aynı kampanyayı yayar |
| Yavaş kampanya | koordineli | Kampanya üç güne yayılır, metinler yeniden yazılır |
| Kamufle kampanya | saldırı (yalnız test) | Kampanya gerçek bir etkinliğin ardından, o etkinliğe **gerçekten katılmış** öğrencilere yaptırılır |

Kampanyaların %35'i hashtag kullanmaz. Masum etkinliklerin çoğu ise etiket
kullanır. Bu ayarlama yapılmadan önce model "hashtag varsa kampanya" kestirmesini
öğrenmişti, bunu engellemek için yapıldı.

## 2. Yöntem

- **Aday küme:** Paylaşımlar kelime düzeyinde TF-IDF ile vektörlenir. İki
  paylaşım şu durumlarda bağlanır:
  - kosinüs benzerliği ≥ 0.65 ve aralarında en fazla 6 saat var, ya da
  - aynı hashtag'i en fazla 12 saat arayla kullanmışlar.

  Paylaşım düzeyinde bağlı bileşenlerden en az 6 hesap içerenler aday kümedir.
- **Özellikler (12):**
  - içerik ve zaman: küme büyüklüğü, mesaj benzerliği, birebir kopya oranı, zamana yayılma
  - hesap geçmişi: yeni hesap oranı, açılış tarihi yayılımı, sessizken aktifleşme
  - ağ: küme içi takip yoğunluğu
  - içerik türü: hashtag/link oranı
  - bağlam: ortak etkinlik (PoA), ortak kulüp, aynı bölüm
- **Bağlam yalnız içerikle tutarlıysa sayılır.** "Ortak etkinlik" özelliği,
  etkinliğe katılan hesap oranı ile paylaşımların o etkinliği anma oranının
  çarpımıdır. Kulüp için de aynısı geçerli. Etkinliğe katılmış ama etkinlikten
  bahsetmeyen bir küme için panel ayrıca uyarı gösterir.
- **PoP durumu bilerek modelde YOK.** Gerçek insan olmak koordinasyon olmadığını
  kanıtlamaz, mühürsüz olmak da koordinasyonu kanıtlamaz. Modele girseydi
  mühürsüz kullanıcılar sırf bu yüzden riskli görünebilirdi.
- **Model:** lojistik regresyon. Her uyarının gerekçesi doğrudan katkılardan
  (katsayı × değer) üretilir. Bağlam özelliklerinin katkısı "hiç bağlam yok"
  noktasına göre ölçülür, böylece yalnız riski azaltabilir. Katkıların toplamının
  riski birebir verdiği bir testle kilitli.
- **Eğitim / test ayrımı:** 12 kampüs dünyasında eğitim, hiç görülmemiş 8
  dünyada test. Test tarafında 342 aday küme var, 42'si koordineli.

## 3. Ana sonuçlar

### Küme düzeyinde

| Yöntem | Precision | Recall | F1 | AUC | Yanlış alarm (masum küme) | Uyarıya düşen normal öğrenci |
|---|---|---|---|---|---|---|
| **LR (ürün)** | 0.886 | 0.929 | **0.907** | 0.950 | **%1.7** | **%2.4** |
| Gradient Boosting | 0.900 | 0.857 | 0.878 | 0.956 | %1.3 | %1.2 |
| Basit kural (benzer + hızlı) | 0.237 | 0.738 | 0.358 | 0.702 | %33.3 | %40.3 |

GB, normal öğrencilerde biraz daha az alarm veriyor ama daha az kampanya
yakalıyor. Asıl önemlisi, gerekçeleri modelin kendisinden okunamıyor. Ürün için
LR seçildi.

### Senaryo bazında uyarı oranı (eşik 0.5)

| Senaryo | Olması gereken | LR | GB | Basit kural |
|---|---|---|---|---|
| Etkinlik sonrası | düşük | **%0** | %0 | %79 |
| Kulüp duyurusu | düşük | **%0** | %8 | %83 |
| Yurt arkadaşları | düşük | **%0** | %0 | %0 |
| Sınav gecesi | düşük | **%19** | %0 | %88 |
| Bot ağı | yüksek | **%100** | %100 | %100 |
| Satın alınmış hesaplar | yüksek | **%94** | %75 | %75 |
| Ücretli gerçek kişiler | yüksek | **%56** | %50 | %25 |
| Yavaş kampanya | yüksek | **%25** | %25 | %0 |

## 4. Sağlamlık deneyleri

### 4.1 Eşik taraması

| Eşik | Masum alarm (ort.) | Koordineli tespit (ort.) | Uyarıya düşen normal öğrenci |
|---|---|---|---|
| 0.3 | %13 | %69 | %8.7 |
| 0.4 | %8 | %69 | %4.4 |
| **0.5** | **%5** | **%69** | **%2.4** |
| 0.6 | %1 | %69 | %0.6 |
| 0.7 | %0 | %69 | %0.0 |
| 0.8 | %0 | %67 | %0.0 |
| 0.9 | %0 | %53 | %0.0 |

**Yorum.** Tespit 0.3 ile 0.7 arasında hiç değişmiyor. Kaçan kampanyalar eşik
yüzünden değil, aday kümeye hiç girmedikleri için kaçıyor. Panelde "yüksek"
düzey 0.7'den başlıyor, bu düzeyde masum alarm ve normal öğrenci alarmı bu
testte sıfır. Eşik bu tabloya bakarak seçilmedi. Eşiği bu test sonucuna göre
ayarlamak test verisine uyum sağlamak (sızıntı) olurdu. Ayrı bir doğrulama
kümesinde seçilmeli.

### 4.2 Ablasyon: hangi özellik ne işe yarıyor?

| Varyant | Masum alarm | Koordineli tespit | Uyarıya düşen normal öğrenci |
|---|---|---|---|
| Tüm özellikler | %5 | %69 | %2.4 |
| Bağlam özellikleri yok | %5 | %69 | %3.6 |
| Hashtag özelliği yok | %11 | %69 | %6.5 |
| Yalnız metin + zaman | %66 | %61 | %38.7 |

**Yorum ve düzeltme.** Bu raporun ilk sürümünde basit kurala karşı kazancı
"PoA bağlamına" bağlamıştık. Ablasyon bunu desteklemiyor. Kazancın büyük
kısmı **hesap geçmişi** özelliklerinden geliyor: yeni hesap oranı, açılış tarihi
yayılımı, sessizken aktifleşme. Yalnız metin ve zamana bakan model normal
öğrencilerin %39'unu alarma sokuyor. Bağlam özellikleri bu testte normal
öğrenci alarmını %3.6'dan %2.4'e indiriyor. Bu etki küçük ama gerçek. Asıl
değerleri ise yöneticiye gösterilen **masum açıklamaları** üretmeleri.

### 4.3 Kamufle saldırı (eğitimde hiç görülmedi)

Saldırgan modelin "ortak etkinlik riski azaltır" kuralını bilir. Kampanyayı
gerçek bir etkinlikten hemen sonra, o etkinliğe gerçekten katılmış (PoA
kanıtlı, mühürlü) öğrencilere yaptırır.

| Model sürümü | Kamufle kampanya tespiti |
|---|---|
| Bağlam içerikten bağımsız (ilk sürüm) | **%0** |
| Bağlam yalnız içerikle tutarlıysa (güncel) | **%75** |

İlk sürümde "ortak etkinlik" özelliği riski logit ölçeğinde yaklaşık 5 birim
düşürüyordu ve bu saldırıların hepsi geçti. Bağlamın içerikle tutarlı olma
şartı bu saldırının dörtte üçünü yakalıyor. Değişiklik masum senaryolarda
alarmı artırmadı, tersine sınav gecesi alarmını %31'den %19'a indirdi. Saldırı
türü eğitim verisine eklenmedi. Düzeltme bu saldırıya özel değil, genel bir
ilke.

Kalan iki sınır:
- Kampanya gerçek etkinlik paylaşımlarıyla aynı kümeye karışırsa, kümenin
  çoğunluğu gerçekten etkinlikten bahsettiği için risk düşük kalabiliyor.
  Buna "kalabalığa karışma" diyoruz.
- Kampanya metnine etkinlik adını da ekleyen daha dikkatli bir saldırgan test
  edilmedi.

### 4.4 Dağılım kayması

Model bir kez eğitildi, sonra farklı kampüslerde denendi:

| Kurgu | Masum alarm | Koordineli tespit | Uyarıya düşen normal öğrenci |
|---|---|---|---|
| Küçük kampüs (250 öğrenci) | %3 | %94 | %5.0 |
| Büyük kampüs (900 öğrenci) | %3 | %84 | %1.3 |
| Masum senaryo ağırlıklı | %1 | %75 | %1.6 |
| Saldırı ağırlıklı | %0 | %80 | %0.5 |

Küçük kampüste normal öğrenci alarmı %5'e çıkıyor. Az kişinin olduğu yerde
organik konuşmalar bile küme oluşturabiliyor. Kampüs büyüklüğüne göre aday
küme parametreleri ayarlanmalı.

## 5. Sınırlar

- Veri tamamen sentetik. Senaryoları biz tasarladık, gerçek kampüs davranışı
  daha karmaşık olabilir.
- Metinler şablonlardan üretildi. Gerçek dilde benzerlik dağılımı farklıdır.
- Farklı cümlelerle ve hashtag'siz yazılan kampanyaların bir kısmı aday kümeye
  girmiyor. Bunun için anlam düzeyinde benzerlik (Türkçe cümle gömmeleri) gerekir.
- Organizatör kararları ("sorun yok / işaretle") henüz modele geri beslenmiyor.

## 6. Gerçek kullanıcı testine geçmeden önce

- Açık rıza (onam) formu: hangi veri, ne amaçla, ne kadar süre, nasıl silinir
- Veri minimizasyonu:
  - Yalnız takma kimlik, paylaşım zamanı ve metin kullanılır.
  - Metin, analizden sonra yalnız özellik vektörü olarak tutulur.
- Katılımcının uyarıyı görme ve itiraz etme hakkı
- Etik kurul / kulüp danışmanı onayı
- Pilot: tek bir kulüp, sınırlı süre, sonuçlar yalnız toplu olarak raporlanır
