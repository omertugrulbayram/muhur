# MÜHÜR / SEAL — Gerçek mi, demo mu? Durum tablosu

Tarih: 2026-11-24 · Sürüm: v0.5 · Backend testleri: 73/73 · Saldırı koşumu: 15/15 engellendi

> 2026-11-23 denetiminden sonra 2. adım (güvenlik, **v0.4**) ile 3. ve 4. adımlar (model + yönetici paneli, **v0.5**) yapıldı. Değişen satırlar sürümle işaretli.

Bu tablo, prototipte neyin gerçekten çalıştığını, neyin simülasyon olduğunu ve
neyin henüz hiç olmadığını ayırır. Başvuru metinlerinde "çalışıyor" denecek her
şey bu tabloda ✅ olmalıdır.

**İşaretler:** ✅ gerçekten çalışıyor · 🟡 çalışıyor ama simülasyon/eksik · ❌ yok ya da hatalı

## 1. İnsan doğrulama (PoP)

| Özellik | Durum | Not |
|---|---|---|
| Kimlik doğrulama (e-Devlet) | 🟡 | Mock issuer. Gerçek e-Devlet entegrasyonu yok, arayüzde "DEMO" olarak yazıyor. Şifre alanı hiçbir şey kontrol etmiyor. |
| TC numarasının saklanmaması | ✅ | TC'den tek yönlü HMAC ile takma kimlik üretiliyor, TC hiçbir yere yazılmıyor. |
| Yalnızca "15+" bilgisinin taşınması | ✅ | Doğum tarihi credential'a girmiyor. Kesin yaş hesabı ve 29 Şubat testi var. Arayüz ise doğum yılını sabit 2000 gönderiyor. |
| İmzalı personhood token | ✅ | **(v0.4)** Ed25519 imzalı JWT. İmza, issuer, audience, tür ve süre kontrol ediliyor. `alg=none` ve algoritma karıştırma saldırıları reddediliyor. |
| Takma kimlik ile imza için ayrı anahtar | ✅ | **(v0.4)** Takma kimlik ayrı bir HMAC anahtarıyla üretiliyor. |

## 2. Katılım kanıtı (PoA)

| Özellik | Durum | Not |
|---|---|---|
| Kısa ömürlü, imzalı check-in QR'ı | ✅ | 90 sn geçerli, PoA'nın Ed25519 anahtarıyla imzalı. |
| Tekrar kullanım (replay) engeli | ✅ | **(v0.4)** Kullanılmış QR'lar SQLite'ta. Sunucu yeniden başlayınca da geçerli, testi var. |
| Katılımın doğrulanmış kişiye bağlanması | ✅ | Check-in, imzalı personhood token olmadan reddediliyor (Faz 4a). |
| QR'ı sadece organizatörün üretmesi | ✅ | **(v0.4)** QR'ı yalnız etkinliğin sahibi, organizatör anahtarıyla ve etkinlik açıkken üretebiliyor. Anahtar veritabanında özet olarak saklanıyor. Kullanıcı hesabı ve rol sistemi yok, tek paylaşılan anahtar var. |
| Etkinlik listesi / kaydı | ✅ | **(v0.4)** Etkinlikler başlangıç ve bitiş saatiyle veritabanında. Organizatör API'den oluşturup listeleyebiliyor, arayüzü henüz yok. |
| Aynı etkinliğe tek katılım | ✅ | **(v0.4)** Veritabanı kısıtıyla garanti: ikinci check-in 409 alıyor. |
| İmzalı katılım kanıtı | ✅ | **(v0.4)** Ed25519 imzalı, kişinin takma kimliğine bağlı. Sunucu kaydıyla karşılaştırılıyor, iptal edilebiliyor. |

## 3. AI modeli (Sybil / koordineli davranış)

