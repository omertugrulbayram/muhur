// NSosyal MÜHÜR — backend API istemcisi.
// Backend calisiyor olmali:  uvicorn app.main:app --reload  (127.0.0.1:8000)
const BASE = "http://127.0.0.1:8000";

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Sunucu hatasi (${res.status})`);
  }
  return res.json();
}

export const api = {
  health: () => fetch(BASE + "/health").then((r) => r.json()),
  popVerify: (national_id, birth_year) =>
    post("/pop/verify", { national_id, birth_year }),
  poaQr: (event_id) => post("/poa/qr", { event_id }),
  poaCheckin: (checkin_token, personhood_token) =>
    post("/poa/checkin", { checkin_token, personhood_token }),
  trustScore: (personhood_credential, attendance_credentials, sybil_probability) =>
    post("/trust/score", {
      personhood_credential,
      attendance_credentials,
      sybil_probability,
    }),
};
