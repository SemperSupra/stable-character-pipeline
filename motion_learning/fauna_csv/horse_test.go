package fauna_csv

import (
 "bytes"
 "math"
 "os"
 "strings"
 "testing"
)
func input(t *testing.T) []byte{
 t.Helper()
 raw,err:=os.ReadFile("testdata/original.synthetic-horse.csv")
 if err!=nil{t.Fatal(err)}
 return raw
}
func TestOriginalSyntheticSourceAndEvidenceScopes(t *testing.T){
 raw:=input(t)
 o,err:=Parse(raw,"synthetic:horse1:m1:walk1","synthetic:horse1:session-a")
 if err!=nil{t.Fatal(err)}
 if o.Admission!="NOT_ADMITTED"||o.Status!="PASS_SYNTHETIC_CSV_STRUCTURE_ONLY"||
 o.CoordinateUnits!="arbitrary_source_unit"||o.PhysicalMetersPerUnit!=nil||
 o.NativeFPS!="UNKNOWN"||o.RelativeOrGlobal!="UNKNOWN"||
 o.MeasuredPhysicalContact||o.IndependentlyObservedFloor||o.InferredGlobalRoot {
  t.Fatalf("unsupported physical, rights or contact promotion %+v",o)
 }
 if o.SourceSHA256!=Digest(raw)||len(o.Frames)!=4||o.Frames[2].Index!=2||
 o.MarkerOrder!=Labels||math.Abs(o.Frames[1].TimeSourceSeconds-.025)>1e-10{
  t.Fatal("lost source/hash/time/marker provenance")
 }
 s,err:=Falsify(o,raw,[]float64{.08,.12,.20})
 if err!=nil{t.Fatal(err)}
 if s.GroundTruthEstablished||s.ContactSource!="HEURISTIC_FROM_SYNTHETIC_HOOF_Z"||
 len(s.Trials)!=3||s.ChangedDecisions<1{
  t.Fatalf("threshold perturbation did not reveal observable heuristic instability: %+v",s)
 }
 if s.Trials[0].AssignedCount>=s.Trials[1].AssignedCount||
 s.Trials[1].AssignedCount>=s.Trials[2].AssignedCount {t.Fatal("monotonic threshold oracle regressed")}
}
func TestCSVAndProvenanceMutationKill(t *testing.T){
 raw:=input(t)
 type caseSpec struct{name string; mutate func(string)string}
 cases:=[]caseSpec{
  {"missing synthetic marker",func(s string)string{return strings.Replace(s,Header,"HORSE_REAL_DATA",1)}},
  {"unknown timestamp type",func(s string)string{return strings.Replace(s,"timestamp_s","timestamp_ms",1)}},
  {"wrong marker",func(s string)string{return strings.Replace(s,"hfl_x","unknown_x",1)}},
  {"duplicate column",func(s string)string{return strings.Replace(s,"hfr_y","hfl_y",1)}},
  {"unbounded source position",func(s string)string{return strings.Replace(s,"1,0,0.8","1000001,0,0.8",1)}},
  {"negative timestamp",func(s string)string{return strings.Replace(s,"1,0.025,","1,-0.025,",1)}},
  {"duplicate timestamp",func(s string)string{return strings.Replace(s,"1,0.025,","1,0,",1)}},
  {"duplicate frame",func(s string)string{return strings.Replace(s,"1,0.025,","0,0.025,",1)}},
  {"missing frame",func(s string)string{return strings.Replace(s,"1,0.025,","3,0.025,",1)}},
  {"bad numeric",func(s string)string{return strings.Replace(s,"1,0.025,","1,NaN,",1)}},
  {"infinite coordinate",func(s string)string{return strings.Replace(s,"1,0.025,","1,0.025,Inf,",1)}},
  {"missing column",func(s string)string{return strings.Replace(s,"1,0.025,1.1,","1,0.025,",1)}},
  {"extra column",func(s string)string{return strings.Replace(s,"1,0.025,","1,0.025,12,",1)}},
  {"truncated motion",func(s string)string{return strings.Join(strings.Split(s,"\n")[:3],"\n")}},
 }
 for _,c:=range cases {t.Run(c.name,func(t *testing.T){
  tampered:=[]byte(c.mutate(string(raw)))
  if bytes.Equal(tampered,raw){t.Fatal("mutation did not alter actual bytes")}
  if _,err:=Parse(tampered,"synthetic:horse1","synthetic:session1");err==nil{
   t.Fatal("malformed source accepted")
  }
 })}
}
func TestFailClosedSensitivityInputs(t *testing.T){
 raw:=input(t);o,err:=Parse(raw,"synthetic:horse1","synthetic:session1");if err!=nil{t.Fatal(err)}
 cases:=[][]float64{{0.1},{.2,.1},{.1,.1},{.1,math.NaN()},{-.1,.2},{.1,math.Inf(1)}}
 for i,x:=range cases{if _,err:=Falsify(o,raw,x);err==nil{t.Fatalf("invalid threshold %d accepted",i)}}
 mutated:=append(bytes.Clone(raw),byte('X'))
 if _,err:=Falsify(o,mutated,[]float64{.1,.2});err==nil {t.Fatal("changed source hash accepted")}
 o.Frames[0].Landmarks[3][2]=999
 if _,err:=Falsify(o,raw,[]float64{.1,.2});err==nil {t.Fatal("forged observation hidden behind matching source hash")}
 o,err=Parse(raw,"synthetic:horse1","synthetic:session1");if err!=nil{t.Fatal(err)}
 o.MeasuredPhysicalContact=true
 if _,err:=Falsify(o,raw,[]float64{.1,.2});err==nil {t.Fatal("heuristic promoted to measured")}
}
func TestHorseSessionRecordingAndDerivativeSplitLeakage(t *testing.T){
 base:=[]SplitRecord{
  {SourceID:"M1walk1",HorseID:"Horse1",RecordingFamily:"Horse1-day1-sessionA",DerivativeFamily:"origin-walk1",MarkerSet:"M1",Split:"train"},
  {SourceID:"M2walk1-mirror",HorseID:"Horse1",RecordingFamily:"Horse1-day1-sessionA",DerivativeFamily:"origin-walk1",MarkerSet:"M2",Split:"train"},
  {SourceID:"Horse2walk1",HorseID:"Horse2",RecordingFamily:"Horse2-day2-sessionB",DerivativeFamily:"origin-walk2",MarkerSet:"M1",Split:"test"},
 }
 if err:=CheckSplit(base);err!=nil{t.Fatal(err)}
 bad:=append([]SplitRecord(nil),base...)
 bad[1].Split="validation"
 if err:=CheckSplit(bad);err==nil{t.Fatal("same horse/session leaked between splits")}
 bad=append([]SplitRecord(nil),base...)
 bad[1].HorseID="HorseOther"
 bad[1].RecordingFamily="renamed-session"
 bad[1].Split="validation"
 if err:=CheckSplit(bad);err==nil{t.Fatal("derivative family leaked under aliases")}
 bad=append([]SplitRecord(nil),base...)
 bad[1].SourceID=bad[0].SourceID
 if err:=CheckSplit(bad);err==nil{t.Fatal("duplicate source ID accepted")}
}
