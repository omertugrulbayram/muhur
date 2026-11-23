# MÜHÜR / SEAL — Gerçek mi, demo mu? Durum tablosu

Tarih: 2026-11-24 · Sürüm: v0.4 · Backend testleri: 62/62 · Saldırı koşumu: 15/15 engellendi

> 2026-11-23 denetiminden sonra 2. adım (güvenlik ve mahremiyet) yapıldı. Değişen satırlar **(v0.4)** ile işaretli.

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
| Sentetik sosyal ağ üretici | ✅ | 1000 hesap, %15 bot, "gizlenen bot" ve "yalnız kurt" türleri var. |
| Gradient Boosting modeli + ablasyon | ✅ | F1 0.989, AUC 0.998. Ağ özellikleri çıkarılınca F1 0.704'e düşüyor. |
| Sonuçların güvenilirliği | 🟡 | Sadece sentetik veride ölçüldü. Bot kümesi kendi içinde yoğun karşılıklı takipleştiği için ayırt etmesi kolay. Zor normal senaryolar (aynı etkinlikteki öğrenciler, kulüp duyurusu) test edilmedi, yanlış pozitif analizi yok. |
| Mesaj içeriği / zamanlama benzerliği | ❌ | Model sadece hesap ve takip özelliklerine bakıyor. Mesaj benzerliği ve "kısa sürede aynı paylaşım" sinyali yok. |
| Modelin kaydedilmesi ve API'den çağrılması | ❌ | Model her çalıştırmada eğitilip atılıyor, tahmin yapan bir API ucu yok. |
| **Modelin arayüze bağlı olması** | ❌ | **Arayüzdeki bot olasılıkları `App.jsx` içinde elle yazılmış sabitler** (0.03, 0.28, 0.72…). "Kampanyayı tetikle" butonu değeri 0.9 yapıyor. Arayüzdeki hiçbir sayı modelden gelmiyor. |
| Örnek hesapların risk değerleri | 🟡 | **(v0.4)** Artık istemcide değil, sunucuya `/demo/risk` ile yazılıyor ve her gerekçede "demo amaçlı elle girilmiş değer" diye görünüyor. Model bağlanınca kalkacak. |

## 4. Güven puanı

| Özellik | Durum | Not |
|---|---|---|
| Şeffaf puan formülü | ✅ | Güven = (0.65·PoP + 0.35·PoA) × (1 − bot olasılığı), kırılım ve gerekçe listesiyle birlikte. Testleri var. |
| Gerekçe listesi ("neden bu puan?") | 🟡 | Var. **(v0.4)** Yüksek riskte "son karar insan incelemesinde" notu ve elle girilmiş demo değerler için etiket eklendi. Hangi davranışın dikkat çektiği ve olası masum açıklama henüz yok (3. adım). |
| **Puanın istemci tarafından değiştirilememesi** | ✅ | **(v0.4)** `/trust/score` yalnız imzalı token kabul ediyor, bilinmeyen alanlar 422 ile reddediliyor. Risk değeri sunucu kaydından okunuyor. 2026-11-23'te sahte kanıtla 0.9997 alınan istek artık 422 dönüyor. |
| Kalıcı kayıt | ✅ | **(v0.4)** SQLite: organizatörler, etkinlikler, kullanılmış QR'lar, katılımlar, risk kayıtları. TC, isim veya doğum tarihi tutulmuyor. |

## 5. Arayüz ve ürün

| Özellik | Durum | Not |
|---|---|---|
| NSosyal akış demosu (React) | ✅ | Gerçek backend'e bağlı. Mühür rozetleri, güven bandı, filtreler var. Gönderiler ve hesaplar sabit örnek veri. |
| Simülasyon etiketleri | ✅ | "DEMO", "mock issuer", "e-Devlet entegrasyonu YOK" yazıları görünüyor. |
| Topluluk yöneticisi paneli | ❌ | Yok. |
| Şüpheli küme listesi / ağ grafiği | ❌ | Yok (`docs/network_graph.png` statik bir görsel). |
| İnsan incelemesi (onayla / izle / işaretle) | ❌ | Yok. |
| Şeffaf keşif katmanı (`discovery/`) | ❌ | Klasör boş. |
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
  - Organizatör yetkili, tek kullanımlık, 90 saniyelik QR ile check-in
  - Kalıcı replay engeli ve etkinlik başına tek katılım
  - İstemcinin değiştiremediği, sunucu tarafında hesaplanan şeffaf güven puanı
  - 62 otomatik test ve 15 saldırının engellendiğini gösteren saldırı koşumu
  - Sentetik ağ üzerinde model ve ablasyon
  - Simülasyon etiketli demo arayüz
- **"Prototip / simülasyon" diye yazılmalı:**
  - e-Devlet doğrulaması
  - Model sonuçları (sadece sentetik veri)
  - Örnek hesapların risk değerleri (elle girilmiş, etiketli)
  - İstek sınırlama (tek sunucu)
- **Şu an "var" denmemeli:**
  - Modelin canlı arayüze bağlı olması
  - Açıklanabilir uyarılar
  - Yönetici paneli ve insan incelemesi
  - Organizatör hesapları ve rolleri
  - "İlişkilendirilemez" (unlinkable) kimlik. Doğrusu takma kimlik (pseudonymous).
  - KVKK uyumu (değerlendirilmedi)

Sonraki adım: 3. bölüm. Gerçekçi sentetik kampüs, model API'ye bağlanacak, açıklanabilir uyarılar.
