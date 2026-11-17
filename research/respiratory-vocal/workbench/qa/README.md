# Actual headless Chrome DOM and accessibility-tree probe — free public research

Source-only third batch stacked on [draft source-gated localhost workbench #634](https://github.com/SemperSupra/stable-character-pipeline/pull/634), with canonical capabilities #628, all 17 original source WAV fixtures and historic source contract transitively. **No original browser JS, API, generator, protected private Physical Vocal source, or original 21 historic WAVs are modified**.

The independent `workbench/qa/browser-cdp.mjs` script uses **only Node built-ins** (`fetch`, `WebSocket`, `assert`, `fs`) and a temporarily launched stock headless Google Chrome via Chrome DevTools Protocol; no npm, Playwright download, microphone, private voice, screenshot upload, internet deployment or extra secret. The dedicated 5-minute read-only public GHA starts the original Go localhost-only workbench, refuses `0.0.0.0` binding and starts headless Chrome on a loopback DevTools port in the disposable runner. All browser-side access uses localhost.

Actual browser checks (not mocked handlers): initial Go catalog fetched and **18 action options**, three contract-only unavailable modes; switch language to Thai and ensure actual translated heading/action labels; choose sniff and verify Prepare disabled and no active audio source; switch to hum/humming and explicitly Prepare, verify original source-bound scenario URL but **no autoplay**; inspect real rendered document at **375px and 320px** for horizontal overflow; request Chrome's **real accessibility tree** and verify labeled combo boxes, button and live status roles; capture an original ephemeral PNG screenshot (no upload). Emit bounded JSON receipt with passed checks, and its SHA in the workflow log. Source test is **semantic UI/AX smoke only**, not user accessibility certification.

**Important limits:** No iPhone/Android device, Safari, hardware audio, real screen reader (VoiceOver/TalkBack/NVDA), switch device, human listener, independent German/Thai native translation review or physical human vocal tract acoustic acceptance. A headless browser's AX tree indicates exposed roles and names, not whether people with disabilities can use it. No more private Actions under the earlier unbilled 60-minute cap; all original voice/identity assets remain sovereign. Keep draft/unmerged, no deployment/release.

Standalone on an environment with Node built-in WebSocket and Chrome DevTools:
```sh
cd research/respiratory-vocal
go run ./cmd/respiratory-workbench
# In another local shell, launch local Chrome with --remote-debugging-port=9222
node workbench/qa/browser-cdp.mjs
```
This separate branch is a read-only qualification of the existing page; integration fixes, if required, need an independently reviewed child PR with the first failed job retained in DLE #582.
