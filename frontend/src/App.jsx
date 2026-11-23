import Demo from "./Demo";
import Landing from "./Landing";
import Panel from "./Panel";
import { useHash } from "./shared";

/* ============================================================
   NSosyal MÜHÜR — yönlendirme
   #/            açılış: nasıl çalışır, ne gerçek ne demo
   #/demo        kullanıcı demosu (PoP → PoA → akış)
   #/panel...    topluluk yöneticisi paneli
   ============================================================ */
export default function App() {
  const hash = useHash();
  if (hash.startsWith("#/panel")) return <Panel />;
  if (hash.startsWith("#/demo")) return <Demo />;
  return <Landing />;
}
