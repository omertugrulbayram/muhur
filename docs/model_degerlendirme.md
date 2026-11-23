# Koordinasyon modeli — değerlendirme (lr-v1)

Tarih: 2026-11-24 · Kaynak: `python -m app.ml.train_coordination` · Ham sonuç:
`backend/app/ml/models/coordination_eval.json`

> **Tüm sonuçlar sentetik veridir.** Gerçek kullanıcı verisiyle test yapılmadı.
> Gerçek kullanıcılarla test için ayrıca izin ve gizlilik planı gerekir.

## Ne ölçüyoruz?

Eski modelin 0.989 F1 değeri, tek tek hesapları "bot / insan" diye ayıran ve
botların kendi içinde yoğun takipleştiği kolay bir sentetik ağda ölçülmüştü.
Bu değerlendirme iki açıdan daha zor:

1. **Birim hesap değil, küme.** Model "şu hesaplar birlikte, koordineli mi
   davranıyor?" sorusunu cevaplar. Bir hesaba "bot" etiketi yapıştırmaz.
2. **Masum ama şüpheli görünen durumlar da var.** Yanlış alarmı en çok bunlar
   üretir:

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

Kampanyaların %35'i hashtag kullanmaz. Masum etkinliklerin çoğu ise etiket
kullanır. Bunun sebebi, modelin "hashtag varsa kampanya" kestirmesini
öğrenmesini engellemektir. Bu ayarlama yapılmadan önce model tam olarak bu
kestirmeyi öğrenmişti.

## Yöntem

- **Aday küme:** Paylaşımlar kelime düzeyinde TF-IDF ile vektörlenir. İki
  paylaşım şu durumlarda bağlanır:
  - kosinüs benzerliği ≥ 0.65 ve aralarında en fazla 6 saat var, ya da
  - aynı hashtag'i en fazla 12 saat arayla kullanmışlar.

  Paylaşım düzeyinde bağlı bileşenlerden en az 6 hesap içerenler aday kümedir.
- **Özellikler (12):** küme büyüklüğü, mesaj benzerliği, birebir kopya oranı,
  zamana yayılma, yeni hesap oranı, açılış tarihi yayılımı, sessizken
  aktifleşme, küme içi takip, hashtag/link oranı, ve üç bağlam özelliği: ortak
  etkinlik (PoA), ortak kulüp, aynı bölüm.
- **PoP durumu bilerek modelde YOK.** Gerçek insan olmak koordinasyon olmadığını
  kanıtlamaz, mühürsüz olmak da koordinasyonu kanıtlamaz. Modele girseydi
  mühürsüz kullanıcılar sırf bu yüzden riskli görünebilirdi. Bu karar F1'i
  0.918'den 0.894'e düşürdü. Adalet için kabul edildi.
- **Model:** lojistik regresyon. Her uyarının gerekçesi doğrudan katkılardan
  (katsayı × değer) üretilir. Bağlam özelliklerinin katkısı "hiç bağlam yok"
  noktasına göre ölçülür, böylece yalnız riski azaltabilir. Olasılık bundan
  etkilenmez, bu bir testle kilitli.
- **Eğitim / test ayrımı:** 12 kampüs dünyasında eğitim, hiç görülmemiş 8
  dünyada test. Test tarafında 342 aday küme var, 42'si koordineli.

## Sonuçlar

### Küme düzeyinde

| Yöntem | Precision | Recall | F1 | AUC | Yanlış alarm (masum küme) | Uyarıya düşen normal öğrenci |
|---|---|---|---|---|---|---|
| **LR (ürün)** | 0.884 | 0.905 | **0.894** | 0.942 | **%1.7** | **%3.3** |
| Gradient Boosting | 0.822 | 0.881 | 0.851 | 0.948 | %2.7 | %1.9 |
| Basit kural (benzer + hızlı) | 0.237 | 0.738 | 0.358 | 0.702 | %33.3 | %40.3 |

### Senaryo bazında uyarı oranı

| Senaryo | Olması gereken | LR | GB | Basit kural |
|---|---|---|---|---|
| Etkinlik sonrası | düşük | **%0** | %0 | %79 |
| Kulüp duyurusu | düşük | **%0** | %8 | %83 |
| Yurt arkadaşları | düşük | **%0** | %0 | %0 |
| Sınav gecesi | düşük | **%31** | %0 | %88 |
| Bot ağı | yüksek | **%100** | %100 | %100 |
| Satın alınmış hesaplar | yüksek | **%94** | %88 | %75 |
| Ücretli gerçek kişiler | yüksek | **%56** | %50 | %25 |
| Yavaş kampanya | yüksek | **%25** | %25 | %0 |

## Yorum

- **Bağlam, yanlış alarmı belirleyen şeydir.** Bağlama bakmayan basit kural kulüp
  duyurularının %83'ünü, etkinlik paylaşımlarının %79'unu "şüpheli" sayıyor ve
  normal öğrencilerin %40'ını bir uyarıya sokuyor. PoA ile kanıtlanmış ortak
  etkinlik ve ortak kulüp bilgisi bu oranları %0'a indiriyor. Bu, PoP/PoA
  katmanının yalnız kimlik için değil, **adil tespit** için de gerekli olduğunu
  gösteriyor.
- **En zayıf masum senaryo sınav gecesi (%31).** Aynı bölümden öğrenciler aynı
  etiketle yazınca model zorlanıyor. Panel bu durumda "aynı bölümden, aynı sınav
  hakkında doğal paylaşım olabilir" açıklamasını gösteriyor. Son kararı insan
  veriyor.
- **Zor koordineli vakalar zor kalıyor.** Farklı cümlelerle ve hashtag'siz
  yazan ücretli gerçek kişilerin yaklaşık yarısı, ve günlere yayılan
  kampanyaların çoğu yakalanmıyor. Çoğu durumda bu kampanyalar aday kümeye bile
  girmiyor. Bunu gizlemiyoruz.

## Sınırlar

- Yalnız sentetik veri. Senaryoları biz tasarladık, gerçek kampüs davranışı daha
  karmaşık olabilir.
- Metinler şablonlardan üretildi. Gerçek dilde benzerlik dağılımı farklıdır.
- Bağlam riski düşürür. Bunu bilen bir saldırgan kampanyayı gerçek bir
  etkinliğe iliştirerek gizlemeye çalışabilir. PoA bunu zorlaştırır (katılım
  kanıtı gerekir) ama imkânsız kılmaz.
- Eşik (%50) ve aday küme parametreleri bu sentetik dünyaya göre seçildi.

## Sonraki adımlar

- Gerçek kullanıcı testi için onam formu ve veri minimizasyonu planı
- Anlam düzeyinde benzerlik (Türkçe cümle gömmeleri) ile paraphrase kampanyaları
  yakalama
- Ağ temelli model (GraphSAGE) ile karşılaştırma
