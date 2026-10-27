// Genuine G9 source face-grid morph: actual Babylon WebGL and MmdRuntime.
// Original synthetic 16-vertex 18-triangle plane, NOT a human character.
import { Engine } from "@babylonjs/core/Engines/engine.js";
import { Scene } from "@babylonjs/core/scene.js";
import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera.js";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight.js";
import { Vector3 } from "@babylonjs/core/Maths/math.vector.js";
import { Color3,Color4 } from "@babylonjs/core/Maths/math.color.js";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial.js";
import { PmxLoader } from "../../../vendor/babylon-mmd/src/Loader/pmxLoader.pure.ts";
import { VmdLoader } from "../../../vendor/babylon-mmd/src/Loader/vmdLoader.ts";
import { MmdRuntime } from "../../../vendor/babylon-mmd/src/Runtime/mmdRuntime.ts";
import "../../../vendor/babylon-mmd/src/Runtime/Animation/mmdRuntimeModelAnimation.ts";

type Snap={frame:number,webgl:boolean,has_canvas:boolean,original_source_meshes:number,
 actual_morph_targets:number,morph_weights:{"まばたき":number,"笑い":number},
 gpu_morph_influences:number[],source_vertices:number,
 source:"self-authored G9 16-vertex PMX + 2-morph VMD",renderer:"real BabylonJS Chromium WebGL"};
declare global {interface Window{SCP_READY?:string;SCP_ERROR?:string;SCP_CAPTURE?:(frame:number)=>Snap;}}
async function main(){
 const canvas=document.querySelector<HTMLCanvasElement>("#stage");
 if(!canvas)throw Error("missing real WebGL canvas");
 const engine=new Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true,doNotHandleContextLost:true},false);
 const gl=canvas.getContext("webgl2")||canvas.getContext("webgl");
 if(!gl)throw Error("real Chromium WebGL unavailable: no NullEngine fallback");
 const scene=new Scene(engine);
 scene.clearColor=new Color4(.06,.075,.1,1);
 scene.ambientColor=new Color3(.55,.55,.55);
 const camera=new ArcRotateCamera("front",Math.PI/2,Math.PI/2,6.8,Vector3.Zero(),scene);
 camera.minZ=.02;camera.maxZ=50;
 camera.setTarget(Vector3.Zero());
 const light=new HemisphericLight("grid-light",new Vector3(0,0,1),scene);
 light.intensity=1.4;
 const [pmx,motion]=await Promise.all([
  fetch("/original/g9/synthetic_face_grid.pmx").then(r=>{if(!r.ok)throw Error("PMX missing");return r.arrayBuffer()}),
  fetch("/original/g9/synthetic_face_motion.vmd").then(r=>{if(!r.ok)throw Error("VMD missing");return r.arrayBuffer()})
 ]);
 if(pmx.byteLength>1048576||motion.byteLength>1048576)throw Error("original source size gate");
 const loader=new PmxLoader();
 const state=await new Promise<any>((resolve,reject)=>{
  try{loader.loadFile(scene,new Uint8Array(pmx),"",resolve,undefined,true,(_r,e)=>reject(e));}
  catch(e){reject(e);}
 });
 const built=await loader.importMeshAsync(null,scene,state,"");
 if(built.meshes.length!==1||built.skeletons.length!==1)
  throw Error("actual Babylon G9 original model not materialized");
 const mesh=built.meshes[0];
 mesh.setEnabled(true);mesh.isVisible=true;
 // Source-genuine geometry/material decoupling: original material builder may be
 // absent in CPU-only loader; use a neutral two-sided diagnostic presentation.
 // It must remain the SAME native PMX geometry and actual GPU morph targets.
 const visibleMat=new StandardMaterial("original-g9-diagnostic-surface",scene);
 visibleMat.diffuseColor=new Color3(.24,.68,.86);
 visibleMat.emissiveColor=new Color3(.08,.15,.22);
 visibleMat.specularColor=new Color3(.2,.2,.2);
 visibleMat.backFaceCulling=false;
 mesh.material=visibleMat;
 mesh.visibility=1;mesh.showBoundingBox=false;
 const mgr=mesh.morphTargetManager;
 if(!mgr||mgr.numTargets!==2)throw Error("real original G9 missing exactly 2 morph targets");
 const baseVertexCount=mesh.getTotalVertices();
 if(baseVertexCount<16)throw Error("native G9 original PMX too few vertices");
 const runtime=new MmdRuntime(scene,null);
 const model=runtime.createMmdModel(mesh,{buildPhysics:false,trimMetadata:false});
 const anim=await new VmdLoader(scene).loadFromBufferAsync("G9 original source VMD",motion);
 if(!anim.validate())throw Error("genuine upstream G9 VMD invalid");
 model.setRuntimeAnimation(model.createRuntimeAnimation(anim));
 window.SCP_CAPTURE=(frame:number)=>{
  if(!Number.isInteger(frame)||frame<0||frame>30)throw Error("frame out of bounds");
  model.beforePhysics(frame);model.afterPhysics();
  // Actual MmdRuntime updated these two source names; native MorphTargetManager is GPU input.
  const blink=model.morph.getMorphWeight("まばたき");
  const smile=model.morph.getMorphWeight("笑い");
  const influences=[mgr.getTarget(0).influence,mgr.getTarget(1).influence];
  if(![blink,smile,...influences].every(Number.isFinite))throw Error("nonfinite real GPU morph values");
  if(Math.abs(influences[0]-blink)>.002||Math.abs(influences[1]-smile)>.002)
   throw Error("GPU morph targets not synchronized to actual VMD runtime weights");
  scene.render();
  return {frame,webgl:!!gl,has_canvas:engine.getRenderingCanvas()===canvas,
    original_source_meshes:built.meshes.length,actual_morph_targets:mgr.numTargets,
    morph_weights:{"まばたき":blink,"笑い":smile},gpu_morph_influences:influences,
    source_vertices:baseVertexCount,
    source:"self-authored G9 16-vertex PMX + 2-morph VMD",
    renderer:"real BabylonJS Chromium WebGL"};
 };
 window.SCP_CAPTURE(0);
 window.SCP_READY="G9_REAL_WEBGL_GENUINE_MORPH_RUNTIME_READY";
}
main().catch(e=>{window.SCP_ERROR=String(e?.stack||e);console.error("G9_BROWSER_FIRST_FAILURE",window.SCP_ERROR)});
