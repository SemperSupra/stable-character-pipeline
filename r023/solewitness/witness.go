// Package solewitness is a source-safe falsifier for per-tick minimum-sole
// claims. It cannot authenticate the upstream Blender extractor or rights.
package solewitness

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math"
)

type V3 [3]float64
type Ground struct {
 Normal V3 `json:"unit_normal"`
 Offset float64 `json:"plane_offset"`
 MetresPerUnit float64 `json:"metres_per_unit"`
}
type Vertex struct {
 Index int `json:"index"`
 Position V3 `json:"position_world"`
}
type Tick struct {
 Index int `json:"quarter_tick"`
 Left []Vertex `json:"left_evaluated_sole"`
 Right []Vertex `json:"right_evaluated_sole"`
 ClaimedLeftIndex int `json:"claimed_left_min_index"`
 ClaimedRightIndex int `json:"claimed_right_min_index"`
 ClaimedLeftHeightM float64 `json:"claimed_left_min_height_m"`
 ClaimedRightHeightM float64 `json:"claimed_right_min_height_m"`
}
type Witness struct {
 Schema string `json:"schema"`
 SceneSHA256 string `json:"scene_sha256"`
 EvaluatedMeshSHA256 string `json:"evaluated_mesh_sha256"`
 Ground Ground `json:"ground"`
 Ticks []Tick `json:"ticks"`
}
type Result struct {
 Status string `json:"status"`
 TickCount int `json:"ticks_checked"`
 MinLeftM float64 `json:"min_left_m"`
 MinRightM float64 `json:"min_right_m"`
 MaxLeftM float64 `json:"max_left_m"`
 MaxRightM float64 `json:"max_right_m"`
}
func finite(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x,0) }
func validSHA(s string) bool { b,e:=hex.DecodeString(s); return len(s)==64&&e==nil&&len(b)==sha256.Size }
func norm2(v V3) float64 { return v[0]*v[0]+v[1]*v[1]+v[2]*v[2] }
func height(v V3,g Ground) float64 {
 return ((v[0]*g.Normal[0]+v[1]*g.Normal[1]+v[2]*g.Normal[2])-g.Offset)*g.MetresPerUnit
}
// minSole checks a complete supplied vertex collection. Ties resolve to the
// smallest vertex index. The independent source extraction must attest that
// these are ALL evaluated sole vertices: a truncated list is not detectable here.
func minSole(vertices []Vertex,g Ground)(int,float64,error) {
 if len(vertices)==0 {return 0,0,errors.New("missing evaluated sole vertices")}
 seen:=map[int]bool{}
 bestIndex:=-1
 bestHeight:=math.Inf(1)
 for _,v:=range vertices {
  if v.Index<0||seen[v.Index] {return 0,0,errors.New("invalid/duplicate vertex index")}
  seen[v.Index]=true
  for _,c:=range v.Position {if !finite(c){return 0,0,errors.New("nonfinite evaluated vertex")}}
  h:=height(v.Position,g)
  if !finite(h){return 0,0,errors.New("nonfinite evaluated height")}
  if h<bestHeight-1e-12 || (math.Abs(h-bestHeight)<=1e-12 && (bestIndex<0||v.Index<bestIndex)) {
   bestHeight=h;bestIndex=v.Index
  }
 }
 return bestIndex,bestHeight,nil
}
func Validate(w Witness)(Result,error) {
 r:=Result{Status:"REJECT_OR_UNQUALIFIED_SOURCE"}
 if w.Schema!="r023.evaluated_sole_synthetic.v1"||!validSHA(w.SceneSHA256)||!validSHA(w.EvaluatedMeshSHA256){
  return r,errors.New("missing schema or pinned input hashes")
 }
 g:=w.Ground
 for _,v:=range g.Normal {if !finite(v){return r,errors.New("nonfinite ground normal")}}
 if !finite(g.Offset)||!finite(g.MetresPerUnit)||g.MetresPerUnit<=0||math.Abs(norm2(g.Normal)-1)>1e-7 {
  return r,errors.New("invalid ground plane or units")
 }
 if len(w.Ticks)!=285 {return r,errors.New("expected exact 72-frame/285 quarter-tick sequence")}
 r.MinLeftM=math.Inf(1);r.MinRightM=math.Inf(1)
 r.MaxLeftM=math.Inf(-1);r.MaxRightM=math.Inf(-1)
 for i,t:=range w.Ticks {
  if t.Index!=i {return r,fmt.Errorf("missing/reordered tick %d",i)}
  left,lh,e:=minSole(t.Left,g);if e!=nil{return r,fmt.Errorf("tick %d left: %w",i,e)}
  right,rh,e:=minSole(t.Right,g);if e!=nil{return r,fmt.Errorf("tick %d right: %w",i,e)}
  if !finite(t.ClaimedLeftHeightM)||!finite(t.ClaimedRightHeightM)||
    left!=t.ClaimedLeftIndex||right!=t.ClaimedRightIndex||
    math.Abs(lh-t.ClaimedLeftHeightM)>1e-9||math.Abs(rh-t.ClaimedRightHeightM)>1e-9 {
   return r,fmt.Errorf("tick %d claimed minimum not supported by evaluated sole list",i)
  }
  r.MinLeftM=math.Min(r.MinLeftM,lh);r.MaxLeftM=math.Max(r.MaxLeftM,lh)
  r.MinRightM=math.Min(r.MinRightM,rh);r.MaxRightM=math.Max(r.MaxRightM,rh)
 }
 r.TickCount=len(w.Ticks)
 r.Status="PASS_SUPPLIED_VERTEX_MINIMA_ONLY__EXTRACTION_AND_PHYSICAL_CONTACT_UNVERIFIED"
 return r,nil
}
func Digest(w Witness)(string,error) {
 b,e:=json.Marshal(w);if e!=nil{return "",e}
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:]),nil
}
