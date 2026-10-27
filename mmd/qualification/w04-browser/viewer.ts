// W04 browser witness: genuine BabylonJS WebGL Engine + pinned Babylon MMD
// PmxLoader/VmdLoader/MmdRuntime. Source 4-bone synthetic G10, no external art.
// Gold joint markers/line segments are explicitly DIAGNOSTIC overlay geometry,
// NOT native PMX character skin proof or MikuMikuDance source footage.
import { Engine } from "@babylonjs/core/Engines/engine.js";
import { Scene } from "@babylonjs/core/scene.js";
import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera.js";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight.js";
import { Vector3, Color3, Color4 } from "@babylonjs/core/Maths/math.vector.js";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial.js";
import { MeshBuilder } from "@babylonjs/core/Meshes/meshBuilder.js";
import { PmxLoader } from "../../../vendor/babylon-mmd/src/Loader/pmxLoader.pure.ts";
import { VmdLoader } from "../../../vendor/babylon-mmd/src/Loader/vmdLoader.ts";
import { MmdRuntime } from "../../../vendor/babylon-mmd/src/Runtime/mmdRuntime.ts";
import "../../../vendor/babylon-mmd/src/Runtime/Animation/mmdRuntimeModelAnimation.ts";

type BonePoint={name:string,x:number,y:number,z:number};
type CaptureResponse={frame:number,has_canvas:boolean,webgl:boolean,
  rendered_original_meshes:number,original_bones:BonePoint[],marker_count:number,
  source_model:"original self-authored G10 PMX",source_motion:"original self-authored G10 VMD",
  visual_label:"actual BabylonJS WebGL-rendered synthetic PMX with diagnostic bone markers"};
declare global { interface Window { SCP_CAPTURE?: (f:number)=>CaptureResponse; SCP_READY?:string; SCP_ERROR?:string; } }
async function start(){
  const canvas=document.querySelector<HTMLCanvasElement>("#stage");
  if(!canvas)throw Error("missing render canvas");
  const engine=new Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true,doNotHandleContextLost:true},false);
  const gl=canvas.getContext("webgl2")||canvas.getContext("webgl");
  if(!gl)throw Error("no actual Chromium WebGL context; a NullEngine fake is forbidden");
  const scene=new Scene(engine);
  scene.useRightHandedSystem=false;
  scene.clearColor=new Color4(.055,.075,.11,1);
  scene.ambientColor=new Color3(.45,.45,.45);
  const camera=new ArcRotateCamera("camera",-Math.PI/2.6,Math.PI/2.9,4.2,new Vector3(0,1,0),scene);
  camera.minZ=.02;
  camera.maxZ=100;
  camera.setTarget(new Vector3(0,1.0,0));
  const lighting=new HemisphericLight("diagnostic_fill",new Vector3(-.5,2,-1),scene);
  lighting.intensity=1.15;
  lighting.diffuse=new Color3(1,.97,.89);
  const base=new URL("/original/g10/",location.href);
  const [pmx,motion]=await Promise.all([
    fetch(new URL("synthetic_two_link_ik.pmx",base)).then(r=>{if(!r.ok)throw Error("PMX not found");return r.arrayBuffer()}),
    fetch(new URL("synthetic_foot_goal.vmd",base)).then(r=>{if(!r.ok)throw Error("VMD not found");return r.arrayBuffer()})
  ]);
  if(pmx.byteLength>1024*1024||motion.byteLength>1024*1024)throw Error("synthetic source budget exceeded");
  const loader=new PmxLoader();
  const state=await new Promise<any>((resolve,reject)=>{
    try {loader.loadFile(scene,new Uint8Array(pmx),"",resolve,undefined,true,(_req,e)=>reject(e));}
    catch(e){reject(e);}
  });
  const built=await loader.importMeshAsync(null,scene,state,"");
  if(built.meshes.length<1||built.skeletons.length!==1||built.skeletons[0].bones.length!==4)
    throw Error("real browser PmxLoader lost original four-bone synthetic rig");
  const pmxMeshes=built.meshes;
  for(const m of pmxMeshes){m.setEnabled(true);m.isVisible=true;}
  const runtime=new MmdRuntime(scene,null);
  const model=runtime.createMmdModel(pmxMeshes[0],{buildPhysics:false,trimMetadata:false});
  const animation=await new VmdLoader(scene).loadFromBufferAsync("original-vmd",motion);
  if(!animation.validate())throw Error("native VMD source animation invalid");
  const handle=model.createRuntimeAnimation(animation);
  model.setRuntimeAnimation(handle);
  const names=["腰","ひざ","足首","足ＩＫ"];
  const markerMaterial=names.map((n,i)=>{
    const mat=new StandardMaterial("marker_material_"+i,scene);
    mat.diffuseColor=(i===3)?new Color3(.95,.25,.4):new Color3(.96,.72,.16);
    mat.emissiveColor=(i===3)?new Color3(.32,.06,.08):new Color3(.23,.15,.03);
    return mat;
  });
  const markers=names.map((n,i)=>{
    const marker=MeshBuilder.CreateSphere("diagnostic_original_bone_"+n,{diameter:i===3?.12:.085,segments:12},scene);
    marker.material=markerMaterial[i];
    return marker;
  });
  const links=([0,1] as const).map(i=>{
    const ln=MeshBuilder.CreateLines("diagnostic_bone_link_"+i,
      {points:[new Vector3(),new Vector3()],updatable:true},scene);
    ln.color=new Color3(.98,.82,.22);
    return ln;
  });
  let lastFrame=-1;
  window.SCP_CAPTURE=(frame:number)=>{
    if(!Number.isInteger(frame)||frame<0||frame>30)throw Error("frame outside source VMD 0-30");
    model.beforePhysics(frame);
    model.afterPhysics();
    const bp=names.map(name=>{
      const bone=model.runtimeBones.find(b=>b.name===name);
      if(!bone)throw Error("missing actual original PMX bone "+name);
      const v=bone.getWorldTranslationToRef(new Vector3());
      if(![v.x,v.y,v.z].every(Number.isFinite))throw Error("nonfinite original world pose");
      return {name,x:v.x,y:v.y,z:v.z};
    });
    for(let i=0;i<markers.length;i++)markers[i].position.copyFromFloats(bp[i].x,bp[i].y,bp[i].z);
    for(let i=0;i<links.length;i++){
      MeshBuilder.CreateLines("diagnostic_bone_link_"+i,
        {points:[new Vector3(bp[i].x,bp[i].y,bp[i].z),
                 new Vector3(bp[i+1].x,bp[i+1].y,bp[i+1].z)],
          instance:links[i]},scene);
    }
    scene.render();
    lastFrame=frame;
    return {frame,has_canvas:engine.getRenderingCanvas()===canvas,webgl:!!gl,
      rendered_original_meshes:pmxMeshes.length,original_bones:bp,marker_count:markers.length,
      source_model:"original self-authored G10 PMX",source_motion:"original self-authored G10 VMD",
      visual_label:"actual BabylonJS WebGL-rendered synthetic PMX with diagnostic bone markers"};
  };
  window.SCP_CAPTURE(0);
  window.SCP_READY="ACTUAL_WEBGL_BABYLON_MMD_NATIVE_RUNTIME_INITIALIZED";
}
start().catch(err=>{window.SCP_ERROR=String(err?.stack||err);console.error("BROWSER_MMD_FIRST_FAILURE",window.SCP_ERROR);});
