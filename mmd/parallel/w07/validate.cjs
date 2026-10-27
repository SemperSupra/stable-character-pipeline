"use strict";
// W07: exact-source synthetic GLB metadata variant and Khronos official validator.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const validator=require("gltf-validator");
const SHA={
 g7:"e5aa5b2f068c83acbdefe1a204931e616a22b42d7c42d589b54249963ffec954",
 g9:"a71aa6e0ac7c4b5a4e9c2e99da07f76d7dc6ca4be33d4068792c7f278e7ee5b9"
};
const digest=b=>crypto.createHash("sha256").update(b).digest("hex");
function decode(data){
 if(data.length<20||data.toString("ascii",0,4)!=="glTF"||
    data.readUInt32LE(4)!==2||data.readUInt32LE(8)!==data.length||
    data.readUInt32LE(16)!==0x4e4f534a)throw Error("source invalid GLB");
 const size=data.readUInt32LE(12);
 if(size>data.length-20)throw Error("source JSON chunk out of range");
 return {json:JSON.parse(data.subarray(20,20+size).toString("utf8")),tail:data.subarray(20+size)};
}
function transform(original,edit){
 const {json,tail}=decode(original);
 edit(json);
 const part=Buffer.from(JSON.stringify(json));
 const padding=Buffer.alloc((4-part.length%4)%4,0x20);
 const head=Buffer.from(original.subarray(0,20));
 const total=head.length+part.length+padding.length+tail.length;
 head.writeUInt32LE(total,8);
 head.writeUInt32LE(part.length+padding.length,12);
 return Buffer.concat([head,part,padding,tail]);
}
const check=bytes=>validator.validateBytes(Uint8Array.from(bytes),{uri:"scp-test.glb",maxIssues:200});
async function refuses(bytes){
 try{return (await check(bytes)).issues.numErrors>0;}catch{return true;}
}
async function evaluate(name,filename){
 const source=fs.readFileSync(filename);
 if(digest(source)!==SHA[name])throw Error("original synthetic source hash invalid");
 const original=await check(source);
 if(original.issues.numErrors!==0)throw Error("original source does not pass validator");
 const messages=original.issues.messages.map(x=>x.code);
 if(!messages.includes("NODE_SKINNED_MESH_NON_ROOT"))throw Error("unexpected absent nonroot-skin warning");
 const benign=transform(source,x=>{x.asset.extras={...x.asset.extras,scp_case:"W07 metadata-only synthetic variant"};});
 const other=await check(benign);
 if(other.issues.numErrors!==0||!other.issues.messages.some(x=>x.code==="NODE_SKINNED_MESH_NON_ROOT"))
   throw Error("metadata-only source metamorphism changed validation behavior");
 const invalidMagic=Buffer.from(source);invalidMagic[0]=0;
 const truncated=source.subarray(0,source.length-4);
 const skinMissing=transform(source,x=>{
  const n=x.nodes.find(v=>Number.isInteger(v.skin));
  if(!n)throw Error("no skinned source geometry");
  n.skin=x.skins.length+99;
 });
 const controls={
    invalid_magic:await refuses(invalidMagic),
    truncated:await refuses(truncated),
    invalid_skin_reference:await refuses(skinMissing)
 };
 if(Object.values(controls).some(v=>!v))throw Error("one GLB negative control admitted");
 return {source:name,sha256:digest(source),metadata_only_sha256:digest(benign),
  original_errors:original.issues.numErrors,metadata_variant_errors:other.issues.numErrors,
  warning_preserved:true,red_controls:controls};
}
async function main(){
 const [g7,g9,out]=process.argv.slice(2);
 if(!out)throw Error("usage g7.glb g9.glb output.json");
 const assets=[await evaluate("g7",g7),await evaluate("g9",g9)];
 const report={schema:"scp.mmd.parallel.w07.v1",
 status:"PASS_REAL_KHRONOS_METADATA_VARIANTS_SIX_NEGATIVE_CONTROLS",
 validator:validator.version(),original_assets:2,generated_metadata_variants:2,
 intentionally_invalid_variants_rejected:6,assets,
 limits:["Khronos generated Asset Generator corpus still untested",
 "original nonroot warning must not be suppressed",
 "MMD runtime physics and mesh deformation not implied"]};
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
 console.log("W07_KHRONOS_PARALLEL",JSON.stringify(report));
}
main().catch(e=>{console.error("W07_FIRST_FAILURE",e.stack||e);process.exitCode=1;});
