// Parallel W06: provenance-bounded metamorphic and adversarial tests of REAL
// Babylon-vs-independent-converter 31-frame, four-joint evidence.
// Go stdlib only. This is not a bespoke physical MMD solver or a 3D renderer.
package main

import (
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "fmt"
  "math"
  "os"
  "path/filepath"
  "sort"
)

const inputSHA="fc2c9a578814506d9cad65702c4ac1274d2ef6e9ec97c153d5a78060d81db19d"
const maxError=0.002
type Sample struct{
  Frame int `json:"frame"`
  JointName string `json:"joint_name"`
  Babylon []float64 `json:"babylon_xyz"`
  Independent []float64 `json:"independent_converter_xyz"`
  Delta float64 `json:"world_translation_delta_source_unit"`
}
type Evidence struct{
  Status string `json:"status"`
  AllSamples []Sample `json:"all_samples"`
  Tested int `json:"tested_world_joint_samples"`
  Failed int `json:"failed_samples_count"`
}
func distance(a,b []float64) float64{
  if len(a)!=3||len(b)!=3{return math.Inf(1)}
  d:=0.0
  for i:=0;i<3;i++{
    if math.IsNaN(a[i])||math.IsInf(a[i],0)||math.IsNaN(b[i])||math.IsInf(b[i],0){return math.Inf(1)}
    d+=(a[i]-b[i])*(a[i]-b[i])
  }
  return math.Sqrt(d)
}
func validate(e Evidence) error{
  if e.Status!="PASS_REAL_BABYLON_VS_DIRECT_31FRAME_WORLD_POSE"||e.Failed!=0||e.Tested!=124||len(e.AllSamples)!=124{
    return fmt.Errorf("source receipt failed or count/shape mismatch")
  }
  labels:=[]string{"腰","ひざ","足首","足ＩＫ"}
  seen:=map[string]bool{}
  each:=map[int]int{}
  for _,s:=range e.AllSamples{
    if s.Frame<0||s.Frame>30{return fmt.Errorf("wrong frame %d",s.Frame)}
    valid:=false;for _,n:=range labels{if n==s.JointName{valid=true}}
    if !valid{return fmt.Errorf("unknown/renamed joint %s",s.JointName)}
    key:=fmt.Sprintf("%02d/%s",s.Frame,s.JointName)
    if seen[key]{return fmt.Errorf("duplicate joint/frame %s",key)}
    seen[key]=true;each[s.Frame]++
    calc:=distance(s.Babylon,s.Independent)
    if calc>maxError||math.IsInf(calc,0)||math.IsNaN(calc)||math.Abs(calc-s.Delta)>1e-8{
      return fmt.Errorf("actual world-xyz disagreement or forged receipt %s: %.9f",key,calc)
    }
  }
  for i:=0;i<=30;i++{if each[i]!=4{return fmt.Errorf("frame %d missing joint",i)}}
  return nil
}
func transform(s Sample,scale float64,translate []float64)Sample{
  t:=s
  t.Babylon=append([]float64(nil),s.Babylon...)
  t.Independent=append([]float64(nil),s.Independent...)
  for i:=0;i<3;i++{t.Babylon[i]=scale*t.Babylon[i]+translate[i];t.Independent[i]=scale*t.Independent[i]+translate[i]}
  t.Delta=scale*s.Delta
  return t
}
func digest(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func main(){
 if len(os.Args)!=3 {panic("usage W06_SOURCE.json OUT.json")}
 in,out:=os.Args[1],os.Args[2]
 b,err:=os.ReadFile(in);if err!=nil{panic(err)}
 if digest(b)!=inputSHA{panic("W06 immutable source SHA mismatch: "+digest(b))}
 var e Evidence;if err=json.Unmarshal(b,&e);err!=nil{panic(err)}
 if err=validate(e);err!=nil{panic(err)}
 originalMax:=0.0
 for _,s:=range e.AllSamples{originalMax=math.Max(originalMax,distance(s.Babylon,s.Independent))}
 // Composition of global translations, unit conversion and time reversal must preserve exact pairing.
 tests:=map[string]bool{}
 for _,v:=range []struct{name string;scale float64;move []float64}{
   {"rigid_global_translation",1,[]float64{3.25,-7.125,19}},
   {"unit_conversion_x2",2,[]float64{0,0,0}},
   {"scale_and_translate",.5,[]float64{-14,9,3}},
 }{
   clone:=e
   clone.AllSamples=make([]Sample,len(e.AllSamples))
   for i,s:=range e.AllSamples{
     t:=transform(s,v.scale,v.move)
     // Pass normalized source-unit bound after uniform scale (never loosen absolute tolerance).
     t.Babylon=append([]float64(nil),t.Babylon...)
     t.Independent=append([]float64(nil),t.Independent...)
     for k:=0;k<3;k++{t.Babylon[k]=(t.Babylon[k]-v.move[k])/v.scale;t.Independent[k]=(t.Independent[k]-v.move[k])/v.scale}
     t.Delta=s.Delta
     clone.AllSamples[i]=t
   }
   if err=validate(clone);err!=nil{panic(v.name+" "+err.Error())}
   tests[v.name]=true
 }
 reversed:=e;reversed.AllSamples=append([]Sample(nil),e.AllSamples...)
 sort.Slice(reversed.AllSamples,func(i,j int)bool{return reversed.AllSamples[i].Frame>reversed.AllSamples[j].Frame})
 if err=validate(reversed);err!=nil{panic("time-reorder "+err.Error())}
 tests["frame_order_independence"]=true
 adversaries:=map[string]func(*Evidence){
 "forge_world_delta":func(x *Evidence){x.AllSamples[54].Delta=0},
 "freeze_one_bone":func(x *Evidence){x.AllSamples[42].Babylon[0]+=1},
 "duplicate_joint_frame":func(x *Evidence){x.AllSamples[31].Frame=x.AllSamples[30].Frame;x.AllSamples[31].JointName=x.AllSamples[30].JointName},
 "missing_frame":func(x *Evidence){x.AllSamples=x.AllSamples[:123]},
 "nonfinite_observation":func(x *Evidence){x.AllSamples[4].Independent[1]=math.NaN()},
 }
 rejected:=[]string{}
 for name,mutate:=range adversaries{
   clone:=e;clone.AllSamples=append([]Sample(nil),e.AllSamples...)
   for i:=range clone.AllSamples{
     clone.AllSamples[i].Babylon=append([]float64(nil),e.AllSamples[i].Babylon...)
     clone.AllSamples[i].Independent=append([]float64(nil),e.AllSamples[i].Independent...)
   }
   mutate(&clone)
   if err:=validate(clone);err==nil{panic("failed to reject adversarial mutation "+name)}
   rejected=append(rejected,name)
 }
 sort.Strings(rejected)
 report:=map[string]any{
  "schema":"scp.mmd.parallel.w06-invariants.v1",
  "status":"PASS_REAL_124_SOURCE_SAMPLES_THREE_METAMORPHIC_AND_FIVE_RED_CONTROLS",
  "source_sha256":inputSHA,"origin":"exact immutable W04 real third-engine four-bone world-pose artifact",
  "samples":124,"frames":31,"named_joints":4,
  "max_original_world_delta_source_unit":originalMax,
  "tolerance_source_unit":maxError,
  "metamorphic_checks":tests,"red_controls_rejected":rejected,
  "not_qualified":[]string{"genuine MikuMikuDance physics","live solver robustness to transformed input","source physical meter scale","production character motion"},
 }
 if err=os.MkdirAll(filepath.Dir(out),0755);err!=nil{panic(err)}
 output,_:=json.MarshalIndent(report,"","  ");if err=os.WriteFile(out,append(output,'\n'),0644);err!=nil{panic(err)}
 fmt.Println("W06_PARALLEL_METAMORPHIC",string(output))
}
