// Dil seçimi: ?lang=en ya da ?lang=tr (seçim tarayıcıda hatırlanır). Varsayılan Türkçe.
// Dil değişince sayfa yeniden yüklenir; bu yüzden modül düzeyindeki sabitler de doğru dilde kalır.

function detect() {
  let q = null;
  try { q = new URLSearchParams(window.location.search).get("lang"); } catch { /* yok */ }
  if (q === "en" || q === "tr") {
    try { localStorage.setItem("muhur-lang", q); } catch { /* özel pencere */ }
    return q;
  }
  try {
    const s = localStorage.getItem("muhur-lang");
    if (s === "en" || s === "tr") return s;
  } catch { /* yok */ }
  return "tr";
}

export const LANG = detect();
export const EN = LANG === "en";

/** L("Türkçe", "English") — aktif dildeki metni döner. */
export const L = (tr, en) => (EN ? en : tr);

export function setLang(lang) {
  try { localStorage.setItem("muhur-lang", lang); } catch { /* yok */ }
  const url = new URL(window.location.href);
  url.searchParams.set("lang", lang);
  window.location.href = url.toString();
}

if (typeof document !== "undefined") {
  document.documentElement.lang = LANG;
  if (EN) document.title = "SEAL — Trust layer for communities";
}
