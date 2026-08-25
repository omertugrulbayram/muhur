# MÜHÜR — Tehdit Modeli (STRIDE)

## Durum
Bu doküman, mevcut prototipte **gerçekten test edilmiş** tehditleri ve
**henüz test edilmemiş / roadmap'te olan** tehditleri açıkça ayırır.

## STRIDE Kategorileri

| Kategori | Tehdit | Karşı Önlem | Test Durumu |
|---|---|---|---|
| Spoofing | Sahte kimlik / sahte katılım | PoP unlinkable nişan; PoA fiziksel QR + PoP'a bağlama | ✅ Kod + test var (replay/tamper/expiry) |
| Tampering | QR/JWT payload değiştirme | Sunucu-taraflı imza doğrulama (HMAC/JWT) | ✅ Test edildi (`test_tampered_token_is_rejected`) |
| Repudiation | İşlemi inkâr etme | İmzalı, zaman damgalı credential'lar | ⚠️ Kavramsal tasarım; loglama/denetim izi kodlanmadı |
| Spoofing (kimlik iddiası uydurma) | PoA'ya sahte/uydurma bir uniqueness_nishani göndermek | PoP→PoA sunucu-taraflı bağlama: PoA artık yalnızca PoP'un imzaladığı personhood_token'ı kabul eder | ✅ **18 Ağu 2026'da kapatıldı** — `test_forged_personhood_claim_is_rejected` ile kanıtlı |
| Information Disclosure | Kimlik bilgisi sızıntısı | TC saklanmaz, yalnızca unlinkable nişan | ✅ Test edildi (`test_nishani_is_deterministic_and_unlinkable`) |
| Denial of Service | QR/istek bombardımanı | Hız sınırlama (rate limiting) | ❌ Henüz kodlanmadı (roadmap) |
| Elevation of Privilege | Yetkisiz erişim | Her adımda credential doğrulama | ⚠️ Temel akışta var; rol/yetki sistemi henüz yok |

## Gerçekten Test Edilen Saldırılar (kod + pytest + attack_harness)
- **Replay** (QR'ın tekrar okutulması) — `attack_harness/replay_attack.py`
- **Tamper** (JWT imzasının bozulması) — aynı script
- **Expiry** (süresi dolmuş token'ın kullanılması) — aynı script

## Tasarımda Ele Alınan Ama HENÜZ Kodda Test Edilmeyen Saldırılar
Bunlar rapor ve mimaride **savunma prensibi olarak tasarlanmıştır**
(örn. "sunucu-taraflı doğrulama, istemciye güvenilmez" ilkesi bunları kapsar),
ancak **gerçek bir saldırı simülasyonu ile ölçülmemiştir**:
- GPS spoofing (mock GPS uygulaması ile konum taklidi)
- Relay saldırısı (credential'ın fiziksel olarak uzağa iletilmesi)
- Emülatör / root / jailbreak tespiti
- Frida ile çalışma-zamanı (runtime) manipülasyonu

Bu dördü şu an **prototipte kod olarak yok**; çünkü mobil istemci (Android/iOS)
henüz geliştirilmedi — bu saldırılar doğası gereği bir mobil istemciye ihtiyaç
duyar. Backend'in "istemciye güvenme" ilkesi bunlara karşı yapısal bir zemin
sağlar, ancak somut test/ölçüm yapılmamıştır. Yol haritasında mobil istemci
geliştirmesiyle birlikte ele alınacaktır.


## Güncelleme Günlüğü

- **18 Ağu 2026:** Rapor Bölüm 3.1'de işaretlenen 'PoP→PoA sunucu-taraflı bağlama eksikliği' kapatıldı. PoP artık kısa ömürlü (10 dk), ayrı bir anahtarla (`MUHUR_POP_SECRET`) imzalanmış bir personhood token üretiyor; PoA bu token'ın imzasını doğrulamadan hiçbir katılım nişanı vermiyor. 9. test (`test_forged_personhood_claim_is_rejected`) bunu kanıtlıyor.
