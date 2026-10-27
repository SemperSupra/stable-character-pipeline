// Standalone public F2a rig admission; Go standard library only.
// This qualifies topology/animation presence, NOT biomechanical accuracy.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
)

type node struct{ Name string; Children []int }
type target struct{ Node int; Path string }
type channel struct{ Target target }
type animation struct{ Channels []channel }
type scene struct{ Asset struct{ Version string }; Nodes []node; Animations []animation }
func sha(raw []byte)string{v:=sha256.Sum256(raw);return hex.EncodeToString(v[:])}

func inventory(raw []byte)(map[string]any,error){
 if len(raw)>8<<20{return nil,errors.New("gltf JSON exceeds 8 MiB")}
 var doc scene
 if err:=json.Unmarshal(raw,&doc);err!=nil{return nil,err}
 if doc.Asset.Version!="2.0"||len(doc.Nodes)<30||len(doc.Animations)!=1{return nil,errors.New("unexpected glTF schema or animation count")}
 names:=map[string]int{}
 parent:=map[int]int{}
 for i,n:=range doc.Nodes{
  if n.Name!=""{if _,ok:=names[n.Name];ok{return nil,fmt.Errorf("duplicate source node %q",n.Name)};names[n.Name]=i}
  for _,c:=range n.Children{
   if c<0||c>=len(doc.Nodes)||c==i{return nil,errors.New("invalid child index")}
   if _,ok:=parent[c];ok{return nil,errors.New("multiple node parents")}
   parent[c]=i
  }
 }
 for i:=range doc.Nodes{
  seen:=map[int]bool{}
  for j:=i;;{
   if seen[j]{return nil,errors.New("rig graph cycle")}
   seen[j]=true
   p,ok:=parent[j];if !ok{break};j=p
  }
 }
 animated:=map[string]bool{}
 for _,c:=range doc.Animations[0].Channels{
  if c.Target.Node<0||c.Target.Node>=len(doc.Nodes){return nil,errors.New("out-of-range animated joint")}
  if c.Target.Path!="rotation"&&c.Target.Path!="translation"&&c.Target.Path!="scale"{return nil,errors.New("unsupported animation path")}
  key:=fmt.Sprintf("%d:%s",c.Target.Node,c.Target.Path)
  if animated[key]{return nil,errors.New("duplicate joint animation channel")}
  animated[key]=true
 }
 require:=func(name,expectedParent,path string)error{
  id,ok:=names[name];if !ok{return fmt.Errorf("missing node %q",name)}
  if expectedParent!=""{p,ok:=names[expectedParent];if !ok||parent[id]!=p{return fmt.Errorf("wrong parent for %q",name)}}
  if path!=""&&!animated[fmt.Sprintf("%d:%s",id,path)]{return fmt.Errorf("missing %s animation for %q",path,name)}
  return nil
 }
 for a:=1;a<=2;a++{
  p:=fmt.Sprintf("fauna/buffalo-%02d",a);root:=p+"/root"
  if err:=require(root,"","translation");err!=nil{return nil,err}
  if err:=require(p+"/head-pivot",root,"rotation");err!=nil{return nil,err}
  for i:=0;i<2;i++{for j:=0;j<2;j++{
   leg:=fmt.Sprintf("%s/leg-%d-%d-pivot",p,i,j)
   hoof:=fmt.Sprintf("%s/hoof-%d-%d",p,i,j)
   if err:=require(leg,root,"rotation");err!=nil{return nil,err}
   if err:=require(hoof,leg,"");err!=nil{return nil,err}
  }}
 }
 for a:=1;a<=4;a++{
  p:=fmt.Sprintf("fauna/egret-%02d",a);root:=p+"/root"
  if err:=require(root,"","translation");err!=nil{return nil,err}
  if err:=require(p+"/head-pivot",root,"rotation");err!=nil{return nil,err}
  for i:=0;i<2;i++{
   leg:=fmt.Sprintf("%s/leg-%d",p,i)
   toe:=fmt.Sprintf("%s/toes-%d",p,i)
   if err:=require(leg,root,"rotation");err!=nil{return nil,err}
   if err:=require(toe,leg,"");err!=nil{return nil,err}
  }
 }
 return map[string]any{
  "schema":"scp.fauna.source-rig-inventory.v1",
  "source_gltf_json_sha256":sha(raw),
  "source_type":"ORIGINAL_LOW_POLY_GLTF_RIG_ONLY",
  "buffalo":2,"egrets":4,"buffalo_leg_pivots":8,"buffalo_hooves":8,
  "egret_leg_pivots":8,"egret_toes":8,"animated_leg_joints":16,"animated_roots":6,
  "qualification":"RIG_GRAPH_AND_ANIMATION_CHANNELS_ONLY",
  "limitations":"no ground-contact samples, foot penetration/slip, joint angle limits or real anatomy calibrated",
 },nil
}

type sample struct{ Time,X,Y,Clearance float64 }
type result struct{ PlantedTransitions int; MaxSlipSpeed,MaxPenetration float64 }
func contact(samples []sample)(result,error){
 var out result
 if len(samples)<2||len(samples)>5000{return out,errors.New("invalid sample count")}
 for i,s:=range samples{
  for _,v:=range []float64{s.Time,s.X,s.Y,s.Clearance}{if math.IsNaN(v)||math.IsInf(v,0)||math.Abs(v)>10000{return out,errors.New("nonfinite or unbounded sample")}}
  if s.Clearance<0{out.MaxPenetration=math.Max(out.MaxPenetration,-s.Clearance)}
  if i==0{continue}
  p:=samples[i-1]
  dt:=s.Time-p.Time
  if dt<=0||dt>1{return out,errors.New("invalid sample time interval")}
  if math.Abs(p.Clearance)<=.03&&math.Abs(s.Clearance)<=.03{
   out.PlantedTransitions++
   v:=math.Hypot(s.X-p.X,s.Y-p.Y)/dt
   out.MaxSlipSpeed=math.Max(out.MaxSlipSpeed,v)
  }
 }
 return out,nil
}
func main(){
 path:=flag.String("input","","Go scene .gltf JSON path")
 flag.Parse()
 if *path==""{fmt.Fprintln(os.Stderr,"-input required");os.Exit(2)}
 raw,err:=os.ReadFile(*path);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 data,err:=inventory(raw);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ");if err:=encoder.Encode(data);err!=nil{os.Exit(1)}
}
