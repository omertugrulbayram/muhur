# MÜHÜR / SEAL — Gerçek mi, demo mu? Durum tablosu

Tarih: 2026-11-23 · Commit: `b833171` · Backend testleri: 27/27 geçiyor

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
| İmzalı personhood token | ✅ | JWT (HS256): imza, issuer, audience ve süre kontrol ediliyor. |
| Takma kimlik ile imza için ayrı anahtar | ❌ | HMAC nişanı ile token imzası aynı PoP anahtarını kullanıyor. |

## 2. Katılım kanıtı (PoA)

| Özellik | Durum | Not |
|---|---|---|
| Kısa ömürlü, imzalı check-in QR'ı | ✅ | 90 sn geçerli, PoA anahtarıyla imzalı. |
| Tekrar kullanım (replay) engeli | 🟡 | Çalışıyor ama kullanılan kodlar bellekte tutuluyor, sunucu yeniden başlayınca sıfırlanıyor. |
| Katılımın doğrulanmış kişiye bağlanması | ✅ | Check-in, imzalı personhood token olmadan reddediliyor (Faz 4a). |
| QR'ı sadece organizatörün üretmesi | ❌ | `/poa/qr` herkese açık. Herkes her etkinlik için kendine QR üretip etkinliğe gitmeden "katıldı" kanıtı alabiliyor. |
| Etkinlik listesi / kaydı | ❌ | Etkinlikler kayıtlı değil, `event_id` serbest metin. |
| Aynı etkinliğe tek katılım | 🟡 | Güven puanında aynı etkinlik iki kez sayılmıyor ama sunucu aynı kişiye birden fazla kanıt verebiliyor. |
| İmzalı katılım kanıtı | ❌ | Verilen katılım kanıtı imzasız düz JSON. |

## 3. AI modeli (Sybil / koordineli davranış)

| Özellik | Durum | Not |
|---|---|---|
| Sentetik sosyal ağ üretici | ✅ | 1000 hesap, %15 bot, "gizlenen bot" ve "yalnız kurt" türleri var. |
| Gradient Boosting modeli + ablasyon | ✅ | F1 0.989, AUC 0.998. Ağ özellikleri çıkarılınca F1 0.704'e düşüyor. |
| Sonuçların güvenilirliği | 🟡 | Sadece sentetik veride ölçüldü. Bot kümesi kendi içinde yoğun karşılıklı takipleştiği için ayırt etmesi kolay. Zor normal senaryolar (aynı etkinlikteki öğrenciler, kulüp duyurusu) test edilmedi, yanlış pozitif analizi yok. |
| Mesaj içeriği / zamanlama benzerliği | ❌ | Model sadece hesap ve takip özelliklerine bakıyor. Mesaj benzerliği ve "kısa sürede aynı paylaşım" sinyali yok. |
| Modelin kaydedilmesi ve API'den çağrılması | ❌ | Model her çalıştırmada eğitilip atılıyor, tahmin yapan bir API ucu yok. |
| **Modelin arayüze bağlı olması** | ❌ | **Arayüzdeki bot olasılıkları `App.jsx` içinde elle yazılmış sabitler** (0.03, 0.28, 0.72…). "Kampanyayı tetikle" butonu değeri 0.9 yapıyor. Arayüzdeki hiçbir sayı modelden gelmiyor. |

## 4. Güven puanı

| Özellik | Durum | Not |
|---|---|---|
| Şeffaf puan formülü | ✅ | Güven = (0.65·PoP + 0.35·PoA) × (1 − bot olasılığı), kırılım ve gerekçe listesiyle birlikte. Testleri var. |
| Gerekçe listesi ("neden bu puan?") | 🟡 | Var ama genel cümleler. Hangi davranışın dikkat çektiği, olası masum açıklama ve "son karar insanda" notu yok. |
| **Puanın istemci tarafından değiştirilememesi** | ❌ | **`/trust/score` kimlik ve katılım kanıtlarını imzasız JSON olarak kabul ediyor, bot olasılığını da istemciden alıyor.** Elle yazılmış bir istekle herkes kendine en yüksek puanı verebilir. 2026-11-23'te denendi: sahte kanıtla **0.9997 / high** alındı. |
| Puanların kalıcı olarak saklanması | ❌ | Veritabanı yok (`db/` boş). |

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
| Asimetrik imza (Ed25519) | ❌ | HS256 kullanılıyor, doğrulayan taraf da imzalayabiliyor. |
| CORS | ❌ | Bütün kaynaklara açık (`*`). |
| İstek sınırlama (rate limit) | ❌ | Yok. |

## Başvuru metni için kısa özet

- **Rahatça "çalışıyor" denebilir:** imzalı kimlik token'ı, TC'nin saklanmaması, kısa ömürlü QR ile check-in, katılımın kişiye bağlanması, şeffaf puan formülü, sentetik ağ üzerinde model ve ablasyon, simülasyon etiketli demo arayüz.
- **"Prototip / simülasyon" diye yazılmalı:** e-Devlet doğrulaması, model sonuçları (sadece sentetik veri), arayüzdeki bot olasılıkları.
- **Şu an "var" denmemeli:** modelin canlı arayüze bağlı olması, organizatör yetkisi, kurcalanamaz güven puanı, yönetici paneli, insan incelemesi, kalıcı veritabanı.

Sonraki adım: 2. bölüm, güvenlik ve mahremiyet düzeltmeleri. Puan sunucuda hesaplanacak, imzalı kanıtlar, organizatör yetkisi, SQLite, Ed25519.
