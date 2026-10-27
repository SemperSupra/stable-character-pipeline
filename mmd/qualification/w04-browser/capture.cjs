#!/usr/bin/env node
// Actual headless Chromium WebGL screenshot, not Blender restyle or synthetic
// 2D drawn image; frame-by-frame real Babylon MmdRuntime scene/render evidence.
// The separate Pillow/ffprobe gate must reject frozen/black frames.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {chromium}=require('playwright');
const out=process.argv[2]||'w04-browser-output';
fs.mkdirSync(out,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
  const browser=await chromium.launch({headless:true,
    executablePath:process.env.SCP_CHROME_BIN||undefined,
    args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader',
      '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--disable-dev-shm-usage']
  });
  let page;
  try{
    page=await browser.newPage({viewport:{width:720,height:960},deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',e=>errors.push('page:'+String(e)));
    page.on('console',msg=>{if(msg.type()==='error')errors.push('console:'+msg.text())});
    const response=await page.goto('http://127.0.0.1:8877/index.html',{waitUntil:'load',timeout:60000});
    if(!response?.ok())throw Error('the local original source viewer did not load');
    await page.waitForFunction(()=>Boolean(window.SCP_READY||window.SCP_ERROR),null,{timeout:75000});
    const status=await page.evaluate(()=>({ready:window.SCP_READY,error:window.SCP_ERROR}));
    if(status.error||status.ready!=='ACTUAL_WEBGL_BABYLON_MMD_NATIVE_RUNTIME_INITIALIZED')
      throw Error('actual Babylon WebGL initialization did not pass: '+JSON.stringify({...status,errors}));
    const frames=[];
    for(let frame=0;frame<=30;frame++){
      const receipt=await page.evaluate(f=>window.SCP_CAPTURE(f),frame);
      if(!receipt.webgl || !receipt.has_canvas || receipt.rendered_original_meshes<1 ||
          receipt.original_bones.length!==4||receipt.marker_count!==4)
        throw Error('not actual native BabylonJS WebGL/PMX animated mesh at '+frame);
      const file=path.join(out,'babylon_actual_frame_'+String(frame).padStart(4,'0')+'.png');
      const picture=await page.locator('#stage').screenshot({path:file,type:'png'});
      if(picture.length<5000)throw Error('suspiciously tiny browser screenshot '+frame);
      frames.push({...receipt,png_sha256:sha(picture),size_bytes:picture.length});
      console.log('BROWSER_NATIVE_ACTUAL_FRAME',JSON.stringify({frame,png_sha256:sha(picture),
        ankle:receipt.original_bones[2],ik_goal:receipt.original_bones[3]}));
    }
    const controller=frames.map(r=>r.original_bones.find(b=>b.name==='足ＩＫ'));
    if(Math.hypot(controller[0].x-controller[30].x,
       controller[0].y-controller[30].y,
       controller[0].z-controller[30].z)<.35)
      throw Error('real browser IK controller remained frozen');
    if(errors.length)throw Error('browser runtime produced unexpected script errors: '+errors.join('; '));
    const report={
      schema:'scp.mmd.w04-real-browser-webgl.v1',
      status:'PASS_GENUINE_BABYLON_WEBGL_NATIVE_PMXSOURCE_31_FRAME_VISUAL_CAPTURE',
      runtime:'actual Chromium hardware-independent software WebGL2/ANGLE SwiftShader',
      source_upstream_commit:'ccb750db2998ed1067017eaf67f3fc987cfba6f8',
      input_assets:'only exact original self-authored G10 PMX/VMD fetched from local test host',
      frames,limits:['gold joint markers and yellow connecting lines are diagnostic overlay geometry',
        'not verified third-party character or skin-material parity',
        'not native MikuMikuDance application CCD equality','not physical contact/ground plane physics',
        'not proof that all real MMD assets are licensed'],
      browser_console_errors:errors
    };
    fs.writeFileSync(path.join(out,'webgl_browser_captures.json'),JSON.stringify(report,null,2)+'\n');
    console.log('W04_REAL_BABYLON_BROWSER_SUMMARY',JSON.stringify({status:report.status,frames:frames.length,
      first_png_sha256:frames[0].png_sha256,last_png_sha256:frames[30].png_sha256}));
  } finally {await browser.close()}
}
main().catch(e=>{console.error('W04_BROWSER_CAPTURE_FIRST_FAILURE',String(e?.stack||e));process.exitCode=1});
