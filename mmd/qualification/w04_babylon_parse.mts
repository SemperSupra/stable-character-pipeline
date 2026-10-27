// W04: REAL pinned babylon-mmd source PMX/VMD parser qualification.
// This is NOT Babylon runtime mesh, MMD animation evaluation or 3D rendering.
// Deliberately use its real TS parser source with tsx, not a bespoke substitute.
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import { PmxReader } from "../../vendor/babylon-mmd/src/Loader/Parser/pmxReader.ts";
import { VmdData, VmdObject } from "../../vendor/babylon-mmd/src/Loader/Parser/vmdObject.ts";
const sha=(d:Uint8Array)=>crypto.createHash("sha256").update(d).digest("hex");
const ab=(b:Buffer)=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);
async function examine(label:string,modelFile:string,motionFile:string){
  const model=fs.readFileSync(modelFile), motion=fs.readFileSync(motionFile);
  if(model.length>1<<20 || motion.length>1<<20)throw Error("fixture must be bounded synthetic source");
  const pmx=await PmxReader.ParseAsync(ab(model));
  const vmd=VmdData.CheckedCreate(ab(motion));
  if(vmd==null)throw Error("real Babylon VMD data reader rejected known original VMD");
  const vmdObject=VmdObject.Parse(vmd);
  const r={
    case:label,
    source_model_sha256:sha(model),source_vmd_sha256:sha(motion),
    parser:"babylon-mmd upstream PmxReader.ParseAsync and VmdData.CheckedCreate/VmdObject.Parse",
    pmx_version:pmx.header.version,vertices:pmx.vertices.length,triangles:pmx.indices.length/3,
    bones:pmx.bones.length,morphs:pmx.morphs.length,
    vmd_bone_keyframes:vmd.boneKeyFrameCount,vmd_morph_keyframes:vmd.morphKeyFrameCount,
    vmd_camera_keyframes:vmd.cameraKeyFrameCount,
    vmd_object_present:!!vmdObject,
    status:"PASS_PINNED_REAL_BABYLON_NATIVE_PARSER_SOURCE_ONLY"
  };
  if(r.vertices<1||r.bones<1||r.triangles<1||
      (label==="g10" && (r.bones<4||r.vmd_bone_keyframes<2)) ||
      (label==="g9" && (r.morphs<2||r.vmd_morph_keyframes<2)))
    throw Error("upstream parser lost original rig/morph/motion semantics: "+JSON.stringify(r));
  // Falsifying controls against actual pinned source parser, NOT a checksum mock.
  let pmxBad=false,vmdBad=false;
  const badModel=Buffer.from(model);badModel[0]=0;
  try{await PmxReader.ParseAsync(ab(badModel))}catch(e){pmxBad=true}
  const badMotion=Buffer.from(motion);badMotion[0]=0;
  try{vmdBad=VmdData.CheckedCreate(ab(badMotion))===null}catch(e){vmdBad=true}
  if(!pmxBad||!vmdBad)throw Error("genuine PMX/VMD parser accepted intentionally invalid magic");
  return {...r,negative_corrupt_pmx:"EXPECTED_REJECTION",negative_corrupt_vmd:"EXPECTED_REJECTION",
    runtime_pose_evaluation:"NOT_TESTED",headless_browser_rendering:"NOT_TESTED",
    source_rights:"ORIGINAL_SYNTHETIC_FIXTURE_ONLY"};
}
async function main(){
  const args=process.argv.slice(2);
  if(args.length!==5)throw Error("expected G10 PMX, G10 VMD, G9 PMX, G9 VMD, output JSON");
  const [g10m,g10v,g9m,g9v,out]=args;
  const r={schema:"scp.mmd.w04-babylon-source-parser.v1",
    upstream_commit:"ccb750db2998ed1067017eaf67f3fc987cfba6f8",
    decision:"PARTIAL_PARSER_PASS_FULL_RUNTIME_HEADLESS_NOT_TESTED",
    cases:[await examine("g10",g10m,g10v),await examine("g9",g9m,g9v)]};
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(r,null,2)+"\n");
  console.log("W04_BABYLON_NATIVE_SOURCE_PARSER",JSON.stringify(r));
}
main().catch(e=>{console.error("W04_NATIVE_PARSER_FAIL",e.stack||e);process.exitCode=1});
