// Package temporal is source-safe motion timebase and critic-evidence qualification.
// A 2D projected track is not evidence of 3D contact, anatomy or physical realism.
package temporal

import (
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "errors"
  "math"
)
type Frame struct { Tick int64 `json:"tick"`; X float64 `json:"x"`; Y float64 `json:"y"` }
type Receipt struct {
 Status string `json:"status"`
 Count int `json:"count"`
 MeanPositionError float64 `json:"mean_position_error"`
 MaxPositionError float64 `json:"max_position_error"`
 SourcePathLength float64 `json:"source_path_length"`
 TargetPathLength float64 `json:"target_path_length"`
}
func finite(v float64) bool {return !math.IsNaN(v)&&!math.IsInf(v,0)}
func Audit(src,dst []Frame) Receipt {
 r:=Receipt{Status:"UNKNOWN", Count:len(src)}
 if len(src)<3||len(dst)!=len(src){r.Status="INSUFFICIENT_OR_UNMATCHED_FRAMES";return r}
 for i:=range src {
  a,b:=src[i],dst[i]
  if !finite(a.X)||!finite(a.Y)||!finite(b.X)||!finite(b.Y) {r.Status="NONFINITE";return r}
  if a.Tick!=b.Tick || (i>0&&(a.Tick<=src[i-1].Tick||b.Tick<=dst[i-1].Tick)){r.Status="CLOCK_MISMATCH";return r}
  d:=math.Hypot(a.X-b.X,a.Y-b.Y);r.MeanPositionError+=d;r.MaxPositionError=math.Max(r.MaxPositionError,d)
  if i>0 {r.SourcePathLength+=math.Hypot(a.X-src[i-1].X,a.Y-src[i-1].Y);r.TargetPathLength+=math.Hypot(b.X-dst[i-1].X,b.Y-dst[i-1].Y)}
 }
 r.MeanPositionError/=float64(r.Count)
 if r.SourcePathLength>=0.1&&r.TargetPathLength<1e-8{r.Status="FROZEN_TARGET";return r}
 if r.MaxPositionError>0.005 {r.Status="MOTION_MISMATCH";return r}
 r.Status="MATCHED_PROJECTED_2D_ONLY"
 return r
}
type ClaimedVisualFinding struct {
 ModelID string `json:"model_id"`
 Status string `json:"status"`
 SourceSHA256 string `json:"source_sha256"`
 TargetSHA256 string `json:"target_sha256"`
 CameraID string `json:"camera_id"`
 FirstTick int64 `json:"first_tick"`
 LastTick int64 `json:"last_tick"`
 Confidence float64 `json:"confidence"`
}
func DigestFrames(frames []Frame) (string,error) {b,e:=json.Marshal(frames);if e!=nil{return "",e};s:=sha256.Sum256(b);return hex.EncodeToString(s[:]),nil}
func Adjudicate(r Receipt,src,dst []Frame,f ClaimedVisualFinding)(string,error) {
 a,e:=DigestFrames(src);if e!=nil{return "",e}
 b,e:=DigestFrames(dst);if e!=nil{return "",e}
 if f.SourceSHA256!=a||f.TargetSHA256!=b||f.ModelID==""||f.CameraID=="" {return "EVIDENCE_MISMATCH",errors.New("unbound visual evidence")}
 if !finite(f.Confidence)||f.Confidence<0||f.Confidence>1||len(src)<3||len(dst)!=len(src)||f.FirstTick>=f.LastTick||f.FirstTick<src[0].Tick||f.LastTick>src[len(src)-1].Tick {return "INVALID_OBSERVATION",errors.New("no temporal grounding")}
 if r.Status!="MATCHED_PROJECTED_2D_ONLY"{return "NUMERIC_FAILURE_NOT_OVERRIDABLE",nil}
 if f.Status=="UNKNOWN" {return "ABSTAINED",nil}
 // Even perfect 2D alignment cannot prove human motion or 3D anatomy.
 return "VISUAL_CLAIM_NOT_3D_QUALIFIED",nil
}
func ResampleEven(src []Frame)([]Frame,error){
 if len(src)<5||len(src)%2==0{return nil,errors.New("need odd length source with 60fps ticks")}
 dst:=make([]Frame,0,(len(src)+1)/2)
 for i,f:=range src{if i>0&&f.Tick<=src[i-1].Tick{return nil,errors.New("nonmonotonic source clock")}
  if i%2==0{dst=append(dst,Frame{Tick:f.Tick/2,X:f.X,Y:f.Y})}
 }
 return dst,nil
}
