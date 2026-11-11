// Package repairtrial is a minimal deterministic corrective A/B research experiment.
// Its metrics are synthetic witnesses, not acceptance of realistic physics.
package repairtrial

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
)
type Frame struct{
 Time float64 `json:"time_s"`
 X float64 `json:"foot_x_m"`
 Y float64 `json:"foot_y_m"`
 Z float64 `json:"foot_z_m"`
 Contact *bool `json:"contact"`
}
type Track struct{Schema string `json:"schema"`;Frames []Frame `json:"frames"`}
type Measurement struct{
 Status string `json:"status"`
 StancePeakMS float64 `json:"stance_peak_m_s"`
 AnyPeakMS float64 `json:"motion_peak_m_s"`
 StanceIntervals int `json:"stance_intervals"`
}
type Verdict struct{
 Schema string `json:"schema"`
 SourceSHA256 string `json:"source_sha256"`
 CandidateSHA256 string `json:"candidate_sha256"`
 Result string `json:"result"`
 Baseline Measurement `json:"baseline"`
 Candidate Measurement `json:"candidate"`
 Findings []string `json:"findings"`
 ChangedFrames []int `json:"changed_frames"`
 Limitations []string `json:"limitations"`
}
func digest(t Track)string{b,_:=json.Marshal(t);h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func good(t Track)bool{
 if t.Schema!="scp.synthetic-contact-track.v1"||len(t.Frames)<4{return false}
 for i,f:=range t.Frames{
  if f.Contact==nil{return false}
  for _,v:=range []float64{f.Time,f.X,f.Y,f.Z}{if math.IsNaN(v)||math.IsInf(v,0){return false}}
  if i>0&&f.Time<=t.Frames[i-1].Time{return false}
 }
 return true
}
func Measure(t Track)Measurement{
 m:=Measurement{Status:"UNKNOWN"};if !good(t){return m}
 for i:=1;i<len(t.Frames);i++{
  a,b:=t.Frames[i-1],t.Frames[i]
  v:=math.Hypot(b.X-a.X,b.Y-a.Y)/(b.Time-a.Time)
  if v>m.AnyPeakMS{m.AnyPeakMS=v}
  if *a.Contact&&*b.Contact{
   m.StanceIntervals++;if v>m.StancePeakMS{m.StancePeakMS=v}
  }
 }
 if m.StanceIntervals==0{return m}
 if m.StancePeakMS>0.03{m.Status="FAIL"}else{m.Status="PASS"}
 return m
}
func LockStance(b Track)(Track,error){
 if !good(b){return Track{},errors.New("untrusted or incomplete motion evidence")}
 c:=Track{Schema:b.Schema,Frames:append([]Frame(nil),b.Frames...)}
 var sx,sy float64
 inStance:=false
 for i,f:=range b.Frames{
  if *f.Contact{
   if !inStance{sx,sy=f.X,f.Y;inStance=true}
   c.Frames[i].X=sx;c.Frames[i].Y=sy
  }else{inStance=false}
 }
 return c,nil
}
func Compare(b,c Track)Verdict{
 v:=Verdict{Schema:"scp.repair-ab-v1",SourceSHA256:digest(b),CandidateSHA256:digest(c),Result:"REJECT",Findings:[]string{},ChangedFrames:[]int{},Limitations:[]string{"Synthetic kinematics only; no anatomy, torque, balance, skin or video-pixel verification","Stance labels and coordinates are input assumptions; reviewer must verify native-scene provenance"}}
 v.Baseline=Measure(b);v.Candidate=Measure(c)
 if !good(b)||!good(c)||len(b.Frames)!=len(c.Frames){v.Findings=append(v.Findings,"UNTRUSTED_OR_MISSING_INPUT");return v}
 for i,a:=range b.Frames{
  x:=c.Frames[i]
  if a.Time!=x.Time||*a.Contact!=*x.Contact||math.Abs(a.Z-x.Z)>1e-9{
   v.Findings=append(v.Findings,"INVARIANT_MODIFIED");return v
  }
  if math.Hypot(a.X-x.X,a.Y-x.Y)>1e-9{
   v.ChangedFrames=append(v.ChangedFrames,i)
   if !*a.Contact{v.Findings=append(v.Findings,"SWING_OR_UNRELATED_MOTION_CHANGED");return v}
  }
 }
 if v.Baseline.Status!="FAIL"{v.Findings=append(v.Findings,"BASELINE_NOT_PROVEN_DEFECTIVE");return v}
 if v.Candidate.Status!="PASS"{v.Findings=append(v.Findings,"CONTACT_REPAIR_NOT_EFFECTIVE");return v}
 if v.Candidate.AnyPeakMS>2.5{v.Findings=append(v.Findings,"REPAIR_CREATES_UNSAFE_TRANSITION");return v}
 if len(v.ChangedFrames)==0{v.Findings=append(v.Findings,"NO_CORRECTIVE_CHANGE");return v}
 v.Result="PROVISIONAL_IMPROVEMENT"
 v.Findings=append(v.Findings,"FOOT_SLIDING_REDUCED_WITHOUT_SWING_REGRESSION")
 return v
}