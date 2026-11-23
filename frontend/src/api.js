// NSosyal MÜHÜR — backend API istemcisi (v0.4).
// Backend çalışıyor olmalı:  uvicorn app.main:app --reload  (127.0.0.1:8000)
//
// Güvenlik notu: istemci artık güven kararını etkileyen hiçbir değeri (kimlik
// JSON'u, bot olasılığı) göndermez; yalnız sunucunun imzaladığı token'ları taşır.
const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// DEMO: Bu arayüz, örnek hesapları etkinliğe "check-in" yaptırabilmek için demo
// kulübün organizatör rolünü de oynar. Gerçek üründe bu anahtar yalnız
// organizatör panelinde bulunur, kullanıcı uygulamasında olmaz.
export const DEMO_ORGANIZER_KEY =
  import.meta.env.VITE_DEMO_ORGANIZER_KEY || "demo-kulup-anahtari";

async function request(method, path, body, headers = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const err = new Error(
      typeof detail.detail === "string" ? detail.detail : `Sunucu hatası (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

const post = (path, body, headers) => request("POST", path, body, headers);
const org = { "X-Organizer-Key": DEMO_ORGANIZER_KEY };

export const api = {
  health: () => request("GET", "/health"),
  popVerify: (national_id, birth_year) =>
    post("/pop/verify", { national_id, birth_year }),
  // organizatör (demo kulüp) QR challenge'ı üretir
  poaChallenge: (event_id) => post("/poa/challenge", { event_id }, org),
  poaCheckin: (checkin_token, personhood_token) =>
    post("/poa/checkin", { checkin_token, personhood_token }),
  trustScore: (personhood_token, attendance_tokens = []) =>
    post("/trust/score", { personhood_token, attendance_tokens }),
  // SİMÜLASYON: model bağlanana kadar demo hesaplara elle risk değeri yazar
  demoRisk: (personhood_token, probability, note) =>
    post("/demo/risk", { personhood_token, probability, note }, org),
};
