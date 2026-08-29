"""Sayfayi sahte bir /rooms cevabina karsi calistirir.

Onemli kontrol: null "veri yok" demek, sifir degil. Bir oda penceresi bosken
sifirmis gibi cizilirse "kusursuz cevaplanmis" ile "hic veri yok" ayni yere duser.
"""
import json, os, http.server, socketserver, threading, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

PAYLOAD = {
    "fetched_at": "2026-08-29T22:10:00.000Z",
    "rooms": [
        {"room": "lobby", "topic": "", "last_seq": 9521987, "bytes": 10485760,
         "idle_seconds": 3, "window": 200, "zero_response_share": 0.965, "nick_diversity": 0.83},
        {"room": "gpu-miners", "topic": "", "last_seq": 4102, "bytes": 210000,
         "idle_seconds": 900, "window": 200, "zero_response_share": 1.0, "nick_diversity": 0.02},
        {"room": "kibble", "topic": "work board", "last_seq": 88213, "bytes": 900000,
         "idle_seconds": 40, "window": 200, "zero_response_share": 0.42, "nick_diversity": 0.55},
        {"room": "technocore", "topic": "", "last_seq": 55010, "bytes": 400000,
         "idle_seconds": 120, "window": 60, "zero_response_share": 0.72, "nick_diversity": 0.40},
        # penceresi bos: cizilmemeli
        {"room": "empty-room", "topic": "", "last_seq": 0, "bytes": 0,
         "idle_seconds": 500000, "window": 0, "zero_response_share": None, "nick_diversity": None},
    ],
    "total": 3184, "capacity": 40960, "bytes": 1288490188, "bytes_capacity": 5368709120,
    "notes": {"total": 5120, "bytes": 786432},
    "engagement": {"window_cap": 200, "windowed_messages": 660,
                   "zero_response_share": 0.8123, "nick_diversity": 0.4712,
                   "windowed_note_to_message_ratio": 7.76},
}

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 8083), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

fails = []
state = {"mode": "ok"}


def route(r):
    if state["mode"] == "fail":
        r.fulfill(status=502, content_type="application/json", body='{"error":"upstream 503"}')
    else:
        r.fulfill(status=200, content_type="application/json", body=json.dumps(PAYLOAD))


with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_context(viewport={"width": 1180, "height": 1150},
                         device_scale_factor=2).new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))
    page.route("**/api/rooms**", route)
    page.goto("http://127.0.0.1:8083/index.html")
    page.wait_for_timeout(1500)

    hero = page.inner_text("#heroNum")
    print("  manşet:", hero, "|", page.inner_text("#heroClaim"))
    if hero != "81%":
        fails.append(f"manşet yanlış: {hero} (81% olmalı)")

    rows = page.eval_on_selector_all("#rooms .room", """els => els.map(e => ({
        name: e.querySelector('.rname .n').textContent,
        pct: e.querySelector('.pct').textContent,
        width: e.querySelector('.fill').style.width
    }))""")
    print(f"  çizilen oda: {len(rows)}")
    for r in rows:
        print(f"    {r['name']:<16} {r['pct']:>5}  bar={r['width']}")

    names = [r["name"] for r in rows]
    if "/r/empty-room" in names:
        fails.append("penceresi boş oda çizilmiş — null sıfır gibi gösterilmiş")
    if len(rows) != 4:
        fails.append(f"beklenen 4 satır, gelen {len(rows)}")
    if names[0] != "/r/gpu-miners":
        fails.append(f"sıralama yanlış: en ölü oda başta olmalı, başta {names[0]}")

    stats = page.eval_on_selector_all("#stats .stat .n", "e => e.map(x => x.textContent)")
    print("  kartlar:", stats)
    if "5,120" not in stats:
        fails.append("not sayısı kartta yok")

    page.screenshot(path="/mnt/user-data/outputs/technocore-vitals.png", full_page=True)

    # okuma coktugunde son iyi degerler ekranda kalmali
    state["mode"] = "fail"
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(1200)
    page.evaluate("""() => {
        Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
        document.dispatchEvent(new Event('visibilitychange'));
    }""")
    page.wait_for_timeout(1500)
    st = page.inner_text("#state")
    kept = page.eval_on_selector_all("#rooms .room", "e => e.length")
    print(f"  okuma çöktü → {st[:56]!r} · ekranda kalan satır: {kept}")
    if kept != 4:
        fails.append("okuma çöktüğünde tablo boşaldı")
    if "failed" not in st:
        fails.append("okuma çöktü ama durum satırı söylemiyor")

    print("  pageerror:", errs[:2] or "(yok)")
    if errs:
        fails.append("pageerror: " + errs[0])
    b.close()

httpd.shutdown()
print("\nSONUC:", "HEPSI GECTI" if not fails else "BASARISIZ")
for f in fails:
    print(" -", f)
