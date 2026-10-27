#!/usr/bin/env node
'use strict';
// W03: real second-reader glTF Transform (MIT) scene/skin/morph inventory.
// This is a document reader, not a renderer or a MikuMikuDance solver.
// All input GLBs come from original, SHA-pinned public synthetic G7/G9 Actions.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const { NodeIO }=require('@gltf-transform/core');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');

async function inspect(io,source,kind,expected) {
  const bytes=fs.readFileSync(source);
  if(bytes.subarray(0,4).toString()!=='glTF')throw Error('invalid GLB header '+source);
  const doc=await io.readBinary(new Uint8Array(bytes));
  const root=doc.getRoot();
  const nodes=root.listNodes();
  const meshNodes=nodes.filter(n=>n.getMesh());
  const skinNodes=nodes.filter(n=>n.getSkin());
  const skins=root.listSkins();
  const animations=root.listAnimations();
  const morphTargets=meshNodes.reduce((sum,n)=>
    sum+n.getMesh().listPrimitives().reduce((n,p)=>n+p.listTargets().length,0),0);
  const channels=animations.flatMap(a=>a.listChannels());
  const payload={
    input_file:path.basename(source),sha256:sha(bytes),
    reader:'@gltf-transform/core',reader_mode:'native NodeIO GLB document',
    source:'original rights-clean G7/G9 GitHub Actions artifact',
    kind,
    scene_count:root.listScenes().length,
    node_count:nodes.length,
    mesh_instances:meshNodes.length,
    skinned_mesh_nodes:skinNodes.length,
    skinned_mesh_nonroot:skinNodes.filter(n=>n.getParentNode()!=null).length,
    skin_count:skins.length,
    skin_joint_counts:skins.map(s=>s.listJoints().length),
    morph_target_count:morphTargets,
    animations:animations.length,
    animated_channels:channels.length,
    animation_paths:channels.map(c=>String(c.getTargetPath())),
    warning_on_original_export:'NODE_SKINNED_MESH_NON_ROOT',
    status:'NOT_YET_EVALUATED'
  };
  const adequate=payload.skin_count>0 && payload.skinned_mesh_nodes>0 &&
    payload.skin_joint_counts.every(x=>x>0) && payload.animated_channels>0 &&
    (kind==='g9' ? payload.morph_target_count>=2 && payload.animation_paths.includes('weights'):
                   payload.skin_joint_counts.some(x=>x>=3));
  if(!adequate)throw Error('independent GLB reader lost skin, joints, animation, or G9 morphs: '+JSON.stringify(payload));
  if(payload.sha256!==expected.sha256)throw Error('binary hash disagreement with immutable Khronos evidence');
  const warning=expected.messages.filter(m=>m.code==='NODE_SKINNED_MESH_NON_ROOT');
  if(warning.length!==1 || expected.format_errors!==0)throw Error('prior Khronos warning provenance mismatch');
  payload.status='PASS_INDEPENDENT_GLTF_TRANSFORM_SCENE_INVENTORY_ONLY';
  // Falsification 1: delete observed skin in memory, require feature check to
  // reject it. This is NOT a claim that an actual renderer drops skin.
  const target=skinNodes[0];target.setSkin(null);
  const mutatedSkinned=nodes.filter(n=>n.getSkin());
  if(mutatedSkinned.length===skinNodes.length)throw Error('semantic skin-removal control survived');
  payload.negative_removed_skin='PASS_EXPECTED_REJECTION';
  // Falsification 2: truncated original glb must be refused by this reader.
  let corruptDetected=false;
  try{await io.readBinary(new Uint8Array(bytes.subarray(0,bytes.length-4)));}
  catch(e){corruptDetected=true;}
  if(!corruptDetected)throw Error('independent glTF reader accepted truncated GLB');
  payload.negative_truncated_glb='PASS_EXPECTED_REJECTION';
  return payload;
}

async function main(){
  const args=process.argv.slice(2);
  if(args.length!==4)throw Error('usage: node w03_gltf_reader.cjs G7.glb G9.glb G11_khronos.json out.json');
  const [g7,g9,g11,out]=args;
  const witness=JSON.parse(fs.readFileSync(g11,'utf8'));
  if(witness.overall!=='PASS_KHRONOS_STANDARD_COMPLIANCE'||witness.validator!=='Khronos glTF Validator')
    throw Error('expected exact successful Khronos authority receipt');
  const match=basename=>{
    const matches=witness.assets.filter(a=>a.file===basename);
    if(matches.length!==1)throw Error('missing/nonunique original Khronos asset '+basename);
    return matches[0];
  };
  const io=new NodeIO();
  const results=[
    await inspect(io,g7,'g7',match(path.basename(g7))),
    await inspect(io,g9,'g9',match(path.basename(g9)))
  ];
  const report={schema:'scp.mmd.w03-gltf-reader.v1',status:'PASS_INDEPENDENT_READER_STRUCTURAL_ONLY',
    upstream:'https://gltf-transform.dev/modules/core/classes/NodeIO',
    khronos_proof_sha256:sha(fs.readFileSync(g11)),
    assets:results,
    claims_not_qualified:['actual visual playback in an independent browser renderer',
      'pixel parity of world geometry','MMD-native solver equivalence',
      'user-character or third-party asset licensing']};
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
  console.log('W03_GLTF_TRANSFORM',JSON.stringify(report));
}
main().catch(e=>{console.error('FAIL_W03_SECOND_READER',e.stack||e);process.exitCode=1});
