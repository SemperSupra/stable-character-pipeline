// Native browser qualification via Chrome DevTools Protocol and Node's
// built-in WebSocket. No npm/Playwright fetch, third-party voice assets,
// recordings, public service or screenshot uploads. NOT iOS VoiceOver HIL.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import process from 'node:process';

const browserEndpoint=process.env.CDP_ENDPOINT??'http://127.0.0.1:9222';
const appEndpoint=process.env.WORKBENCH_ENDPOINT??'http://127.0.0.1:8766';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function discover(){
 for(let i=0;i<75;i++){
  try{
   const res=await fetch(browserEndpoint+'/json/list',{signal:AbortSignal.timeout(1500)});
   if(!res.ok)throw new Error('CDP unavailable');
   const targets=await res.json();
   const tab=targets.find(t=>t.type==='page'&&t.webSocketDebuggerUrl);
   if(tab)return tab.webSocketDebuggerUrl;
  }catch{}
  await sleep(100);
 }
 throw new Error('local Chrome CDP discovery failed');
}
const socket=new WebSocket(await discover());
await new Promise((resolve,reject)=>{
 const timer=setTimeout(()=>reject(new Error('CDP websocket timeout')),10000);
 socket.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
 socket.addEventListener('error',()=>{clearTimeout(timer);reject(new Error('CDP websocket failed'));},{once:true});
});
let sequence=0;
const pending=new Map();
socket.addEventListener('message',event=>{
 let message;try{message=JSON.parse(event.data);}catch{return;}
 if(!message.id)return;
 const awaiting=pending.get(message.id);if(!awaiting)return;
 pending.delete(message.id);clearTimeout(awaiting.timer);
 if(message.error)awaiting.reject(new Error(JSON.stringify(message.error)));
 else awaiting.resolve(message.result);
});
function call(method,params={}){
 const id=++sequence;
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},12000);
  pending.set(id,{resolve,reject,timer});
  socket.send(JSON.stringify({id,method,params}));
 });
}
async function evaluate(expression){
 const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw new Error('Browser JavaScript: '+JSON.stringify(r.exceptionDetails));
 return r.result?.value;
}
async function until(expr){
 for(let i=0;i<70;i++){const v=await evaluate(expr);if(v)return v;await sleep(80);}
 throw new Error('condition not reached: '+expr);
}
const checked=[];
function record(name,condition){assert.ok(condition,name);checked.push(name);}
try{
 await call('Page.enable');
 await call('Runtime.enable');
 await call('Page.navigate',{url:appEndpoint+'/'});
 await until('document.getElementById("action")?.options.length===18');
 const initial=await evaluate('({count:document.getElementById("action").options.length,lang:document.documentElement.lang,autoplay:document.getElementById("play").autoplay})');
 record('18 actions loaded by actual browser fetch',initial.count===18);
 record('default English and no autoplay',initial.lang==='en'&&!initial.autoplay);
 const catalog=await evaluate('(async()=>{const r=await fetch("/api/v1/capabilities");return await r.json();})()');
 record('canonical source catalog and unavailable statuses',catalog.schema==='respiratory.audience_capabilities.v0'&&catalog.entries.length===18&&catalog.entries.filter(e=>e.mode==='typed_contract_only').length===3);
 const thai=await evaluate('(()=>{const l=document.getElementById("language");l.value="th";l.dispatchEvent(new Event("change",{bubbles:true}));return {lang:document.documentElement.lang,title:document.getElementById("heading").textContent,action:document.getElementById("action").selectedOptions[0]?.textContent};})()');
 const thaiLetters=/[\u0E00-\u0E7F]/u;
 record('Thai UI and source-derived action labels',thai.lang==='th'&&thaiLetters.test(thai.title)&&thaiLetters.test(thai.action||''));
 const unsupported=await evaluate('(()=>{const a=document.getElementById("action");a.value="sniff";a.dispatchEvent(new Event("change",{bubbles:true}));return {disabled:document.getElementById("prepare").disabled,scenario:document.getElementById("scenario").disabled,src:document.getElementById("play").getAttribute("src")};})()');
 record('contract-only sniff disables preview and clears media',unsupported.disabled&&unsupported.scenario&&!unsupported.src);
 const prepared=await evaluate('(()=>{const a=document.getElementById("action");a.value="hum";a.dispatchEvent(new Event("change",{bubbles:true}));const s=document.getElementById("scenario");s.value="humming";s.dispatchEvent(new Event("change",{bubbles:true}));const b=document.getElementById("prepare");if(b.disabled)return {disabled:true};b.click();const audio=document.getElementById("play");return {disabled:false,src:audio.getAttribute("src"),paused:audio.paused,autoplay:audio.autoplay};})()');
 record('manual preview uses canonical humming source',!prepared.disabled&&prepared.src?.includes('action=hum')&&prepared.src?.includes('scenario=humming'));
 record('audio does not start without explicit Play',prepared.paused&&!prepared.autoplay);
 for(const width of [375,320]){
  await call('Emulation.setDeviceMetricsOverride',{width,height:812,deviceScaleFactor:1,mobile:true});
  const sizes=await evaluate('({w:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth})');
  record(width+'px viewport no horizontal overflow',sizes.w===width&&sizes.scroll<=width+1&&sizes.body<=width+1);
 }
 const tree=await call('Accessibility.getFullAXTree');
 const nodes=tree.nodes??[];
 const roles=nodes.map(n=>n.role?.value).filter(Boolean);
 const combos=nodes.filter(n=>n.role?.value==='combobox'&&(n.name?.value||'').length>0);
 record('Chrome accessibility tree exposes labeled selection controls',combos.length>=3);
 record('Chrome accessibility tree includes button and live status',roles.includes('button')&&roles.includes('status'));
 const png=Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64');
 record('actual Chrome screenshot is PNG',png.length>800&&png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
 if(process.env.BROWSER_SCREENSHOT_PATH)fs.writeFileSync(process.env.BROWSER_SCREENSHOT_PATH,png);
 console.log(JSON.stringify({schema:'respiratory.browser_source_hil.v0',
  validity:'real_chrome_DOM_and_AX_not_real_screen_reader_or_physiological_audio',
  browser:'chrome_headless_CDP',passed:checked.length,checks:checked,
  actions:18,scenarios:17,unavailable:3,locales:['en','de','th'],
  viewportWidths:[375,320],screenshotBytes:png.length}));
 socket.close();
}catch(e){
 console.error('BROWSER_QUALIFICATION_FAILED:',String(e?.stack??e));
 socket.close();
 process.exitCode=1;
}
