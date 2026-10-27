// W04 Stage 3: ACTUAL pinned Babylon MMD PMX scene materialization
// with @babylonjs/core NullEngine and upstream PmxLoader. No mocked model.
// Separate scene construction PASS from model animation/IK/physics QUALIFICATION.
import fs from "node:fs";
import crypto from "node:crypto";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine.js";
import { Scene } from "@babylonjs/core/scene.js";
import { PmxLoader } from "../../vendor/babylon-mmd/src/Loader/pmxLoader.pure.ts";
const sha=(b:Buffer)=>crypto.createHash("sha256").update(b).digest("hex");
async function caseRun(kind:string,file:string){
  const raw=fs.readFileSync(file);
  if(raw.length>2**20)throw Error("only bounded self-authored PMX admitted");
  const engine=new NullEngine({renderWidth:64,renderHeight:64});
  const scene=new Scene(engine);
  try {
    const loader=new PmxLoader();
    const state=await new Promise<any>((resolve,reject)=>{
      try {loader.loadFile(scene,Uint8Array.from(raw),"",resolve,undefined,true,(_req,error)=>reject(error))}
      catch(e){reject(e)}
    });
    const built=await loader.importMeshAsync(null,scene,state,"");
    const skinned=built.meshes.filter((m:any)=>m.skeleton!=null);
    const names=built.skeletons.flatMap((s:any)=>s.bones.map((b:any)=>b.name));
    const morphTargets=built.meshes.reduce((sum:number,m:any)=>sum+(m.morphTargetManager?.numTargets||0),0);
    const counts={case:kind,source_pmx_sha256:sha(raw),meshes:built.meshes.length,
      skin_instances:skinned.length,skeletons:built.skeletons.length,bone_names:names,
      morph_targets:morphTargets,
      status:"PASS_REAL_BABYLON_MMD_PMX_SCENE_CONSTRUCTION_ONLY",
      physics_simulation:"NOT_TESTED",animated_pose_evaluation:"NOT_TESTED",rendered_frame:"NOT_TESTED"};
    if(counts.skin_instances<1||counts.skeletons<1||
      (kind==="g10"&&counts.bone_names.length<4)||
      (kind==="g9"&&counts.morph_targets<2))
      throw Error("real Babylon scene failed to instantiate original skeleton/skin/morph: "+JSON.stringify(counts));
    return counts;
  }finally {scene.dispose();engine.dispose();}
}
async function main(){
  const [g10,g9,out]=process.argv.slice(2);
  if(!out)throw Error("usage G10_PMX G9_PMX output.json");
  const cases=[await caseRun("g10",g10),await caseRun("g9",g9)];
  const data={schema:"scp.mmd.w04-pmx-scene.v1",
    upstream_commit:"ccb750db2998ed1067017eaf67f3fc987cfba6f8",
    status:"PASS_REAL_BABYLON_PMX_MODEL_SCENE_ONLY",
    cases,not_tested:["actual runtime pose binding/IK solver",
      "physics collision/contact","camera pixel render or browser viewer"]};
  fs.mkdirSync(out.slice(0,out.lastIndexOf("/"))||".",{recursive:true});
  fs.writeFileSync(out,JSON.stringify(data,null,2)+"\n");
  console.log("W04_BABYLON_NULLENGINE_PMX_SCENE",JSON.stringify(data));
}
main().catch(e=>{console.error("W04_PMX_NULLENGINE_FIRST_FAILURE",e.stack||e);process.exitCode=1});
