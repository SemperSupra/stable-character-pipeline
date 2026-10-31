// R15: Original-synthetic only, real headless browser mouse click through
// unchanged human UI. Native Node and locally installed Chrome, no npm packages.
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFileSync,mkdtempSync,readFileSync as read} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {spawn} from "node:child_process";

const wait=(ms)=>new Promise(r=>setTimeout(r,ms));
const caps={scope:"public-synthetic",release:"HELD_R009_NOT_RUN_NOT_ADMITTED",revision:"a".repeat(40)};
const good={human_behavior:"FAIL_ABSTRACT_LIMBS_ONLY",release:"HELD_R009_NOT_RUN_NOT_ADMITTED"};
const html=readFileSync(new URL("./ui.html",import.meta.url));
const js=readFileSync(new URL("./ui.js",import.meta.url));
let scenario="ok",posted=0,postValid=true;
const server=createServer(async(req,res)=>{
  const path=new URL(req.url,"http://127.0.0.1").pathname;
  let payload=null,type="application/json",status=200;
  if(path==="/"){payload=html;type="text/html"}
  else if(path==="/ui.js"){payload=js;type="text/javascript"}
  else if(path==="/v1/capabilities"){payload=scenario==="forged-cap"?{...caps,release:"PASS"}:caps}
  else if(path==="/v1/jobs"&&req.method==="POST"){
    posted++;
    let raw="";for await(const part of req)raw+=part;
    try{const d=JSON.parse(raw);postValid&&=d.schema==="scp.native-job-request.v1"&&d.job_id==="w7a-forward-24"&&d.revision===caps.revision&&d.source_class==="public-synthetic"}
    catch{postValid=false}
    if(scenario==="forged-result")payload={...good,human_behavior:"PASS_HUMAN"};
    else if(scenario==="http-fail"){status=409;payload={code:"SOURCE_REVISION_MISMATCH"}}
    else payload=good;
  }else if(path.startsWith("/v1/jobs/")&&path.endsWith("/media/OriginalFront")||path.endsWith("/media/OriginalOblique")){payload=Buffer.alloc(0);type="video/mp4"}
  else {status=404;payload={code:"NOT_FOUND"}}
  res.writeHead(status,{"Content-Type":type,"Cache-Control":"no-store"});
  res.end(Buffer.isBuffer(payload)?payload:JSON.stringify(payload));
});
await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
const origin="http://127.0.0.1:"+server.address().port;
const profile=mkdtempSync(join(tmpdir(),"scp-r15-chrome-"));
const bin=process.env.CHROME_BIN||"google-chrome";
const chrome=spawn(bin,["--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--disable-background-networking","--no-first-run","--no-default-browser-check","--remote-debugging-port=0","--user-data-dir="+profile,"about:blank"],{stdio:"ignore"});
let ws=null,id=0;const pending=new Map();
async function command(method,params={}){
  const my=++id;const response=new Promise((resolve,reject)=>{pending.set(my,{resolve,reject})});
  ws.send(JSON.stringify({id:my,method,params}));
  const x=await response;if(x.error)throw Error(method+": "+JSON.stringify(x.error));return x.result||{};
}
async function expression(expr){
  const x=await command("Runtime.evaluate",{expression:expr,returnByValue:true,awaitPromise:true});
  if(x.exceptionDetails)throw Error(JSON.stringify(x.exceptionDetails));
  return x.result.value;
}
async function ready(){
  for(let i=0;i<100;i++){
    if(await expression("document.readyState==='complete' && !!document.getElementById('submit')"))return;
    await wait(100);
  }
  throw Error("BROWSER_DOCUMENT_NOT_READY");
}
async function click(){
  const rect=await expression("(()=>{const r=document.getElementById('submit').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()");
  await command("Input.dispatchMouseEvent",{type:"mouseMoved",x:rect.x,y:rect.y});
  await command("Input.dispatchMouseEvent",{type:"mousePressed",x:rect.x,y:rect.y,button:"left",clickCount:1});
  await command("Input.dispatchMouseEvent",{type:"mouseReleased",x:rect.x,y:rect.y,button:"left",clickCount:1});
}
async function keyboardSubmit(){
  await expression("document.getElementById('submit').focus()");
  assert.equal(await expression("document.activeElement.id"),"submit");
  await command("Input.dispatchKeyEvent",{type:"keyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13,text:"\\r",unmodifiedText:"\\r"});
  await command("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
}
async function pageState(){
 return expression("({job:document.getElementById('job').textContent,hidden:document.getElementById('output').hidden,disabled:document.getElementById('submit').disabled,front:document.getElementById('front').getAttribute('src'),oblique:document.getElementById('oblique').getAttribute('src')})");
}
async function journey(mode){
  scenario=mode;posted=0;postValid=true;
  await command("Page.navigate",{url:origin+"/?scenario="+mode});
  await ready();
  assert.equal(await expression("document.getElementById('job').getAttribute('role')"),"status");
  assert.equal(await expression("document.getElementById('job').getAttribute('aria-live')"),"polite");
  assert.equal(await expression("document.getElementById('front').hasAttribute('controls')"),true);
  assert.equal(await expression("document.getElementById('oblique').hasAttribute('controls')"),true);
  if(mode==="keyboard")await keyboardSubmit();else await click();
  for(let i=0;i<100;i++){
    const state=await pageState();
    if(!state.disabled&&(state.job.startsWith("Original two-view")||state.job.startsWith("Run not accepted"))){
      assert.equal(postValid,true);
      if(mode==="ok"||mode==="keyboard"){
       assert.equal(posted,1);assert.equal(state.hidden,false);
       assert.equal(state.front,"/v1/jobs/w7a-forward-24/media/OriginalFront");
       assert.equal(state.oblique,"/v1/jobs/w7a-forward-24/media/OriginalOblique");
       assert.match(state.job,/FAIL.*UNKNOWN.*HELD/);
      }else{
       assert.equal(posted,mode==="forged-cap"?0:1);
       assert.equal(state.hidden,true);assert.match(state.job,/not accepted|unsuccessful/);
      }
      console.log("R15_ACTUAL_CHROME_MOUSE_CLICK_SCOPED_PASS",mode);
      return;
    }
    await wait(80);
  }
  throw Error("BROWSER_UI_RESULT_TIMEOUT_"+mode);
}
try{
  let endpoint;
  for(let i=0;i<100;i++){
    if(chrome.exitCode!==null)throw Error("CHROME_EXITED");
    try{const lines=read(join(profile,"DevToolsActivePort"),"utf8").trim().split("\n");const r=await fetch("http://127.0.0.1:"+lines[0]+"/json/list");const data=await r.json();endpoint=data.find(x=>x.type==="page")?.webSocketDebuggerUrl;if(endpoint)break}catch{}
    await wait(100);
  }
  if(!endpoint)throw Error("CHROME_CDP_UNAVAILABLE");
  ws=new WebSocket(endpoint);
  await new Promise((resolve,reject)=>{ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true})});
  ws.addEventListener("message",event=>{
    const msg=JSON.parse(event.data);
    if(!msg.id)return;
    const pendingMessage=pending.get(msg.id);
    if(pendingMessage){pending.delete(msg.id);pendingMessage.resolve(msg)}
  });
  await command("Page.enable");await command("Runtime.enable");
  for(const mode of ["ok","keyboard","forged-cap","forged-result","http-fail"])await journey(mode);
  console.log("R15_BROWSER_SOURCE_SAFE_UI_ONLY_NO_REAL_R009_OR_ACCESSIBILITY_ADMISSION");
}finally{
  ws?.close();chrome.kill("SIGTERM");
  await new Promise(resolve=>server.close(resolve));
}
