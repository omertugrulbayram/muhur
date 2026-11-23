# MÜHÜR — Tehdit Modeli (STRIDE)

Sürüm: v0.4 · 2026-11-24

Bu doküman, prototipte **kodla engellenen ve testle kanıtlanan** tehditleri,
**kısmen ele alınanları** ve **hiç ele alınmayanları** açıkça ayırır. "✅" yazan
her satırın arkasında bir pytest testi veya saldırı koşumu adımı vardır.

## Güven ilkesi

İstemciye güvenilmez. Güven kararını etkileyen her girdi ya sunucunun Ed25519
ile imzaladığı bir token'dır ya da sunucunun kendi veritabanı kaydıdır. Güven
puanı uçları bilinmeyen alanları reddeder: istemci kimlik JSON'u veya bot
olasılığı gönderemez.

## Anahtarlar

| Anahtar | Tür | Ne imzalar / ne üretir |
|---|---|---|
| PoP imza anahtarı | Ed25519 | personhood token |
| PoA imza anahtarı | Ed25519 | check-in QR'ı, katılım kanıtı |
| Takma kimlik anahtarı | HMAC-SHA256 sırrı | TC → takma kimlik (imza için kullanılmaz) |

Açık anahtarlar `/.well-known/muhur-keys` adresinde yayınlanır. Doğrulama
yalnız `EdDSA` algoritmasını kabul eder. Her token'ın bir türü (`typ`) ve hedef
kitlesi (`aud`) vardır, bir tür başka bir türün yerine kullanılamaz.
demo/production ortamında anahtar eksikse servis başlamaz (fail-closed).

## STRIDE

| Kategori | Tehdit | Önlem | Durum |
|---|---|---|---|
| Spoofing | Sahte kimlik token'ı (başka anahtar, `alg=none`, HS256 + açık anahtar) | Ed25519 imza doğrulama, yalnız EdDSA | ✅ `test_security_chain.py` |
| Spoofing | Elle yazılmış JSON "kanıtla" güven puanı almak | `/trust/score` yalnız imzalı token kabul eder, bilinmeyen alan 422 | ✅ `test_old_forged_json_exploit_is_rejected` (eski sürümde 0.9997 veriyordu) |
| Spoofing | Etkinliğe gitmeden kendine QR üretmek | QR'ı yalnız etkinlik sahibi organizatör, etkinlik açıkken üretir | ✅ `test_challenge_requires_organizer_key`, `test_other_organizer_cannot_issue_for_my_event` |
| Spoofing | Başkasının katılım kanıtını kullanmak | Kanıt takma kimliğe bağlı, imzalı, sunucu kaydıyla karşılaştırılır | ✅ `test_someone_elses_attendance_not_counted` |
| Tampering | QR veya token içeriğini değiştirmek | İmza doğrulama | ✅ `test_tampered_challenge_rejected` |
| Tampering | İstemcinin kendi bot olasılığını göndermesi | Risk yalnız sunucu kaydından okunur | ✅ `test_client_cannot_send_sybil_probability` |
| Replay | Aynı QR'ı ikinci kez kullanmak | Kullanılmış QR'lar SQLite'ta, tek işlemde tüketilir | ✅ `test_replay_is_blocked`, `test_replay_survives_restart` |
| Replay | Aynı kişinin aynı etkinliğe birden fazla katılım kanıtı alması | `UNIQUE(event_id, subject)` | ✅ `test_same_person_cannot_attend_twice` |
| Repudiation | İşlemi inkâr etmek | İmzalı, zaman damgalı token'lar; katılım ve risk kayıtları veritabanında | 🟡 Kayıt var, ayrı bir denetim günlüğü (kim neyi ne zaman değiştirdi) yok |
| Information Disclosure | TC kimlik sızıntısı | TC hiçbir yere yazılmaz; yalnız HMAC takma kimlik | ✅ `test_no_raw_national_id_anywhere` (veritabanı dosyası dahil) |
| Information Disclosure | Organizatör anahtarı sızıntısı | Veritabanında SHA-256 özeti | ✅ `test_organizer_key_stored_hashed` |
| Information Disclosure | Başka sitelerin API'yi tarayıcıdan çağırması | CORS yalnız izinli kökenler; demo/prod'da `*` yasak | ✅ `test_cors_blocks_unknown_origin`, `test_demo_env_rejects_wildcard_cors` |
| Denial of Service | İstek bombardımanı | IP + uç başına dakikalık sınır (bellek içi) | 🟡 `test_rate_limit`; tek süreçte geçerli, çok sunucuda ortak depo gerekir |
| Elevation of Privilege | Yetkisiz organizatör işlemi | `X-Organizer-Key`, etkinlik sahipliği kontrolü | ✅ `test_wrong_organizer_key_rejected` |
| Elevation of Privilege | Demo uçlarıyla risk değerini değiştirmek | `/demo/*` yalnız demo modunda + organizatör anahtarıyla; kayıt `manual-demo` olarak etiketlenir | ✅ `test_demo_risk_requires_organizer`, `test_demo_risk_disabled_outside_demo_mode` |

## Bilinen sınırlar (dürüstçe)

- **Takma kimlik "unlinkable" değildir.** Takma kimlik anahtarını tutan sunucu
  aynı kişiyi farklı oturumlarda tanıyabilir. Doğru terim "pseudonymous"tur.
  Gerçek ilişkilendirilemezlik için kör imza veya sıfır bilgi ispatı gerekir
  (yol haritası).
- **PoP issuer simülasyondur.** Gerçek e-Devlet bağlantısı yoktur. Arayüzdeki
  şifre alanı hiçbir şey kontrol etmez.
- **QR fiziksel varlığı kanıtlamaz.** QR'ın fotoğrafı 90 saniye içinde uzaktaki
  birine gönderilirse o kişi check-in yapabilir. Kısa süre ve tek kullanım bu
  pencereyi daraltır ama kapatmaz. Dönen QR, konum veya cihaz doğrulaması gerekir.
- **Organizatör anahtarı tek bir paylaşılan sırdır.** Kullanıcı hesabı, rol,
  anahtar yenileme ve iptal yoktur.
- **Personhood token'ı çalınırsa** süresi (varsayılan 1 saat) dolana kadar
  kullanılabilir. Cihaza bağlama (DPoP vb.) yoktur.
- **Anahtar yenileme (rotation)** yoktur. `kid` alanı taşınıyor, altyapı buna hazır.
- **Mobil istemci saldırıları** (GPS taklidi, emülatör, Frida) mobil istemci
  olmadığı için test edilmedi.

## Saldırı koşumu

`backend/.venv/Scripts/python attack_harness/replay_attack.py` gerçek HTTP API'ye
karşı 15 saldırı dener. 2026-11-24 sonucu: **15/15 engellendi.**

## Güncelleme günlüğü

- **18 Ağu 2026:** PoP→PoA sunucu tarafı bağlama eklendi (Faz 4a).
- **23 Kas 2026:** Denetimde üç açık doğrulandı: `/trust/score` imzasız JSON
  kanıtla 0.9997 puan veriyordu, istemci kendi bot olasılığını gönderebiliyordu,
  `/poa/qr` herkese açıktı.
- **24 Kas 2026 (v0.4):** Üç açık kapatıldı. HS256 → Ed25519, ayrı takma kimlik
  anahtarı, SQLite kalıcı kayıt, organizatör yetkisi, etkinlik zaman penceresi,
  etkinlik başına tek katılım, imzalı katılım kanıtı, sıkı CORS, istek sınırı.
  Test sayısı 27 → 62.
