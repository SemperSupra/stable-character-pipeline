"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const script=fs.readFileSync(require("node:path").join(__dirname,"ui.js"),"utf8");

function environment(responses){
  const nodes={run:{},submit:{disabled:false},job:{textContent:""},output:{hidden:true},front:{src:""},oblique:{src:""}};
  let onSubmit;nodes.run.addEventListener=(event,fn)=>{assert.equal(event,"submit");onSubmit=fn};
  const calls=[];
  const fetch=async(path,opts={})=>{
    calls.push({path,opts});
    if(!responses.length)throw Error("unexpected request");
    const answer=responses.shift();
    assert.equal(path,answer.path);
    return {ok:answer.ok,json:async()=>answer.data};
  };
  vm.runInNewContext(script,{document:{getElementById:id=>nodes[id]},fetch});
  assert.equal(typeof onSubmit,"function");
  return {nodes,calls,submit:()=>onSubmit({preventDefault(){}})};
}
const capabilities={scope:"public-synthetic",release:"HELD_R009_NOT_RUN_NOT_ADMITTED",revision:"a".repeat(40)};
const result={human_behavior:"FAIL_ABSTRACT_LIMBS_ONLY",release:"HELD_R009_NOT_RUN_NOT_ADMITTED"};
function response(path,data,ok=true){return {path,data,ok};}
async function success(){
  const e=environment([response("/v1/capabilities",capabilities),response("/v1/jobs",result)]);
  await e.submit();
  assert.equal(e.calls.length,2);
  assert.equal(e.calls[1].opts.method,"POST");
  const req=JSON.parse(e.calls[1].opts.body);
  assert.equal(req.source_class,"public-synthetic");
  assert.equal(req.revision,capabilities.revision);
  assert.equal(e.nodes.output.hidden,false);
  assert.equal(e.nodes.submit.disabled,false);
  assert.equal(e.nodes.front.src,"/v1/jobs/w7a-forward-24/media/OriginalFront");
  assert.equal(e.nodes.oblique.src,"/v1/jobs/w7a-forward-24/media/OriginalOblique");
  assert.match(e.nodes.job.textContent,/FAIL.*UNKNOWN.*HELD/);
}
async function rejectInvalidCapability(){
  const e=environment([response("/v1/capabilities",{...capabilities,release:"PASS"})]);
  await e.submit();
  assert.equal(e.calls.length,1);
  assert.equal(e.nodes.output.hidden,true);
  assert.equal(e.nodes.submit.disabled,false);
  assert.match(e.nodes.job.textContent,/not accepted/i);
}
async function rejectForgedScientificSuccess(){
  const e=environment([response("/v1/capabilities",capabilities),response("/v1/jobs",{...result,human_behavior:"PASS_HUMAN"})]);
  await e.submit();
  assert.equal(e.nodes.output.hidden,true);
  assert.equal(e.nodes.submit.disabled,false);
  assert.equal(e.nodes.front.src,"");
}
async function rejectTransportFailure(){
  const e=environment([response("/v1/capabilities",capabilities),response("/v1/jobs",{code:"SOURCE_REVISION_MISMATCH"},false)]);
  await e.submit();
  assert.equal(e.nodes.output.hidden,true);
  assert.match(e.nodes.job.textContent,/SOURCE_REVISION_MISMATCH/);
  assert.equal(e.nodes.submit.disabled,false);
}
(async()=>{for(const [name,fn] of Object.entries({success,rejectInvalidCapability,rejectForgedScientificSuccess,rejectTransportFailure})){await fn();console.log("R13_UI_MOCKED_EVENT_PASS",name)}console.log("R13_NO_BROWSER_OR_PRIVATE_PRODUCT_ACCEPTANCE")})().catch(e=>{console.error(e);process.exitCode=1});
