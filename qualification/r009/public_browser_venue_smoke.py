"""PUBLIC-SAFE Playwright venue smoke, NOT a test of the private R009 QA app.

Exercises Chromium, responsive viewport, OS-following theme, keyboard,
pointer/canvas interaction, exported JSON cold reimport with wrong-SHA rejection,\nAX snapshot, overflow falsifier, privacy request capture, and screenshots.
Contains synthetic DOM only. No protected R009 code, images, video, or tokens.
"""
import json
import os
import platform
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = r"""
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Public synthetic browser test surface</title>
<style>
:root {font:16px system-ui,sans-serif; --background:#ffffff; --foreground:#17212b}
:root[data-theme=dark] {--background:#151b22;--foreground:#f3f5fa}
body{background:var(--background);color:var(--foreground);margin:0;padding:16px}
main{max-width:900px;margin:0 auto}button{margin:4px;padding:8px 12px}
canvas{display:block;width:100%;height:auto;touch-action:none;background:#abc7e1}
@media(max-width:600px){main{max-width:100%}}
</style>
<main><h1>Browser venue check — synthetic only</h1>
<nav aria-label="Appearance" role="group">
<button type="button" id="system">System</button>
<button type="button" id="light">Light</button>
<button type="button" id="dark">Dark</button>
</nav>
<p id="status" role="status" aria-live="polite">System</p>
<label for="comment">Correction</label><input id="comment">
<canvas id="canvas" width="400" height="160" aria-label="Synthetic annotation canvas"></canvas>
<button id="export" type="button">Export synthetic review</button>
<label for="import">Import synthetic review</label><input id="import" type="file" accept="application/json">
<p id="import-status" role="status"></p>
</main>
<script>
let strokes=0;
let preference='system';
const media=matchMedia('(prefers-color-scheme: dark)');
function setTheme(m){preference=m;document.documentElement.dataset.theme=m==='system'?(media.matches?'dark':'light'):m;document.getElementById('status').textContent=m}
media.addEventListener('change',()=>{if(preference==='system')setTheme('system')});
for (const m of ['system','light','dark'])document.getElementById(m).onclick=()=>setTheme(m);
setTheme('system');
const c=document.getElementById('canvas'),ctx=c.getContext('2d');
ctx.fillStyle='#347ca5';ctx.fillRect(80,35,80,65);
c.addEventListener('pointerdown',ev=>{strokes++;ctx.fillStyle='#d02b55';ctx.fillRect(190,60,30,30)});
window.syntheticStrokeCount=()=>strokes;
const receipt={schema:'synthetic-review.v1',source_sha256:'a'.repeat(64),accepted:false,strokes:[{x:0.5,y:0.5}]};
document.getElementById('export').onclick=()=>{const blob=new Blob([JSON.stringify(receipt)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='synthetic-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
document.getElementById('import').onchange=async e=>{try{const file=e.target.files[0];const raw=JSON.parse(await file.text());if(raw.schema!==receipt.schema||raw.source_sha256!==receipt.source_sha256||raw.accepted!==false||!Array.isArray(raw.strokes))throw Error('SOURCE_OR_SCHEMA_MISMATCH');document.getElementById('import-status').textContent='Imported '+raw.strokes.length+' synthetic strokes'}catch(e){document.getElementById('import-status').textContent='REJECTED '+e.message}};
</script></html>
"""

def main():
    dest = Path(os.environ.get("QA_BROWSER_OUT", "synthetic-browser-evidence"))
    dest.mkdir(parents=True, exist_ok=True)
    results = {"scope":"PUBLIC_SYNTHETIC_VENUE_ONLY_NOT_PRIVATE_QA", "checks":[], "system":platform.platform(),
               "git_sha":os.environ.get("GITHUB_SHA"), "runner":os.environ.get("RUNNER_OS")}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        results["browser_version"]=browser.version
        for label, viewport in [("desktop",{"width":1280,"height":800}),("mobile",{"width":390,"height":844})]:
            page=browser.new_page(viewport=viewport)
            requests=[]
            errors=[]
            page.on("request",lambda req:requests.append(req.url))
            page.on("pageerror",lambda err:errors.append(str(err)))
            page.emulate_media(color_scheme="dark")
            page.set_content(PAGE,wait_until="load")
            assert page.get_by_role("heading",name="Browser venue check — synthetic only").count()==1
            assert page.locator("#status").inner_text()=="system"
            assert page.locator("html").get_attribute("data-theme")=="dark"
            page.emulate_media(color_scheme="light")
            assert page.locator("html").get_attribute("data-theme")=="light"
            page.get_by_role("button",name="Dark").click()
            page.emulate_media(color_scheme="light")
            assert page.locator("html").get_attribute("data-theme")=="dark"
            page.get_by_role("button",name="System").click()
            assert page.locator("html").get_attribute("data-theme")=="light"
            page.get_by_role("button",name="Dark").click()
            assert page.locator("html").get_attribute("data-theme")=="dark"
            page.get_by_role("button",name="Light").click()
            assert page.locator("html").get_attribute("data-theme")=="light"
            page.get_by_label("Correction").fill("Check foot contact")
            assert page.get_by_label("Correction").input_value()=="Check foot contact"
            box=page.locator("canvas").bounding_box()
            assert box is not None
            page.mouse.click(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
            assert page.evaluate("syntheticStrokeCount()")==1
            with page.expect_download() as download_info:
                page.get_by_role("button",name="Export synthetic review").click()
            download=download_info.value
            assert download.suggested_filename=="synthetic-review.json"
            exported=Path(download.path()).read_bytes()
            review=json.loads(exported)
            assert review["accepted"] is False and len(review["strokes"])==1
            page.set_content(PAGE,wait_until="load")  # cold DOM restart, no authoritative state retained
            page.locator("#import").set_input_files({"name":"synthetic-review.json","mimeType":"application/json","buffer":exported})
            assert page.locator("#import-status").inner_text()=="Imported 1 synthetic strokes"
            bad=dict(review,source_sha256="b"*64)
            page.locator("#import").set_input_files({"name":"bad.json","mimeType":"application/json","buffer":json.dumps(bad).encode()})
            assert page.locator("#import-status").inner_text().startswith("REJECTED")
            ax=page.locator("main").aria_snapshot()
            assert "Export synthetic review" in ax and "Import synthetic review" in ax
            (dest/f"public-{label}-ax.txt").write_text(ax,encoding="utf-8")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("document.body.style.minWidth = '2000px'")
            assert page.evaluate("document.documentElement.scrollWidth > innerWidth"), "Overflow falsifier failed to detect deliberate defect"
            page.evaluate("document.body.style.minWidth = ''")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, f"Unexpected page errors: {errors}"
            assert not requests, f"Synthetic fixture emitted network requests: {requests}"
            page.screenshot(path=str(dest/f"public-{label}-synthetic.png"),full_page=True)
            results["checks"].append({"viewport":label,"checks_passed":12,"page_errors":errors,"network_requests":requests})
            page.close()
        browser.close()
    (dest/"receipt.json").write_text(json.dumps(results,sort_keys=True,indent=2),encoding="utf-8")
    print(json.dumps(results,sort_keys=True))
if __name__=="__main__":main()
