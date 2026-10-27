#!/usr/bin/env node
// Genuine Khronos Validator (Apache-2.0) on immutable prior original MMD outputs.
// No bespoke parsing for glTF conformance. Semantic IK/morph checks remain separate.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('gltf-validator');

async function inspect(file) {
  const input = fs.readFileSync(file);
  const checksum = crypto.createHash('sha256').update(input).digest('hex');
  const response = await validator.validateBytes(new Uint8Array(input), {
    uri:path.basename(file), writeTimestamp:false, maxIssues:0
  });
  const issues=response.issues || {};
  return {
    file:path.basename(file), sha256:checksum,
    format_errors:issues.numErrors || 0,
    format_warnings:issues.numWarnings || 0,
    format_infos:issues.numInfos || 0,
    format_hints:issues.numHints || 0,
    messages:issues.messages || [],
    conformance_pass:(issues.numErrors || 0)===0,
    source_classes:["synthetic-self-authored","exact-known-GHA-artifact"],
    meaning_not_tested:["MMD IK fidelity","physics solver parity","contact and friction",
       "source bone morph semantics","license authorization for other assets"]
  };
}

async function main() {
  const files=process.argv.slice(2);
  if(files.length<4)throw new Error("expected at least four existing original source MMD interchange GLBs");
  const output={schema:"scp.mmd.khronos-conformance.v1",validator:"Khronos glTF Validator",validator_version:validator.version(),pin:"2.0.0-dev.3.10",assets:[],
    negative_control:{},overall:"PENDING"};
  fs.mkdirSync("standards-output",{recursive:true});
  try {
    for(const file of files) {
      const result=await inspect(file);
      output.assets.push(result);
      console.log("G11_KHRONOS",JSON.stringify({file:result.file,errors:result.format_errors,warnings:result.format_warnings,sha256:result.sha256}));
    }
    const original=fs.readFileSync(files[0]);
    let detected=false,why="";
    try {
      const bad=await validator.validateBytes(new Uint8Array(original.subarray(0,original.length-4)), {
        uri:"g11-deliberately-truncated.glb",writeTimestamp:false,maxIssues:0
      });
      detected=(bad.issues?.numErrors || 0)>0;
      why=String(bad.issues?.messages?.[0]?.code || "none");
    } catch(e) {
      detected=true;
      why="rejected_exception:"+String(e).slice(0,160);
    }
    output.negative_control={mutation:"truncate last 4 GLB bytes",detected,reason:why};
    output.overall=output.assets.every(a=>a.conformance_pass)&&detected?
      "PASS_KHRONOS_STANDARD_COMPLIANCE":"FAIL_KHRONOS_STANDARD_COMPLIANCE";
  } catch(error) {
    output.overall="FAIL_KHRONOS_HARNESS_EXCEPTION";
    output.exception=String(error?.stack||error);
  }
  const json=JSON.stringify(output,null,2)+"\n";
  fs.writeFileSync("standards-output/khronos_conformance.json",json);
  console.log("G11_SUMMARY",JSON.stringify({result:output.overall,negative:output.negative_control,version:output.validator_version,assets:output.assets.length}));
  if(output.overall!=="PASS_KHRONOS_STANDARD_COMPLIANCE")process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
