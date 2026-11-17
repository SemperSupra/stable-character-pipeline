package coupling

import(
 "bytes"
 "encoding/json"
 "math"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/physics"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
func config()Config{
 return Config{Mechanics:physics.Config{
  ReferenceVolumeM3:.003,InitialVolumeM3:.003,
  MinimumVolumeM3:.001,MaximumVolumeM3:.006,
  ComplianceM3PerPa:1e-5,
  NasalResistancePaSPerM3:2e7,OralResistancePaSPerM3:3e7,
  PortResistancePaSPerM3:4e7,
 },NormalizationLossJ:1}
}
func TestAllSeventeenOriginalSyntheticCasesAndOriginalUnchanged(t *testing.T){
 fixtures:=preview.Fixtures()
 if len(fixtures)!=17{t.Fatalf("source fixtures unexpectedly changed %d",len(fixtures))}
 unique:=map[string]string{}
 for name,p:=range fixtures{
  originalBytes,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
  before,baseline,err:=preview.Render(p);if err!=nil{t.Fatal(err)}
  wave,r,err:=Render(p,config());if err!=nil{t.Fatalf("%s coupling: %v",name,err)}
  if r.Schema!="respiratory.mechanics_audio_adapter.v0"||
   r.Validity!="uncalibrated_relative_mechanical_energy_gain_not_physical_audio_power"||
   r.Audio.SHA256==""||r.Mechanics.Schema!="respiratory.resistance_compliance.v0"||
   len(r.Frames)!=len(p.Frames) {
   t.Fatalf("%s invalid boundary/receipts %+v",name,r)
  }
  afterBytes,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
  if !bytes.Equal(originalBytes,afterBytes){t.Fatalf("%s input source was mutated",name)}
  after,afterReceipt,err:=preview.Render(p);if err!=nil{t.Fatal(err)}
  if !bytes.Equal(before,after)||baseline.SHA256!=afterReceipt.SHA256{
   t.Fatalf("%s altered original WAV generator/fixture",name)
  }
  replay,again,err:=Render(p,config())
  if err!=nil||!bytes.Equal(wave,replay)||again.Audio.SHA256!=r.Audio.SHA256{
   t.Fatalf("%s deterministic source/coupling replay failed: %v",name,err)
  }
  if r.Audio.Peak>=.99||r.Mechanics.MaxAbsEnergyResidualJ>1e-10{
   t.Fatalf("%s headroom or energy bounds violated",name)
  }
  if name=="no_flow_silence"{
   if r.Audio.RMS!=0||r.Audio.Peak!=0{t.Fatal("no source/flow emitted synthetic WAV")}
  }else if r.Audio.RMS==0{t.Fatalf("%s unexpectedly silent",name)}
  if prior,ok:=unique[r.Audio.SHA256];ok{t.Fatalf("%s and %s yielded identical adapted WAV",name,prior)}
  unique[r.Audio.SHA256]=name
 }
}
func TestPressureResistanceActuallyModulatesAudioAtFixedFlow(t *testing.T){
 p:=preview.Fixtures()["oral_quiet"]
 low:=config();low.Mechanics.OralResistancePaSPerM3=1e7
 high:=config();high.Mechanics.OralResistancePaSPerM3=2e7
 lowWave,a,e:=Render(p,low);if e!=nil{t.Fatal(e)}
 highWave,b,e:=Render(p,high);if e!=nil{t.Fatal(e)}
 if bytes.Equal(lowWave,highWave)||!(b.Audio.RMS>a.Audio.RMS)||
  !(b.Mechanics.ResistiveLossJ>a.Mechanics.ResistiveLossJ)||
  !(b.Frames[0].NormalizedAmplitudeGain>a.Frames[0].NormalizedAmplitudeGain){
  t.Fatalf("pressure path did not actually drive toy audio: low=%+v high=%+v",a,b)
 }
 if a.Frames[0].SignedFlowM3S!=b.Frames[0].SignedFlowM3S{t.Fatal("flow changed while only resistance changed")}
 if !(a.Audio.Peak>0&&b.Audio.Peak<.99){t.Fatal("adapted toy audio silent/overdriven")}
}
func TestNonPulmonaryClickDoesNotNeedPulmonaryEnergy(t *testing.T){
 p:=preview.Fixtures()["beatbox_nonpulmonary"]
 original,_,e:=preview.Render(p);if e!=nil{t.Fatal(e)}
 wave,r,e:=Render(p,config());if e!=nil{t.Fatal(e)}
 if !bytes.Equal(original,wave){t.Fatal("independent nonpulmonary click altered by zero lung drive")}
 if r.Mechanics.ResistiveLossJ!=0||r.Mechanics.NetOutflowVolumeM3!=0||
  r.Frames[0].NormalizedAmplitudeGain!=0||r.Frames[0].NonPulmonaryClicksRetained!=1{
  t.Fatalf("nonpulmonary beatbox used lung drive %+v",r)
 }
}
func TestBadPhysicsAndUnboundedGainRejected(t *testing.T){
 p:=preview.Fixtures()["humming"]
 cases:=[]Config{}
 x:=config();x.NormalizationLossJ=0;cases=append(cases,x)
 x=config();x.NormalizationLossJ=math.NaN();cases=append(cases,x)
 x=config();x.NormalizationLossJ=math.Inf(1);cases=append(cases,x)
 x=config();x.NormalizationLossJ=1e-20;cases=append(cases,x)
 x=config();x.Mechanics.OralResistancePaSPerM3=-1;cases=append(cases,x)
 x=config();x.Mechanics.InitialVolumeM3=x.Mechanics.MaximumVolumeM3+.01;cases=append(cases,x)
 for i,x:=range cases{if _,_,err:=Render(p,x);err==nil{t.Fatalf("invalid config %d accepted",i)}}
 p.Classification="PRIVATE_PERSONAL_VOICE"
 if _,_,e:=Render(p,config());e==nil{t.Fatal("private source admitted to public synthetic coupling")}
 p=preview.Fixtures()["straw_suction"]
 // Signed inspiratory branch remains valid; adaptation cannot turn
 // inward suction into outward pressure, or claim clinical thresholds.
 _,r,e:=Render(p,config());if e!=nil{t.Fatal(e)}
 if r.Frames[0].SignedFlowM3S>=0{t.Fatal("straw suction flow sign reversed")}
}
func TestNoImplicitEngineOrMedicalClaims(t *testing.T){
 _,r,e:=Render(preview.Fixtures()["oral_quiet"],config());if e!=nil{t.Fatal(e)}
 if r.Validity=="human_validated"||r.Audio.ModelValidity=="physical_vocal_v0"{
  t.Fatal("synthetic adapter falsely admitted full engine or clinical validity")
 }
 // Confirm the new adapter never overwrites prescribed source oscillators.
 p:=preview.Fixtures()["singing_two_notes"]
 before:=append([]behavior.Source(nil),p.Frames[0].Sources...)
 if _,_,e:=Render(p,config());e!=nil{t.Fatal(e)}
 if p.Frames[0].Sources[0]!=before[0]{t.Fatal("prescribed source pitch/amplitude mutated")}
}