| Özellik | Durum | Not |
|---|---|---|
| Sentetik kampüs üretici | ✅ | **(v0.5)** ~600 hesap, iki haftalık paylaşım akışı, kulüp/yurt/bölüm/etkinlik bağlamı. 4 masum (etkinlik, kulüp duyurusu, yurt, sınav gecesi) ve 4 koordineli senaryo (bot ağı, satın alınmış hesap, ücretli gerçek kişi, yavaş kampanya). Eski 1000 hesaplık ağ üreteci de duruyor. |
| Koordinasyon modeli | ✅ | **(v0.5)** Küme düzeyinde, açıklanabilir lojistik regresyon. Görülmemiş test dünyalarında F1 0.89. Basit kurala göre normal öğrencilerin uyarıya düşme oranı %40 → %3. Ayrıntı: `docs/model_degerlendirme.md`. Eski Gradient Boosting baseline (F1 0.989, kolay ağ) karşılaştırma olarak duruyor. |
| Sonuçların güvenilirliği | 🟡 | **(v0.5)** Zor masum senaryolar ve yanlış pozitif oranları ölçüldü. Yine de **yalnız sentetik veri**. Zayıf noktalar raporda açıkça yazılı: sınav gecesinde %31 yanlış alarm; ücretli gerçek kişilerde %56, yavaş kampanyada %25 tespit. |
| Mesaj içeriği / zamanlama benzerliği | ✅ | **(v0.5)** TF-IDF metin benzerliği, ortak hashtag ve zaman penceresiyle aday küme bulunuyor. Anlam düzeyinde (paraphrase) benzerlik yok. |
| Modelin kaydedilmesi ve API'den çağrılması | ✅ | **(v0.5)** Model JSON olarak kayıtlı (pickle değil). Açılışta demo kampüs analiz ediliyor, uyarılar ve hesap riskleri veritabanına yazılıyor. `/organizer/alerts`, `/organizer/model` uçları var. |
| **Modelin arayüze bağlı olması** | ✅ | **(v0.5)** Paneldeki tüm uyarılar ve akıştaki hesapların risk değerleri modelden geliyor. Elle yazılmış sabit kalmadı. Akış hesapları sentetik demo kampüsünden seçiliyor. |
| Elle risk girme (`/demo/risk`) | 🟡 | **(v0.5)** Arayüz artık kullanmıyor. Uç yalnız demo modunda ve organizatör anahtarıyla duruyor, kayıt `manual-demo` olarak etiketleniyor. |

## 4. Güven puanı

| Özellik | Durum | Not |
|---|---|---|
| Şeffaf puan formülü | ✅ | Güven = (0.65·PoP + 0.35·PoA) × (1 − bot olasılığı), kırılım ve gerekçe listesiyle birlikte. Testleri var. |
| Açıklanabilir uyarılar | ✅ | **(v0.5)** Her uyarıda modelin katkılarından üretilen "neden dikkat çekti" ve "riski azaltanlar" listeleri var. Olası masum açıklamalar (ortak etkinlik, kulüp, bölüm) ve "son karar insanda" notu her zaman gösteriliyor. Cümlelerin modelle tutarlılığı testle kilitli. |
| **Puanın istemci tarafından değiştirilememesi** | ✅ | **(v0.4)** `/trust/score` yalnız imzalı token kabul ediyor, bilinmeyen alanlar 422 ile reddediliyor. Risk değeri sunucu kaydından okunuyor. 2026-11-23'te sahte kanıtla 0.9997 alınan istek artık 422 dönüyor. |
| Kalıcı kayıt | ✅ | **(v0.4)** SQLite: organizatörler, etkinlikler, kullanılmış QR'lar, katılımlar, risk kayıtları. TC, isim veya doğum tarihi tutulmuyor. |

## 5. Arayüz ve ürün

