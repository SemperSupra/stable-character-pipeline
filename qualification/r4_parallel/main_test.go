package main

import (
  "encoding/json"
  "math"
  "os"
  "strings"
  "testing"
)
func registry(t *testing.T)(Registry,[]byte){
  t.Helper()
  raw,err:=os.ReadFile("../r4_admission/candidates.json")
  if err!=nil{t.Fatal(err)}
  var r Registry
  if err:=json.Unmarshal(raw,&r);err!=nil{t.Fatal(err)}
  return r,raw
}
func TestRightsSourceOnly(t *testing.T){
  _,raw:=registry(t)
  r,err:=execute("rights",raw)
  if err!=nil{t.Fatal(err)}
  if r.Candidates!=5 || r.ActualModelInferences!=0 || r.GPURuns!=0 || r.WeightsDownloaded!=0 || !r.SourceOnly{
    t.Fatalf("rights survey was misrepresented: %+v",r)
  }
}
func TestRightsForbiddenExecution(t *testing.T){
  for _,which:=range []string{"weights","media","inference","private","paid"}{
    r,_:=registry(t)
    switch which{
    case "weights":r.FetchWeights=true
    case "media":r.FetchSourceMedia=true
    case "inference":r.ExecuteModelInference=true
    case "private":r.AllowPrivateInputs=true
    case "paid":r.AllowPaidCompute=true
    }
    if err:=validRegistry(r);err==nil{t.Fatalf("accepted forbidden %s",which)}
  }
}
func TestRightsMissingPerAssetGate(t *testing.T){
  r,_:=registry(t)
  r.Candidates[0].ExternalAssets=nil
  if err:=validRegistry(r);err==nil{t.Fatal("missing external source asset rights silently accepted")}
  r,_=registry(t)
  r.Candidates[1].ActualInferenceStatus="PASS_UNPROVEN"
  if err:=validRegistry(r);err==nil{t.Fatal("unproven learned model PASS accepted")}
  r,_=registry(t)
  r.Candidates[2].WeightsTerms=""
  if err:=validRegistry(r);err==nil{t.Fatal("weights right conflated with code rights")}
}
func TestAdaptersCapabilityMapping(t *testing.T){
  reg,raw:=registry(t)
  a,err:=contracts(reg)
  if err!=nil{t.Fatal(err)}
  if len(a)!=5{t.Fatalf("expected 5 contracts not %d",len(a))}
  seen:=map[string]AdapterContract{}
  for _,c:=range a{seen[c.Model]=c;if c.Tested!="CONTRACT_ONLY_NO_MODEL_INFERENCE"{t.Fatal("forged model inference")}}
  for _,name:=range []string{"unirig","skintokens"}{
    c:=seen[name]
    if c.OutputKind!="MODEL_ESTIMATED_SKELETON_AND_SKIN_WEIGHTS" || c.RequiresExistingRig{
      t.Fatalf("wrong mesh auto-rigger contract: %s",name)
    }
  }
  if !seen["mocapanything-v2"].RequiresExistingRig || !seen["motion2mixamorig"].RequiresExistingRig{
    t.Fatal("reference skeleton requirement erased")
  }
  if seen["sam-3d-body"].OutputKind!="MODEL_ESTIMATED_BODY_MESH"{
    t.Fatal("still photo estimated mesh capability mismatch")
  }
  out,err:=execute("adapters",raw)
  if err!=nil||out.Candidates!=5||len(out.Contracts)!=5{t.Fatalf("adapters output invalid %v %v",out.Candidates,err)}
}
func TestAdaptersRequireIndependentRights(t *testing.T){
  reg,_:=registry(t)
  a,err:=contracts(reg);if err!=nil{t.Fatal(err)}
  for _,c:=range a{
    req:=AdapterRequest{
      HasMediaRights:true,HasWeightRights:true,HasDestinationRigRights:true,ReferenceRig:true,
    }
    switch c.OutputKind{
    case "MODEL_ESTIMATED_SKELETON_AND_SKIN_WEIGHTS":req.MediaKind="mesh"
    case "MODEL_ESTIMATED_BODY_MESH":req.MediaKind="photo"
    default:req.MediaKind="video"
    }
    if err:=validateAdapter(c,req);err!=nil{t.Fatalf("typed preflight should accept shape for %s: %v",c.Model,err)}
    for i:=0;i<3;i++{
      blocked:=req
      switch i{
      case 0: blocked.HasMediaRights=false
      case 1: blocked.HasWeightRights=false
      case 2: blocked.HasDestinationRigRights=false
      }
      if err:=validateAdapter(c,blocked);err==nil{t.Fatalf("%s accepted missing rights lane %d",c.Model,i)}
    }
    req.AutoDownload=true
    if err:=validateAdapter(c,req);err==nil{t.Fatal("downloading weights not gated")}
  }
}
func TestAdaptersNoUnprovenIdentityOr3D(t *testing.T){
  r,_:=registry(t);a,err:=contracts(r);if err!=nil{t.Fatal(err)}
  for _,c:=range a{
    req:=AdapterRequest{HasMediaRights:true,HasWeightRights:true,HasDestinationRigRights:true,ReferenceRig:true,MediaKind:"video",ClaimTrue3D:true}
    if err:=validateAdapter(c,req);err==nil{t.Fatal("true 3D claim accepted by source-only lane")}
    req.ClaimTrue3D=false;req.ClaimIdentityRecovered=true
    if err:=validateAdapter(c,req);err==nil{t.Fatal("biometric identity claim accepted by source-only lane")}
  }
  r.Candidates[0].Capability="PHOTO_AUTO_ID_AND_3D"
  if _,err:=contracts(r);err==nil{t.Fatal("new capability silently admitted")}
}
func TestAdaptersReferenceRigAndInputTypes(t *testing.T){
  r,_:=registry(t);a,err:=contracts(r);if err!=nil{t.Fatal(err)}
  for _,c:=range a{
    req:=AdapterRequest{HasMediaRights:true,HasWeightRights:true,HasDestinationRigRights:true,MediaKind:"INVALID_INPUT"}
    if err:=validateAdapter(c,req);err==nil{t.Fatal("invalid input type accepted for "+c.Model)}
    if c.RequiresExistingRig {
      req.MediaKind="video"
      if err:=validateAdapter(c,req);err==nil||!strings.Contains(err.Error(),"reference rig"){t.Fatal("missing rig accepted for "+c.Model)}
    }
  }
}
func TestSyntheticSkinDeformation(t *testing.T){
  s,err:=syntheticReceipt()
  if err!=nil{t.Fatal(err)}
  if s.Metric3DRecovered||s.ActualBlenderImport||s.JointCount!=3||s.Frames!=3||s.VertexCount!=3||s.MaxVertexDisplacement<.01 {
    t.Fatalf("synthetic proof inadequate or overclaimed %+v",s)
  }
  _,raw:=registry(t);r,err:=execute("synthetic",raw)
  if err!=nil||r.Synthetic==nil||r.ActualModelInferences!=0{t.Fatalf("invalid synthetic lane %v",err)}
}
func TestSyntheticCycleAndDisconnectedRoots(t *testing.T){
  r:=syntheticFixture()
  r.Joints[0].Parent=2
  if err:=validateRig(r);err==nil{t.Fatal("cycle accepted")}
  r=syntheticFixture()
  r.Joints[2].Parent=-1
  if err:=validateRig(r);err==nil{t.Fatal("two roots accepted")}
  r=syntheticFixture()
  r.Joints[2].Parent=99
  if err:=validateRig(r);err==nil{t.Fatal("out-of-range parent accepted")}
}
func TestSyntheticSkinWeightsAndNaN(t *testing.T){
  r:=syntheticFixture()
  r.Vertices[0].W=[2]float64{.5,.7}
  if err:=validateRig(r);err==nil{t.Fatal("unnormalized weights accepted")}
  r=syntheticFixture()
  r.Vertices[0].IDs=[2]int{1,55}
  if err:=validateRig(r);err==nil{t.Fatal("invalid joint skin index accepted")}
  r=syntheticFixture()
  r.Vertices[1].Pos[0]=math.NaN()
  if err:=validateRig(r);err==nil{t.Fatal("nonfinite mesh accepted")}
}
func TestSyntheticMissingnessAndClock(t *testing.T){
  r:=syntheticFixture()
  r.Frames[1].TimeMS=1500
  if err:=validateRig(r);err==nil{t.Fatal("time gap silently interpolated")}
  r=syntheticFixture()
  r.Frames[1].Visible[1]=false
  if err:=validateRig(r);err==nil{t.Fatal("unobserved pose filled without explicit gap policy")}
  r=syntheticFixture()
  r.Frames[2].Delta=r.Frames[2].Delta[:2]
  if err:=validateRig(r);err==nil{t.Fatal("partial pose accepted")}
  r=syntheticFixture()
  if _,err:=deform(r,99);err==nil{t.Fatal("out-of-range motion frame accepted")}
}
func TestUnknownParallelLane(t *testing.T){
  _,b:=registry(t)
  if _,err:=execute("private_GPU",b);err==nil{t.Fatal("unknown lane accepted")}
}
