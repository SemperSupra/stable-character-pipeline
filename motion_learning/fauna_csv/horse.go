// Package fauna_csv qualifies only an original, synthetic seven-landmark CSV
// source format. Physical motion, ground contact, units, and data rights are NOT attested.
package fauna_csv

import (
 "bytes"
 "crypto/sha256"
 "encoding/csv"
 "encoding/hex"
 "errors"
 "fmt"
 "io"
 "math"
 "reflect"
 "strconv"
 "strings"
)

const (
 Schema = "scp.fauna.synthetic-seven-landmark-observation.v1"
 Header = "SCP_ORIGINAL_SYNTHETIC_HORSE_CSV_V1"
 MaxBytes = 1<<20
 Markers = 7
)
var Labels = [Markers]string{"Head","Withers","Sacrum","HFL","HFR","HHL","HHR"}
var FootIndices = [4]int{3,4,5,6}
type Vec3 [3]float64
type Frame struct {
 Index int `json:"index"`
 TimeSourceSeconds float64 `json:"time_source_seconds"`
 Landmarks [Markers]Vec3 `json:"landmarks_source_units"`
}
type Observation struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceState string `json:"source_state"`
 Admission string `json:"admission"`
 SourceSHA256 string `json:"source_sha256"`
 SourceID string `json:"source_id"`
 CaptureFamily string `json:"capture_family"`
 MarkerOrder [Markers]string `json:"marker_order"`
 CoordinateUnits string `json:"coordinate_units"`
 PhysicalMetersPerUnit *float64 `json:"physical_meters_per_unit"`
 RelativeOrGlobal string `json:"relative_or_global"`
 Frames []Frame `json:"frames"`
 NativeFPS string `json:"native_fps"`
 MeasuredPhysicalContact bool `json:"measured_physical_contact"`
 IndependentlyObservedFloor bool `json:"independently_observed_floor"`
 InferredGlobalRoot bool `json:"inferred_global_root"`
 Unknown []string `json:"unknown"`
}
type ThresholdTrial struct{
 ThresholdSourceUnits float64 `json:"threshold_source_units"`
 HeuristicBelowThreshold [][4]bool `json:"heuristic_below_threshold"`
 AssignedCount int `json:"assigned_count"`
}
type Sensitivity struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 ObservationSHA256 string `json:"observation_sha256"`
 Trials []ThresholdTrial `json:"trials"`
 ChangedDecisions int `json:"changed_decisions"`
 ContactSource string `json:"contact_source"`
 GroundTruthEstablished bool `json:"ground_truth_established"`
}
func Digest(b []byte) string {h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func expectedHeader() []string {
 h:=[]string{Header,"timestamp_s"}
 for _,n:=range Labels {
  low:=strings.ToLower(n)
  h=append(h,low+"_x",low+"_y",low+"_z")
 }
 return h
}
func number(s string)(float64,error){
 if strings.TrimSpace(s)!=s || s==""{return 0,errors.New("blank/whitespace numeric cell")}
 v,err:=strconv.ParseFloat(s,64)
 if err!=nil || math.IsNaN(v)||math.IsInf(v,0){return 0,errors.New("nonfinite/malformed numeric cell")}
 return v,nil
}
func Parse(original []byte,sourceID,captureFamily string)(Observation,error){
 var zero Observation
 if len(original)==0||len(original)>MaxBytes{return zero,errors.New("source exceeds bounded original fixture size")}
 if sourceID==""||captureFamily==""||strings.ContainsAny(sourceID," 	
")||strings.ContainsAny(captureFamily," 	
"){
  return zero,errors.New("source identity or capture group missing/ambiguous")
 }
 reader:=csv.NewReader(bytes.NewReader(original))
 reader.FieldsPerRecord=2+Markers*3
 reader.ReuseRecord=false
 reader.TrimLeadingSpace=false
 reader.LazyQuotes=false
 header,err:=reader.Read();if err!=nil{return zero,fmt.Errorf("header: %w",err)}
 expect:=expectedHeader()
 for i:=range expect {if header[i]!=expect[i]{return zero,fmt.Errorf("original synthetic fixture marker or column %d mismatch",i)}}
 rows:=[]Frame{}
 prevTime:=math.Inf(-1)
 for {
  rec,err:=reader.Read()
  if errors.Is(err,io.EOF){break}
  if err!=nil{return zero,fmt.Errorf("CSV parse: %w",err)}
  if len(rows)>=10000{return zero,errors.New("too many frames")}
  frameID,e:=strconv.Atoi(rec[0]);if e!=nil||frameID!=len(rows){return zero,errors.New("nonconsecutive source frame IDs")}
  time,e:=number(rec[1]);if e!=nil||time<0||time<=prevTime{return zero,errors.New("invalid or nonmonotonic source timestamp")}
  f:=Frame{Index:frameID,TimeSourceSeconds:time}
  for k:=0;k<Markers;k++{
   for a:=0;a<3;a++{
    v,e:=number(rec[2+3*k+a]);if e!=nil{return zero,fmt.Errorf("frame %d marker %d axis %d: %w",frameID,k,a,e)}
    if math.Abs(v)>1e6{return zero,errors.New("unbounded synthetic coordinate")}
    f.Landmarks[k][a]=v
   }
  }
  rows=append(rows,f);prevTime=time
 }
 if len(rows)<3{return zero,errors.New("at least three samples required for temporal falsification")}
 return Observation{
  Schema:Schema,Status:"PASS_SYNTHETIC_CSV_STRUCTURE_ONLY",
  SourceState:"ORIGINAL_SYNTHETIC",Admission:"NOT_ADMITTED",
  SourceSHA256:Digest(original),SourceID:sourceID,CaptureFamily:captureFamily,
  MarkerOrder:Labels,CoordinateUnits:"arbitrary_source_unit",
  PhysicalMetersPerUnit:nil,RelativeOrGlobal:"UNKNOWN",Frames:rows,NativeFPS:"UNKNOWN",
  MeasuredPhysicalContact:false,IndependentlyObservedFloor:false,InferredGlobalRoot:false,
  Unknown:[]string{"physical_scale","original_vhdc_axes","world_root","source_ground_plane",
   "observed_contact","true_frame_rate","original_dataset_rights","full_skeleton_hierarchy"},
 },nil
}
func Falsify(o Observation,raw []byte,thresholds []float64)(Sensitivity,error){
 var empty Sensitivity
 if o.Status!="PASS_SYNTHETIC_CSV_STRUCTURE_ONLY"||o.SourceState!="ORIGINAL_SYNTHETIC"||
  o.Admission!="NOT_ADMITTED"||o.SourceSHA256!=Digest(raw)||o.MeasuredPhysicalContact||
  o.PhysicalMetersPerUnit!=nil||o.InferredGlobalRoot||o.IndependentlyObservedFloor {
  return empty,errors.New("source ancestry or source/inference boundary violated")
 }
 // Reject forged observation rows even when an attacker reuses a genuine source SHA.
 canonical,err:=Parse(raw,o.SourceID,o.CaptureFamily)
 if err!=nil || !reflect.DeepEqual(canonical,o){return empty,errors.New("observation differs from independently reparsed immutable source bytes")}
 if len(thresholds)<2||len(thresholds)>12{return empty,errors.New("threshold count invalid")}
 result:=Sensitivity{Schema:"scp.fauna.threshold-falsification.v1",
  ObservationSHA256:o.SourceSHA256,Status:"PASS_SYNTHETIC_HEURISTIC_SENSITIVITY_ONLY",
  ContactSource:"HEURISTIC_FROM_SYNTHETIC_HOOF_Z",GroundTruthEstablished:false,
  Trials:[]ThresholdTrial{}}
 prev:=[4]bool{}
 for n,t:=range thresholds{
  if math.IsNaN(t)||math.IsInf(t,0)||t<0||t>1e6||(n>0&&t<=thresholds[n-1]){
   return empty,errors.New("thresholds must be finite, strictly increasing source-unit quantities")
  }
  trial:=ThresholdTrial{ThresholdSourceUnits:t,HeuristicBelowThreshold:make([][4]bool,0,len(o.Frames))}
  for k,f:=range o.Frames {
   state:=[4]bool{}
   for j,m:=range FootIndices{
    state[j]=f.Landmarks[m][2]<t
    if state[j]{trial.AssignedCount++}
    if n>0 {
     if state[j]!=result.Trials[n-1].HeuristicBelowThreshold[k][j]{result.ChangedDecisions++}
    }
   }
   trial.HeuristicBelowThreshold=append(trial.HeuristicBelowThreshold,state)
   prev=state
  }
  result.Trials=append(result.Trials,trial)
 }
 _=prev
 return result,nil
}
type SplitRecord struct{
 SourceID string `json:"source_id"`
 HorseID string `json:"horse_id"`
 RecordingFamily string `json:"recording_family"`
 DerivativeFamily string `json:"derivative_family"`
 MarkerSet string `json:"marker_set"`
 Split string `json:"split"`
}
func CheckSplit(records []SplitRecord)error{
 if len(records)==0{return errors.New("no recordings")}
 ids:=map[string]bool{}
 horse,recording,derived:=map[string]string{},map[string]string{},map[string]string{}
 for _,r:=range records{
  if r.SourceID==""||r.HorseID==""||r.RecordingFamily==""||
   r.DerivativeFamily==""||r.MarkerSet==""||ids[r.SourceID]{
   return errors.New("unknown, duplicated, or unproven source family")
  }
  if r.Split!="train"&&r.Split!="validation"&&r.Split!="test"{return errors.New("invalid split")}
  ids[r.SourceID]=true
  for _,p:=range []struct{m map[string]string;k string}{
   {horse,r.HorseID},{recording,r.RecordingFamily},{derived,r.DerivativeFamily},
  }{
   if old,ok:=p.m[p.k];ok&&old!=r.Split{return fmt.Errorf("horse/recording/derivative ancestry leakage for %s",r.SourceID)}
   p.m[p.k]=r.Split
  }
 }
 return nil
}
