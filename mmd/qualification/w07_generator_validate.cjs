'use strict';
// Actual pinned Khronos MIT glTF-Asset-Generator source; genuine official validator.
// Two separately admitted corpus categories, no model/assets from private sources.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const validator=require('gltf-validator');
const root=process.argv[2], lane=process.argv[3], out=process.argv[4];
if(!out||!['skin','negative'].includes(lane))throw Error('usage KHRONOS_ROOT skin|negative OUT.json');
const subjects=(lane==='skin')?[
  ['Positive','Animation_Skin'],['Positive','Animation_SkinType']
]:[['Negative','Mesh_NoPosition']];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const assert=(x,s)=>{if(!x)throw Error(s)};
async function readOne(category,group,model){
 const location=path.join(root,'Output',category,group,model.fileName);
 const base=path.dirname(location),text=fs.readFileSync(location,'utf8');
 // Only same-directory relative BIN references are allowed.
 const doc=JSON.parse(text);
 const external=async uri=>{
   if(!/^[a-zA-Z0-9_.-]+$/.test(uri))throw Error('external resource path not eligible');
   const file=path.join(base,uri);
   return new Uint8Array(fs.readFileSync(file));
 };
 const result=await validator.validateString(text,{
   uri:model.fileName,externalResourceFunction:external,maxIssues:128
 });
 const count=result.issues.numErrors||0;
 return {file:model.fileName,source_gltf_sha256:sha(Buffer.from(text)),
   errors:count,warnings:result.issues.numWarnings||0,
   codes:result.issues.messages.map(x=>x.code).filter((x,i,arr)=>arr.indexOf(x)===i),
   expected_valid:category==='Positive',actual_valid:count===0};
}
async function main(){
 const results=[];
 for(const [category,group] of subjects){
   const dir=path.join(root,'Output',category,group);
   const manifest=JSON.parse(fs.readFileSync(path.join(dir,'Manifest.json'),'utf8'));
   const models=Array.isArray(manifest)?manifest:manifest.models;
   assert(Array.isArray(models)&&models.length>0,'upstream generator Manifest not understood');
   for(const model of models)results.push(await readOne(category,group,model));
 }
 const positives=results.filter(r=>r.expected_valid);
 const negatives=results.filter(r=>!r.expected_valid);
 const unexpected=results.filter(r=>r.actual_valid!==r.expected_valid);
 const result={
   schema:'scp.mmd.w07-khronos-generator.v1',
   status:unexpected.length?'REAL_UPSTREAM_CORPUS_CONFORMANCE_DISAGREEMENT':'PASS_GENUINE_KHRONOS_ASSET_GENERATOR_SELECTED_CATEGORIES',
   upstream_source_commit:'3d99767e9a67fbfe109f0d298c1e8d909bcac9db',
   upstream_license:'KhronosGroup glTF-Asset-Generator MIT',
   official_validator_version:validator.version(),
   lane,positive_models:positives.length,negative_models:negatives.length,
   unexpected:unexpected.map(x=>({file:x.file,errors:x.errors,codes:x.codes})),results,
   limits:['subset of official generated asset corpus, not full coverage',
    'specification validator verdict is distinct from actual Babylon or Blender rendering',
    'no private or third-party human reference assets used']
 };
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
 console.log('KHRONOS_GENERATOR_NATIVE',JSON.stringify({status:result.status,lane,total:results.length,unexpected:result.unexpected}));
 if(unexpected.length)process.exitCode=1;
}
main().catch(e=>{console.error('KHRONOS_GENERATOR_FIRST_FAILURE',e.stack||e);process.exitCode=1});
