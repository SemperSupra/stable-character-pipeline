// W04 Stage 2 — REAL BabylonJS NullEngine, actual Babylon MMD VmdLoader.
// No mocked animation classes, simulated pose evaluation, PMX geometry,
// browser renderer or physics claim. Original copyrighted identities excluded.
import fs from "node:fs";
import crypto from "node:crypto";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine.js";
import { Scene } from "@babylonjs/core/scene.js";
import { VmdLoader } from "../../vendor/babylon-mmd/src/Loader/vmdLoader.ts";

function digest(b:Buffer){return crypto.createHash("sha256").update(b).digest("hex");}
function arrayBuffer(b:Buffer){return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}
function summary(track:any){
  return {
    name:String(track.name),
    type:String(track.trackType),
    frames:Array.from(track.frameNumbers as Uint32Array),
    keyframes:(track.frameNumbers as Uint32Array).length,
    weights:track.weights ? Array.from(track.weights as Float32Array) : undefined,
    position_components:track.positions ? (track.positions as Float32Array).length : undefined,
    rotation_components:track.rotations ? (track.rotations as Float32Array).length : undefined
  };
}
async function runOne(scene:Scene,kind:"g9"|"g10",motionFile:string){
  const raw=fs.readFileSync(motionFile);
  const loader=new VmdLoader(scene);
  const animation=await loader.loadFromBufferAsync("SCP-original-"+kind,arrayBuffer(raw));
  if(!animation.validate())throw Error("real upstream MmdAnimation invalid after VmdLoader");
  const bones=animation.boneTracks.map(summary);
  const movable=animation.movableBoneTracks.map(summary);
  const morphs=animation.morphTracks.map(summary);
  const allFrames=[...bones,...movable,...morphs].flatMap(t=>t.frames);
  const relevant=kind==="g9" ? morphs : [...bones,...movable];
  if(kind==="g9" && (morphs.length<2 || !morphs.every(t=>t.keyframes>=3) ||
      !morphs.some(t=>(t.weights||[]).some((w,i,arr)=>i>0&&w!==arr[0]))))
    throw Error("real G9 2-morph native animation tracks were not instantiated or changed");
  if(kind==="g10" && (!relevant.length || !allFrames.includes(0) || !allFrames.includes(30)))
    throw Error("real G10 native IK-goal movement tracks missing time origin/end");
  return {kind,
    source_vmd_sha256:digest(raw),
    loader:"actual pinned babylon-mmd VmdLoader.loadFromBufferAsync under BabylonJS NullEngine",
    passed_upstream_validation:true,
    bone_tracks:bones,movable_bone_tracks:movable,morph_tracks:morphs,
    max_frame:Math.max(...allFrames),
    status:"PASS_REAL_VMD_LOADER_ANIMATION_OBJECT_ONLY",
    pmx_model_bound:false,actual_pose_deformation:"NOT_TESTED",
    native_mmd_ccd_and_physics:"NOT_TESTED",pixel_playback:"NOT_TESTED"};
}
async function main(){
  const [g10path,g9path,out]=process.argv.slice(2);
  if(!out)throw Error("provide original G10 VMD, G9 VMD, output");
  const engine=new NullEngine({renderWidth:64,renderHeight:64});
  const scene=new Scene(engine);
  try {
    const cases=[await runOne(scene,"g10",g10path),await runOne(scene,"g9",g9path)];
    const report={schema:"scp.mmd.w04-nullengine-vmdloader.v1",status:"PASS_GENUINE_NULLENGINE_AND_BABYLON_MMD_VMD_ANIMATION_OBJECTS",
      upstream_commit:"ccb750db2998ed1067017eaf67f3fc987cfba6f8",
      cases,limitations:["no PMX scene mesh instantiated","no skinned pose or morph evaluated by runtime",
        "no actual WebGL/WebGPU renderer output","source motion tracks, not full physical motion parity"]};
    fs.mkdirSync(requirePath(out),{recursive:true});
    fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
    console.log("W04_BABYLON_NULLENGINE_VMDLOADER",JSON.stringify(report));
  } finally {scene.dispose();engine.dispose();}
}
function requirePath(file:string){return file.includes("/")?file.substring(0,file.lastIndexOf("/")):".";}
main().catch(e=>{console.error("W04_NULLENGINE_FIRST_FAILURE",e.stack||e);process.exitCode=1});
