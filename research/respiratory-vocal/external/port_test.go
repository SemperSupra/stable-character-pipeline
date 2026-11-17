package external

import (
 "math"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
func config(port behavior.Port) Config {
 c:=Config{Port:port,ResistancePaSPerM3:8e6}
 if port==behavior.Balloon {
  c.BalloonComplianceM3PerPa=1e-7
  c.InitialBalloonVolumeM3=.001
  c.BalloonCapacityM3=.01
 }
 return c
}
func closeEnough(a,b float64)bool{return math.Abs(a-b)<1e-10*math.Max(1,math.Abs(a)+math.Abs(b))}
func TestAllFiveOriginalExternalPortFamiliesPreservePassivity(t *testing.T) {
 cases:=[]struct{name string;port behavior.Port;sign int}{
  {"flute_jet",behavior.Flute,1},
  {"reed_instrument",behavior.Reed,1},
  {"external_whistle",behavior.ExternalWhistle,1},
  {"balloon_airflow",behavior.Balloon,1},
  {"straw_suction",behavior.Straw,-1},
 }
 originals:=preview.Fixtures()
 for _,tc:=range cases{
  p,ok:=originals[tc.name];if !ok{t.Fatal(tc.name+" fixture missing")}
  c:=config(tc.port)
  got,err:=Evaluate(p,c);if err!=nil{t.Fatalf("%s failed: %v",tc.name,err)}
  if got.Schema!="respiratory.external_port_passivity.v0"||
   got.Classification!=behavior.Classification||len(got.Frames)!=1||got.Port!=tc.port{
   t.Fatalf("unbound port result: %+v",got)
  }
  if float64(tc.sign)*got.SignedNetVolumeM3<=0||
   float64(tc.sign)*got.Frames[0].TotalPressureDropPa<=0{
   t.Fatalf("port flow vs pressure sign invalid: %+v",got)
  }
  if got.DissipatedEnergyJ<=0||got.MaxAbsEnergyResidualJ>1e-10||
   !closeEnough(got.SourceWorkJ,got.DissipatedEnergyJ+got.StoredEnergyChangeJ){
   t.Fatalf("passivity violation: %+v",got)
  }
  if tc.port==behavior.Balloon{
   if got.StoredEnergyChangeJ<=0||got.FinalBalloonVolumeM3<=c.InitialBalloonVolumeM3{
    t.Fatalf("balloon did not store elastic energy: %+v",got)
   }
  } else if got.StoredEnergyChangeJ!=0||got.FinalBalloonVolumeM3!=0{
   t.Fatalf("nonballoon object stored unmodeled energy: %+v",got)
  }
  // Identical source/event/state must have identical numerical receipts.
  again,err:=Evaluate(p,c)
  if err!=nil||got.SourceWorkJ!=again.SourceWorkJ||got.Frames[0]!=again.Frames[0]{
   t.Fatalf("nondeterministic port receipt: %v",err)
  }
 }
}
func TestBalloonPressureAndStoredEnergyRiseWithVolume(t *testing.T){
 p:=preview.Fixtures()["balloon_airflow"]
 second:=p.Frames[0]
 second.StartSample=24000;second.EndSample=48000
 p.Frames=append(p.Frames,second)
 got,err:=Evaluate(p,config(behavior.Balloon));if err!=nil{t.Fatal(err)}
 if len(got.Frames)!=2||
  !(got.Frames[1].ElasticPressureMidPa>got.Frames[0].ElasticPressureMidPa)||
  !(got.Frames[1].FinalBalloonVolumeM3>got.Frames[0].FinalBalloonVolumeM3)||
  !closeEnough(got.SourceWorkJ,got.DissipatedEnergyJ+got.StoredEnergyChangeJ){
  t.Fatalf("pressure not monotone or energy failed: %+v",got)
 }
}
func TestResistanceScalingAndInwardStrawWork(t *testing.T){
 p:=preview.Fixtures()["straw_suction"]
 c:=config(behavior.Straw)
 a,err:=Evaluate(p,c);if err!=nil{t.Fatal(err)}
 c.ResistancePaSPerM3*=2
 b,err:=Evaluate(p,c);if err!=nil{t.Fatal(err)}
 if !(a.Frames[0].TotalPressureDropPa<0)&&!(b.Frames[0].TotalPressureDropPa<0){
  t.Fatal("suction is incorrectly outward")
 }
 if !closeEnough(b.DissipatedEnergyJ,2*a.DissipatedEnergyJ)||
  !closeEnough(b.Frames[0].TotalPressureDropPa,2*a.Frames[0].TotalPressureDropPa){
  t.Fatalf("incorrect linear loss scaling %+v %+v",a,b)
 }
}
func TestInvalidCouplingCapacityAndParametersRejected(t *testing.T){
 cases:=[]struct{action string;c Config}{
  {"flute_jet",config(behavior.Straw)},
  {"nasal_quiet",config(behavior.Flute)},
  {"balloon_airflow",Config{Port:behavior.Balloon,ResistancePaSPerM3:8e6,BalloonComplianceM3PerPa:0,BalloonCapacityM3:.01}},
  {"balloon_airflow",Config{Port:behavior.Balloon,ResistancePaSPerM3:8e6,BalloonComplianceM3PerPa:1e-7,InitialBalloonVolumeM3:.0001,BalloonCapacityM3:.00015}},
 }
 fs:=preview.Fixtures()
 for _,tc:=range cases{
  if _,err:=Evaluate(fs[tc.action],tc.c);err==nil{t.Fatalf("invalid coupling accepted %+v",tc)}
 }
 c:=config(behavior.Flute);c.ResistancePaSPerM3=math.NaN()
 if _,err:=Evaluate(fs["flute_jet"],c);err==nil{t.Fatal("NaN resistance accepted")}
 c=config(behavior.Flute);c.ResistancePaSPerM3=-3
 if _,err:=Evaluate(fs["flute_jet"],c);err==nil{t.Fatal("negative passive resistance accepted")}
 c=config(behavior.Straw);c.BalloonComplianceM3PerPa=1e-7
 if _,err:=Evaluate(fs["straw_suction"],c);err==nil{t.Fatal("phantom stored energy on straw accepted")}
 private:=fs["flute_jet"];private.Classification="PRIVATE_FINAL_CHARACTER"
 if _,err:=Evaluate(private,config(behavior.Flute));err==nil{t.Fatal("private source admitted")}
}
