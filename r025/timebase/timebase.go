// Package timebase provides source-safe diagnostics for a doubled frame-index
// motion import. It cannot certify a real Blender action, source, or clip.
package timebase

import ("errors";"fmt";"math")
type Key struct { Frame, Value, LeftHandleX, RightHandleX float64 }
type Slot struct { ID string; Curves [][]Key }
type Plan struct {
 SourceSHA string
 FPS int
 SourceFrames int
 SceneStart, SceneEnd int
 Slots []Slot
}
type Finding struct { Status string; Curves,Keys int; ObservedStride float64; RetimeFactor float64 }
func finite(f float64)bool{return !math.IsNaN(f)&&!math.IsInf(f,0)}
func hash(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func Inspect(p Plan)(Finding,error){
 r:=Finding{Status:"UNQUALIFIED_TIMEBASE"}
 if !hash(p.SourceSHA)||p.FPS!=12||p.SourceFrames!=72||p.SceneStart!=0||p.SceneEnd!=71||len(p.Slots)!=2{
  return r,errors.New("missing pinned source or unexpected clock/slot dimensions")
 }
 seen:=map[string]bool{}
 stride:=-1.0
 for _,slot:=range p.Slots{
  if slot.ID==""||seen[slot.ID]||len(slot.Curves)!=126{return r,errors.New("missing or duplicate action slot/curve")}
  seen[slot.ID]=true
  for _,curve:=range slot.Curves{
   if len(curve)!=p.SourceFrames{return r,errors.New("incomplete imported frame census")}
   for i,k:=range curve{
    if !finite(k.Frame)||!finite(k.Value)||!finite(k.LeftHandleX)||!finite(k.RightHandleX){
     return r,errors.New("nonfinite keyframe or handle")
    }
    if i>0{
     d:=k.Frame-curve[i-1].Frame
     if d<=0{return r,fmt.Errorf("non-increasing key at %d",i)}
     if stride<0{stride=d}
     if math.Abs(d-stride)>1e-8{return r,errors.New("inconsistent source-to-import clock stride")}
    }
   }
   if math.Abs(curve[0].Frame)>1e-8 || math.Abs(curve[len(curve)-1].Frame-stride*71)>1e-8{
    return r,errors.New("unaligned imported clock origin/end")
   }
   r.Curves++;r.Keys+=len(curve)
  }
 }
 r.ObservedStride=stride
 if math.Abs(stride-2)<1e-8{
  r.Status="RED_DOUBLE_FRAME_IMPORT__RETIME_DIAGNOSTIC_ONLY"
  r.RetimeFactor=.5
 }else if math.Abs(stride-1)<1e-8{
  r.Status="PASS_SYNTHETIC_FRAME_INDEX_ALIGNMENT_ONLY"
  r.RetimeFactor=1
 }else{
  return r,fmt.Errorf("unrecognized sample stride %.9g",stride)
 }
 return r,nil
}
// Retime returns a separate deep copy; source values are immutable.
// Frame coordinates AND Bezier handle X are transformed; handle Y/value remain.
func Retime(p Plan,factor float64)(Plan,error){
 f,e:=Inspect(p);if e!=nil{return Plan{},e}
 if f.Status!="RED_DOUBLE_FRAME_IMPORT__RETIME_DIAGNOSTIC_ONLY"||factor!=.5{
  return Plan{},errors.New("retime only admitted for exact doubled-frame diagnostic")
 }
 out:=p;out.Slots=make([]Slot,len(p.Slots))
 for si,s:=range p.Slots{
  out.Slots[si]=Slot{ID:s.ID,Curves:make([][]Key,len(s.Curves))}
  for ci,curve:=range s.Curves{
   copyCurve:=make([]Key,len(curve))
   for i,k:=range curve{
    k.Frame*=factor;k.LeftHandleX*=factor;k.RightHandleX*=factor
    copyCurve[i]=k
   }
   out.Slots[si].Curves[ci]=copyCurve
  }
 }
 result,e:=Inspect(out)
 if e!=nil||result.Status!="PASS_SYNTHETIC_FRAME_INDEX_ALIGNMENT_ONLY"{
  return Plan{},errors.New("post-retime 72-frame alignment failed")
 }
 return out,nil
}
