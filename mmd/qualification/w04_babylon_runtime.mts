// W04 Stage 4 — source-native ACTUAL Babylon MMD runtime on real PMX+VMD.
// Reuses upstream MmdRuntime, true solver, and Blender-independent PMX/VMD
// source. Does NOT assert pixel/physics/browser fidelity without those tests.
import fs from "node:fs";
import crypto from "node:crypto";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine.js";
import { Scene } from "@babylonjs/core/scene.js";
import { Vector3 } from "@babylonjs/core/Maths/math.vector.js";
import { PmxLoader } from "../../vendor/babylon-mmd/src/Loader/pmxLoader.pure.ts";
import { VmdLoader } from "../../vendor/babylon-mmd/src/Loader/vmdLoader.ts";
import { MmdRuntime } from "../../vendor/babylon-mmd/src/Runtime/mmdRuntime.ts";
import "../../vendor/babylon-mmd/src/Runtime/Animation/mmdRuntimeModelAnimation.ts";

function hex(b:Buffer){return crypto.createHash("sha256").update(b).digest("hex");}
function arr(b:Buffer){return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}
async function execute(caseName:string,pmxPath:string,vmdPath:string,all31=false){
  const pmx=fs.readFileSync(pmxPath),vmd=fs.readFileSync(vmdPath);
  if(pmx.length>1<<20||vmd.length>1<<20)throw Error("bounded self-authored G9/G10 only");
  const engine=new NullEngine({renderWidth:64,renderHeight:64});
  const scene=new Scene(engine);
  try {
    const loader=new PmxLoader();
    const state=await new Promise<any>((resolve,reject)=>{
      try{loader.loadFile(scene,Uint8Array.from(pmx),"",resolve,undefined,true,(_r,e)=>reject(e))}
      catch(e){reject(e)}
    });
    const built=await loader.importMeshAsync(null,scene,state,"");
    const mesh=built.meshes[0];
    const animation=await new VmdLoader(scene).loadFromBufferAsync("original-source-motion",arr(vmd));
    if(!animation.validate())throw Error("upstream Vmd animation invalid");
    const runtime=new MmdRuntime(scene,null);
    const model=runtime.createMmdModel(mesh,{buildPhysics:false,trimMetadata:false});
    const handle=model.createRuntimeAnimation(animation);
    model.setRuntimeAnimation(handle);
    const snapshots=[];
    for(const frame of (all31 ? Array.from({length:31},(_,i)=>i) : [0,15,30])){
      model.beforePhysics(frame);
      model.afterPhysics();
      const bones=model.runtimeBones.map(b=>{
        const translation=b.getWorldTranslationToRef(new Vector3());
        return {name:b.name,world_xyz:[translation.x,translation.y,translation.z]};
      });
      const morphWeights=caseName==="g9"?{
          "まばたき":model.morph.getMorphWeight("まばたき"),
          "笑い":model.morph.getMorphWeight("笑い")
      }:{};
      if(!bones.length||!bones.every(b=>b.world_xyz.every(Number.isFinite)))
        throw Error("invalid actual runtime evaluated world-space bone poses");
      if(!Object.values(morphWeights).every(Number.isFinite))
        throw Error("invalid actual evaluated morph weights");
      snapshots.push({frame,bones,morphWeights});
    }
    if(caseName==="g10"){
      const bone=(frame:number)=>snapshots.find(s=>s.frame===frame)?.bones.find(b=>b.name==="足ＩＫ")?.world_xyz;
      const a=bone(0),b=bone(30);
      if(!a||!b||Math.hypot(...a.map((v,i)=>v-b[i]))<.15)
        throw Error("actual MMD runtime IK source-goal animation was stationary");
    }else{
      const keys=snapshots.filter(x=>[0,15,30].includes(x.frame));
      const blink=keys.map(x=>x.morphWeights["まばたき"]);
      const smile=keys.map(x=>x.morphWeights["笑い"]);
      if(!(Math.abs(blink[0])<.02&&Math.abs(blink[1]-1)<.02&&Math.abs(blink[2])<.02 &&
        Math.abs(smile[0])<.02&&Math.abs(smile[1]-.35)<.02&&Math.abs(smile[2]-1)<.02))
        throw Error("actual MmdRuntime G9 morphs disagree with original keyed 0/15/30 source motion");
    }
    return {case:caseName,model_sha256:hex(pmx),motion_sha256:hex(vmd),
      status:"PASS_NATIVE_BABYLON_MMD_RUNTIME_EVALUATED_SYNTHETIC_POSE_OR_MORPH",
      actual_runtime_model:true,actual_bound_animation:true,snapshots,
      native_MikuMikuDance_solver_parity:"NOT_TESTED",
      actual_browser_pixel_rendering:"NOT_TESTED",contact_physics:"NOT_TESTED"};
  }finally{scene.dispose();engine.dispose();}
}
async function main(){
  const [g10m,g10v,g9m,g9v,out,mode]=process.argv.slice(2);
  const all31=mode==="--all31";
  if(mode!==undefined && !all31)throw Error("invalid optional mode: "+mode);
  if(!out)throw Error("expected real G10 PMX/VMD G9 PMX/VMD output");
  const cases=[await execute("g10",g10m,g10v,all31),await execute("g9",g9m,g9v,all31)];
  const result={schema:"scp.mmd.w04-real-runtime.v1",
    upstream_commit:"ccb750db2998ed1067017eaf67f3fc987cfba6f8",
    status:all31 ? "PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_31_FRAMES_ONLY" : "PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_SELECTED_FRAMES_ONLY",
    cases,not_tested:["all-bone absolute pose parity with independently evaluated Blender source",
    "native MikuMikuDance IK engine solver parity","collision/foot contact","WebGL rendered video"]};
  fs.mkdirSync(out.substring(0,out.lastIndexOf("/"))||".",{recursive:true});
  fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
  console.log("W04_ACTUAL_BABYLON_RUNTIME",JSON.stringify(result));
}
main().catch(e=>{console.error("W04_RUNTIME_FIRST_FAILURE",e.stack||e);process.exitCode=1});
