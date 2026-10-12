"""UI regression under bad conditions. Prints PASS/FAIL per scenario."""
import asyncio
import os
import signal
import subprocess
import time
import urllib.request

from playwright.async_api import async_playwright

B = "http://localhost:3000"
API = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT, exist_ok=True)
results = []


def check(name, ok, info=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{info}]" if info else ""))


def post(path, body=b"{}", ctype="application/json"):
    req = urllib.request.Request(API + path, data=body, headers={"Content-Type": ctype}, method="POST")
    return urllib.request.urlopen(req, timeout=10).read()


async def no_hscroll(pg):
    return await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


async def main():
    post("/reset")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 950})
        pg = await ctx.new_page()
        errors, dialogs = [], []
        pg.on("pageerror", lambda e: errors.append(str(e)[:160]))
        pg.on("dialog", lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))

        # 1. corrupted localStorage must not break boot
        await pg.goto(B + "/")
        await pg.evaluate("""localStorage.setItem('wb.settings','{bad json');
                             localStorage.setItem('wb.profile','null');
                             localStorage.setItem('wb.persona','persona_that_does_not_exist')""")
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(800)
        check("boots with corrupted localStorage", await pg.is_visible("text=Ask across") and not errors, "; ".join(errors))

        # 2. XSS payloads in documents and personas never execute
        xss = b"<img src=x onerror=alert('xss1')> <script>alert('xss2')</script> [click](javascript:alert('xss3')) owner Bob"
        post("/upload", body=b"--B\r\nContent-Disposition: form-data; name=\"file\"; filename=\"xss.md\"\r\nContent-Type: text/markdown\r\n\r\n" + xss + b"\r\n--B--\r\n",
             ctype="multipart/form-data; boundary=B")
        post("/persona", body=b'{"label": "<img src=x onerror=alert(4)>", "memories": ["<script>alert(5)</script>"]}')
        await pg.goto(B + "/", wait_until="networkidle")
        await pg.fill("input.input", "who is the owner")
        await pg.click("button[type=submit]"); await pg.wait_for_selector(".answer", timeout=15000); await pg.wait_for_timeout(1200)
        await pg.locator("details.fold summary").first.click()
        await pg.goto(B + "/personas", wait_until="networkidle"); await pg.wait_for_timeout(800)
        links = await pg.evaluate("[...document.querySelectorAll('a')].filter(a => a.href.startsWith('javascript')).length")
        check("XSS payloads do not execute", not dialogs and links == 0, f"dialogs={dialogs} js-links={links}")
        await pg.screenshot(path=f"{OUT}/u2_xss_personas.png")

        # 3. readable validation error in the UI (1001-char change)
        await pg.goto(B + "/impact", wait_until="networkidle")
        await pg.fill("input.input", "x" * 1001)
        await pg.click("button[type=submit]"); await pg.wait_for_timeout(1500)
        body = await pg.inner_text("main")
        check("validation error shown readably", "at most 1000" in body and "[object Object]" not in body)

        # 4. unsupported + binary uploads show clean errors in Activity
        await pg.goto(B + "/knowledge", wait_until="networkidle")
        await pg.set_input_files("input[type=file]", files=[
            {"name": "virus.exe", "mimeType": "application/octet-stream", "buffer": b"MZ"},
            {"name": "junk.txt", "mimeType": "text/plain", "buffer": bytes(range(256)) * 20},
            {"name": "ok.md", "mimeType": "text/markdown", "buffer": b"Lena owns observability."}])
        await pg.wait_for_timeout(2500)
        act = await pg.inner_text("main")
        check("bad uploads rejected with messages, good one accepted",
              "Unsupported file type" in act and "binary" in act and "ok.md" in act, act[act.find("Activity"):][:220].replace("\n", " | "))
        await pg.screenshot(path=f"{OUT}/u4_upload_errors.png")

        # 5. rapid repeated clicks on Ask don't break anything
        post("/sample")
        await pg.goto(B + "/", wait_until="networkidle")
        await pg.fill("input.input", "What would break if we deprecated the v1 payments API?")
        for _ in range(8):
            await pg.click("button[type=submit]", force=True, no_wait_after=True)
        await pg.wait_for_selector(".answer.win", timeout=20000); await pg.wait_for_timeout(1500)
        cards = await pg.locator(".answer").count()
        check("rapid clicks render one result set", cards == 2 and not errors, f"cards={cards}")

        # 6. long persona label & long question: no horizontal overflow
        post("/persona", body=('{"label": "%s"}' % ("Very Long Persona Name " * 4)[:80]).encode())
        await pg.goto(B + "/personas", wait_until="networkidle"); await pg.wait_for_timeout(600)
        ok1 = await no_hscroll(pg)
        await pg.goto(B + "/", wait_until="networkidle")
        await pg.fill("input.input", "supercalifragilistic" * 60)
        await pg.click("button[type=submit]"); await pg.wait_for_timeout(1500)
        check("no horizontal overflow with long content", ok1 and await no_hscroll(pg))

        # 7. every page at phone width without horizontal scroll
        m = await ctx.new_page()
        await m.set_viewport_size({"width": 375, "height": 800})
        bad = []
        for path in ["/", "/impact", "/knowledge", "/personas", "/graph", "/integrations", "/about"]:
            await m.goto(B + path, wait_until="networkidle"); await m.wait_for_timeout(700)
            if not await no_hscroll(m):
                w = await m.evaluate("document.documentElement.scrollWidth")
                bad.append(f"{path}:{w}px")
        await m.screenshot(path=f"{OUT}/u7_mobile_about.png")
        check("all pages fit a 375px phone", not bad, ", ".join(bad))

        # 8. settings + profile persist across reload
        await pg.goto(B + "/", wait_until="networkidle")
        await pg.click("button[aria-label=Settings]"); await pg.wait_for_timeout(500)
        await pg.click("span[title=rose]"); await pg.wait_for_timeout(300)
        await pg.click("button[aria-label=Close]"); await pg.wait_for_timeout(400)
        await pg.click("button[aria-label=Profile]"); await pg.click("text=Edit profile"); await pg.wait_for_timeout(400)
        await pg.fill("input[placeholder='Your name']", "Vik Rao"); await pg.click("text=Save profile"); await pg.wait_for_timeout(1200)
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(800)
        accent = await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()")
        avatar = await pg.inner_text("button[aria-label=Profile]")
        check("settings and profile persist after reload", accent == "#fb7185" and avatar.strip() == "VR", f"accent={accent} avatar={avatar!r}")

        # 9. unknown route -> not-found page, shell intact
        await pg.goto(B + "/does-not-exist", wait_until="networkidle"); await pg.wait_for_timeout(500)
        check("unknown route shows not-found", await pg.is_visible("text=Page not found") and await pg.is_visible("text=WhyBot"))

        # 10. backend down: app stays up, shows clear error, recovers
        pid = subprocess.run(["lsof", "-ti", "tcp:8000"], capture_output=True, text=True).stdout.split()
        for x in pid:
            os.kill(int(x), signal.SIGTERM)
        time.sleep(1.5)
        await pg.goto(B + "/", wait_until="domcontentloaded"); await pg.wait_for_timeout(2500)
        await pg.fill("input.input", "anyone there?")
        await pg.click("button[type=submit]"); await pg.wait_for_timeout(2500)
        txt = await pg.inner_text("body")
        shot = f"{OUT}/u10_backend_down.png"
        await pg.screenshot(path=shot)
        check("backend down: page alive + readable error", "Engine offline" in txt and "reach the WhyBot engine" in txt and "Internal Server Error" not in txt and not errors,
              txt[txt.find("Something went wrong"):][:140].replace("\n", " "))
        subprocess.Popen(f"cd {os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')} && MOCK_MODE=1 setsid nohup python3 -m uvicorn main:app --port 8000 > /dev/null 2>&1 &", shell=True)
        time.sleep(3)
        await pg.click("button[type=submit]"); await pg.wait_for_selector(".answer", timeout=15000)
        check("recovers when backend returns", await pg.locator(".answer").count() >= 1)

        # 11. reduce-motion setting
        await pg.click("button[aria-label=Settings]"); await pg.wait_for_timeout(400)
        await pg.locator(".setting", has_text="Reduce motion").locator("button[role=switch]").click()
        await pg.wait_for_timeout(300)
        rm = await pg.evaluate("JSON.parse(localStorage.getItem('wb.settings')).reduceMotion")
        check("reduce motion toggles and persists", rm is True)

        check("no uncaught JS errors anywhere", not errors, "; ".join(errors[:3]))
        await b.close()
    print(f"\n{sum(ok for _, ok in results)}/{len(results)} UI scenarios passed")


asyncio.run(main())
