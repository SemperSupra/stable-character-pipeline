/* Original standalone browser-side oracle, not supplied by donor. */
const fs=require("fs");
const path=require("path");
const {chromium}=require(path.join(process.argv[2],"node_modules","playwright"));
function oracle(p){
 const [x,y,z]=p;
 const sphere=Math.hypot(x,y,z)-1;
 const q=[Math.abs(x)-1.4,Math.abs(y)-0.25,Math.abs(z)-0.25];
 return Math.min(sphere,Math.hypot(...q.map(n=>Math.max(n,0)))+Math.min(Math.max(...q),0));
}
(async()=>{
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 let result=null;
 const errors=[];
 try {
  const page=await browser.newPage();
  page.on("console",m=>{
    const text=m.text();
    if(text.startsWith("WASM_RESULT=")){
       try{result=JSON.parse(text.substring("WASM_RESULT=".length))}
       catch(e){errors.push("BAD_RESULT_JSON")}
    }
  });
  page.on("pageerror",e=>errors.push("PAGE_ERROR:"+e.message));
  await page.goto("http://127.0.0.1:8787/",{waitUntil:"load"});
  await page.waitForFunction(()=>window.__geometryDone || window.__geometryError,{timeout:30000});
  const state=await page.evaluate(()=>({done:window.__geometryDone||false,
     error:window.__geometryError||null,status:document.getElementById("status")?.textContent,
     wasmAvailable:typeof WebAssembly==="object"}));
  if(state.error)errors.push(state.error);
  if(!state.done||!state.wasmAvailable)errors.push("WASM_NOT_EXECUTED");
  if(result?.donor!=="sdfx"||result?.invalid_rejected!==true)errors.push("MISMATCH_INPUT_CONTRACT");
  if(result?.samples?.length!==12)errors.push("SAMPLE_COUNT");
  let maxError=0;
  for(const [i,s] of (result?.samples||[]).entries()){
    if(!Array.isArray(s.xyz)||s.xyz.length!==3) {errors.push("BAD_POINT_"+i);continue}
    const delta=Math.abs(s.distance-oracle(s.xyz));
    if(!Number.isFinite(delta)){errors.push("NONFINITE_"+i);continue}
    maxError=Math.max(maxError,delta);
    if(delta>1e-11) errors.push("NUMERIC_"+i);
  }
  const receipt={schema:"browser-wasm-sdf/v1",status:errors.length?"FAIL":"PASS",
    browser:"Chromium via pinned Playwright",browserVersion:browser.version(),
    userAgent:await page.evaluate(()=>navigator.userAgent),
    runtimeState:state,cases:result?.samples?.length||0,maxAbsError:maxError,
    errors};
  fs.writeFileSync(process.argv[3],JSON.stringify(receipt,null,2)+"\n");
  console.log(JSON.stringify(receipt));
  if(errors.length)process.exitCode=1;
 } finally {await browser.close()}
})().catch(e=>{console.error("BROWSER_ORACLE_FAILURE",e);process.exitCode=2});
