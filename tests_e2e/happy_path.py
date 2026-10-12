"""Happy-path browser flow across every page. Needs ./start.sh running (MOCK_MODE=1 is fine)."""
import os
import asyncio
from playwright.async_api import async_playwright
B = "http://localhost:3000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT, exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1600,"height":1000})
        errs=[]; pg.on("pageerror", lambda e: errs.append(("pageerror",str(e)[:200])))
        pg.on("console", lambda m: m.type=="error" and errs.append(("console",m.text[:200])))
        bad=[]; pg.on("response", lambda r: r.status>=400 and bad.append((r.status,r.url)))
        await pg.goto(B+"/", wait_until="networkidle"); await pg.wait_for_timeout(1200)
        await pg.screenshot(path=os.path.join(OUT, "n1_home_empty.png"))
        # knowledge: upload file + starter
        await pg.click("text=Knowledge"); await pg.wait_for_url(B+"/knowledge"); await pg.wait_for_timeout(800)
        await pg.set_input_files("input[type=file]", files=[{"name":"team-notes.md","mimeType":"text/markdown","buffer":b"# Mobile team\nRavi Kumar owns the iOS release. The android-app depends on auth-service.\n\nRelease freeze starts Friday."}])
        await pg.wait_for_timeout(1200)
        await pg.click("text=No docs handy? Load starter data"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=os.path.join(OUT, "n2_knowledge.png"), full_page=True)
        # profile
        await pg.click("button[aria-label=Profile]"); await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "n3_profile_menu.png"))
        await pg.click("text=Edit profile"); await pg.wait_for_timeout(500)
        await pg.fill("input[placeholder='Your name']","Vik Rao"); await pg.fill("input[placeholder='Engineer, PM, Founder…']","Engineering Manager")
        await pg.fill("input[placeholder='Platform, Sales…']","Payments")
        await pg.screenshot(path=os.path.join(OUT, "n4_profile_modal.png"))
        await pg.click("text=Save profile"); await pg.wait_for_timeout(1000)
        # settings
        await pg.click("button[aria-label=Settings]"); await pg.wait_for_timeout(700)
        await pg.click("span[title=teal]"); await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "n5_settings.png"))
        await pg.click("button[aria-label=Close]"); await pg.wait_for_timeout(500)
        # ask compare
        await pg.click("text=Ask the Brain"); await pg.wait_for_url(B+"/"); await pg.wait_for_timeout(600)
        await pg.click(".chip >> nth=0"); await pg.wait_for_selector(".answer.win", timeout=20000); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=os.path.join(OUT, "n6_ask.png"))
        # impact
        await pg.click("text=Blast Radius"); await pg.wait_for_url(B+"/impact"); await pg.wait_for_timeout(600)
        await pg.click(".chip >> nth=0"); await pg.wait_for_selector("text=Impact brief", timeout=20000); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=os.path.join(OUT, "n7_impact.png"))
        await pg.screenshot(path=os.path.join(OUT, "n7b_impact_full.png"), full_page=True)
        for name, path in [("personas","/personas"),("graph","/graph"),("integrations","/integrations"),("about","/about")]:
            await pg.click(f"a[href='{path}']"); await pg.wait_for_url(B+path); await pg.wait_for_timeout(2200)
            await pg.screenshot(path=os.path.join(OUT, f"n8_{name}.png"))
        # integrations live request
        await pg.click(f"a[href='/integrations']"); await pg.wait_for_timeout(800)
        await pg.click("text=Send request"); await pg.wait_for_selector("pre.codeblock >> nth=0"); await pg.wait_for_timeout(800)
        out = await pg.inner_text("pre.codeblock >> nth=0"); print("integration output starts:", out[:80].replace("\n"," "))
        # API docs via proxy
        r = await pg.goto(B+"/api/docs"); await pg.wait_for_timeout(1500)
        print("api docs title:", await pg.title())
        # mobile
        m = await b.new_page(viewport={"width":390,"height":844}); await m.goto(B+"/impact", wait_until="networkidle"); await m.wait_for_timeout(1000)
        await m.screenshot(path=os.path.join(OUT, "n9_mobile.png"))
        print("ERRORS:", errs); print("BAD RESPONSES:", bad)
        await b.close()
asyncio.run(main())