| Özellik | Durum | Not |
|---|---|---|
| NSosyal akış demosu (React) | ✅ | Gerçek backend'e bağlı. **(v0.5)** Hesaplar ve paylaşımlar sentetik kampüsten, riskler modelden. Yüksek riskli kümedeki hesapta "yargı değil, inceleme bekliyor" notu ve panele bağlantı var. |
| Simülasyon etiketleri | ✅ | "DEMO", "mock issuer", "e-Devlet entegrasyonu YOK" yazıları görünüyor. |
| Topluluk yöneticisi paneli | ✅ | **(v0.5)** `#/panel`. Organizatör anahtarıyla giriliyor. Uyarı listesi ve risk filtresi, detay, paylaşımlar, hesap tablosu ve model kartı var. Her ekranda "DEMO VERİ" etiketi var. |
| Şüpheli küme listesi / ağ grafiği | ✅ | **(v0.5)** Etkileşimli ağ grafiği: mühürlü/mühürsüz, yeni hesap, takip ve benzer paylaşım bağlantıları. |
| İnsan incelemesi | ✅ | **(v0.5)** Sorun yok / İzle / İşaretle kararları notla birlikte kalıcı kaydediliyor. Geçmiş görünüyor, model yeniden çalışınca karar korunuyor. Kararlar şimdilik başka bir yere aktarılmıyor (ör. modeli yeniden eğitmek için). |
| Şeffaf keşif katmanı (`discovery/`) | ❌ | Klasör boş. Akıştaki "Neden bunu görüyorum?" güven gerekçelerini gösteriyor ama ayrı bir keşif/sıralama katmanı yok. |
| İnternette yayın | ❌ | Sadece yerelde çalışıyor (`127.0.0.1`). |

## 6. Altyapı ve güvenlik

| Özellik | Durum | Not |
|---|---|---|
| Ayrı PoP/PoA anahtarları, fail-closed config | ✅ | `APP_ENV=demo` ortamında anahtar eksikse servis başlamıyor. |
| Güvenlik zinciri testleri | ✅ | Sahte token, yanlış audience, süre dolması ve replay için testler var. |
| Asimetrik imza (Ed25519) | ✅ | **(v0.4)** Açık anahtarlar `/.well-known/muhur-keys` adresinde, üçüncü taraf bağımsız doğrulayabiliyor (testi var). |
| CORS | ✅ | **(v0.4)** Yalnız izinli kökenler. demo/üretimde `*` verilirse servis başlamıyor. |
| İstek sınırlama (rate limit) | 🟡 | **(v0.4)** IP + uç başına dakikalık sınır. Bellek içi, tek sunucuda geçerli. |


## Başvuru metni için kısa özet

- **Rahatça "çalışıyor" denebilir:**
  - Ed25519 imzalı kimlik ve katılım kanıtları, açık anahtarla bağımsız doğrulama
  - TC kimlik numarasının saklanmaması (veritabanı dosyası dahil test edildi)
  - Organizatör yetkili, tek kullanımlık, 90 saniyelik QR ile check-in; kalıcı replay engeli
  - İstemcinin değiştiremediği, sunucu tarafında hesaplanan güven puanı
  - Arayüze bağlı, açıklanabilir koordinasyon modeli
  - Topluluk yöneticisi paneli: uyarı nedenleri, olası masum açıklamalar, ağ grafiği, insan incelemesi
  - 73 otomatik test, 15 saldırının engellendiğini gösteren saldırı koşumu
- **"Prototip / simülasyon" diye yazılmalı:**
  - e-Devlet doğrulaması
  - Tüm kampüs verisi ve model sonuçları (sentetik)
  - İstek sınırlama (tek sunucu)
- **Şu an "var" denmemeli:**
  - Gerçek kullanıcı verisiyle test
  - Organizatör hesapları ve rolleri
  - Anlam düzeyinde (paraphrase) metin benzerliği, GNN
  - "İlişkilendirilemez" (unlinkable) kimlik. Doğrusu takma kimlik (pseudonymous).
  - KVKK uyumu (değerlendirilmedi)
  - İnternette yayın (henüz yok)
- **Söylenmesi güçlü olan dürüst rakamlar:** Bağlama bakmayan basit kural normal
  öğrencilerin %40'ını uyarıya sokuyor, MÜHÜR modeli %3'ünü. Kulüp duyurusu ve
  etkinlik paylaşımlarında yanlış alarm %80'den %0'a iniyor. Zor vakalar da
  rakamlarıyla açıkça yazılı.

Sonraki adımlar: test raporunun genişletilmesi (5), internette yayın ve demo video (6).
