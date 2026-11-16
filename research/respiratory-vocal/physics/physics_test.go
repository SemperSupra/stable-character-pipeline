package physics
import("math";"testing"
"github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior")
func cfg()Config{return Config{ReferenceVolumeM3:.003,InitialVolumeM3:.003,MinimumVolumeM3:.001,MaximumVolumeM3:.006,ComplianceM3PerPa:1e-5,NasalResistancePaSPerM3:2e7,OralResistancePaSPerM3:3e7,PortResistancePaSPerM3:4e7}}
func frame(start,end int,phase behavior.Phase,route behavior.Route,qn,qo,qp float64)behavior.Frame{
 f:=behavior.Frame{StartSample:start,EndSample:end,Phase:phase,Route:route,NasalFlowM3S:qn,OralFlowM3S:qo,ObjectFlowM3S:qp,TotalFlowM3S:qn+qo+qp,VelumOpen:qn!=0,MouthFreeOpening:qo!=0,DevicePort:behavior.NoPort}
 if qp!=0{f.DevicePort=behavior.Straw};return f
}
func perf(action behavior.Action,fs ...behavior.Frame)behavior.Performance{
 return behavior.Performance{Schema:behavior.Schema,Classification:behavior.Classification,Action:action,SampleRateHz:behavior.Rate,Frames:fs}
}
func near(a,b float64)bool{return math.Abs(a-b)<1e-10*math.Max(1,math.Max(math.Abs(a),math.Abs(b)))}
func TestSignedFlowConservationVolumeAndEnergy(t *testing.T){
 out:=frame(0,24000,behavior.Expiration,behavior.Oral,0,.0001,0)
 in:=frame(24000,48000,behavior.Inspiration,behavior.Oral,0,-.0001,0)
 got,e:=Integrate(perf(behavior.QuietBreath,out,in),cfg());if e!=nil{t.Fatal(e)}
 if len(got.Frames)!=2||!near(got.FinalVolumeM3,got.InitialVolumeM3)||math.Abs(got.NetOutflowVolumeM3)>1e-13{t.Fatalf("cycle not conservative: %+v",got)}
 if got.ResistiveLossJ<=0||!near(got.ExternalDriveWorkJ,got.ResistiveLossJ+got.StoredEnergyChangeJ)||got.MaxAbsEnergyResidualJ>1e-10{t.Fatalf("energy inconsistent: %+v",got)}
 if !(got.Frames[0].FinalVolumeM3<got.Frames[0].InitialVolumeM3&&got.Frames[1].FinalVolumeM3>got.Frames[1].InitialVolumeM3){t.Fatal("flow direction reversed")}
}
func TestParallelNasalOralPressureConsistency(t *testing.T){
 f:=frame(0,4800,behavior.Expiration,behavior.Mixed,6e-5,4e-5,0)
 got,e:=Integrate(perf(behavior.QuietBreath,f),cfg());if e!=nil{t.Fatal(e)}
 if !near(got.Frames[0].ResistiveEquivalentPressurePa,1200){t.Fatal(got.Frames[0])}
 f.OralFlowM3S=6e-5;f.TotalFlowM3S=1.2e-4
 if _,e:=Integrate(perf(behavior.QuietBreath,f),cfg());e==nil{t.Fatal("parallel pressure mismatch admitted")}
}
func TestNonPulmonaryClickAndSuction(t *testing.T){
 click:=frame(0,2400,behavior.Pause,behavior.Closed,0,0,0)
 click.Sources=[]behavior.Source{{Kind:behavior.ArticulatoryClick,Amplitude:.5}}
 a,e:=Integrate(perf(behavior.Beatbox,click),cfg());if e!=nil{t.Fatal(e)}
 if a.ResistiveLossJ!=0||a.ExternalDriveWorkJ!=0||a.FinalVolumeM3!=a.InitialVolumeM3{t.Fatalf("click used pulmonary air: %+v",a)}
 straw:=frame(0,2400,behavior.Inspiration,behavior.ObjectRoute,0,0,-.0001)
 a,e=Integrate(perf(behavior.StrawSuction,straw),cfg());if e!=nil{t.Fatal(e)}
 if a.FinalVolumeM3<=a.InitialVolumeM3{t.Fatal("suction direction wrong")}
}
func TestNegativeMathAndReservoirBounds(t *testing.T){
 p:=perf(behavior.QuietBreath,frame(0,4800,behavior.Expiration,behavior.Oral,0,.0001,0))
 bad:=[]Config{}
 c:=cfg();c.ComplianceM3PerPa=0;bad=append(bad,c)
 c=cfg();c.NasalResistancePaSPerM3=math.NaN();bad=append(bad,c)
 c=cfg();c.OralResistancePaSPerM3=-1;bad=append(bad,c)
 c=cfg();c.InitialVolumeM3=c.MaximumVolumeM3+.01;bad=append(bad,c)
 for i,c:=range bad{if _,e:=Integrate(p,c);e==nil{t.Fatalf("invalid config %d admitted",i)}}
 c=cfg();c.InitialVolumeM3=c.MinimumVolumeM3
 if _,e:=Integrate(perf(behavior.QuietBreath,frame(0,4800,behavior.Expiration,behavior.Oral,0,.005,0)),c);e==nil{t.Fatal("negative reservoir volume admitted")}
 p.Classification="PRIVATE_FINAL_CHARACTER_VOICE"
 if _,e:=Integrate(p,cfg());e==nil{t.Fatal("private data admitted to synthetic model")}
}
