package behavior

import(
 "encoding/json"
 "math"
 "strings"
 "testing"
)

func baseline(phase Phase,route Route) Frame {
 f:=Frame{StartSample:0,EndSample:4800,Phase:phase,Route:route,DevicePort:NoPort}
 switch phase{
 case Inspiration:
  switch route{
  case Nasal:f.NasalFlowM3S=-1e-4;f.VelumOpen=true
  case Oral:f.OralFlowM3S=-1e-4;f.MouthFreeOpening=true
  case Mixed:f.NasalFlowM3S=-6e-5;f.OralFlowM3S=-4e-5;f.VelumOpen=true;f.MouthFreeOpening=true
  }
 case Expiration:
  switch route{
  case Nasal:f.NasalFlowM3S=1e-4;f.VelumOpen=true
  case Oral:f.OralFlowM3S=1e-4;f.MouthFreeOpening=true
  case Mixed:f.NasalFlowM3S=6e-5;f.OralFlowM3S=4e-5;f.VelumOpen=true;f.MouthFreeOpening=true
  }
 }
 f.TotalFlowM3S=f.NasalFlowM3S+f.OralFlowM3S
 return f
}
func fixture(a Action,f ...Frame)Performance {
 return Performance{Schema:Schema,Classification:Classification,Action:a,SampleRateHz:Rate,Frames:f}
}
func object(phase Phase,kind Port,src SourceKind,pitch float64)Frame{
 f:=baseline(phase,Closed)
 f.Phase=phase;f.Route=ObjectRoute;f.DevicePort=kind
 if phase==Expiration{f.ObjectFlowM3S=1e-4}else{f.ObjectFlowM3S=-1e-4}
 f.TotalFlowM3S=f.ObjectFlowM3S
 if src!=""{f.Sources=[]Source{{Kind:src,NominalHz:pitch,Amplitude:0.4}}}
 return f
}

func TestAllSoundFamiliesWithSourcePhysics(t *testing.T){
 nasal:=baseline(Inspiration,Nasal);nasal.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.2}}
 mouth:=baseline(Expiration,Oral);mouth.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.2}}
 mixed:=baseline(Inspiration,Mixed);mixed.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.2}}
 hum:=baseline(Expiration,Nasal);hum.Sources=[]Source{{Kind:GlottalVoiced,NominalHz:160,Amplitude:0.4}}
 sing:=baseline(Expiration,Oral);sing.Sources=[]Source{{Kind:GlottalVoiced,NominalHz:220,Amplitude:0.5}}
 whistle:=baseline(Expiration,Oral);whistle.Sources=[]Source{{Kind:LipWhistle,NominalHz:800,Amplitude:0.3}}
 beat:=baseline(Pause,Closed);beat.Sources=[]Source{{Kind:ArticulatoryClick,Amplitude:0.8}}
 pantOut:=baseline(Expiration,Oral);pantOut.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.5}}
 pantIn:=baseline(Inspiration,Oral);pantIn.StartSample=4800;pantIn.EndSample=9600;pantIn.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.5}}
 cry:=baseline(Expiration,Oral);cry.Sources=[]Source{{Kind:GlottalIrregular,NominalHz:190,Amplitude:0.7},{Kind:AirflowNoise,Amplitude:0.3}}
 laugh:=baseline(Expiration,Oral);laugh.Sources=[]Source{{Kind:GlottalVoiced,NominalHz:190,Amplitude:0.6},{Kind:AirflowNoise,Amplitude:0.2}}
 scream:=baseline(Expiration,Oral);scream.Sources=[]Source{{Kind:GlottalIrregular,NominalHz:510,Amplitude:0.6}}
 cases:=[]Performance{
  fixture(QuietBreath,nasal),fixture(QuietBreath,mouth),fixture(QuietBreath,mixed),
  fixture(DeepBreath,mouth),fixture(Pant,pantOut,pantIn),
  fixture(Hum,hum),fixture(Sing,sing),fixture(LipWhistleAction,whistle),fixture(Beatbox,beat),
  fixture(FlutePlay,object(Expiration,Flute,EdgeTone,650)),
  fixture(ReedPlay,object(Expiration,Reed,ReedTone,250)),
  fixture(BlowWhistle,object(Expiration,ExternalWhistle,EdgeTone,1100)),
  fixture(InflateBalloon,object(Expiration,Balloon,ElasticNoise,0)),
  fixture(StrawSuction,object(Inspiration,Straw,AirflowNoise,0)),
  fixture(Cry,cry),fixture(Laugh,laugh),fixture(Scream,scream),
 }
 for i,p:=range cases{
  if err:=p.Validate();err!=nil{t.Fatalf("valid physical control family %d %s: %v",i,p.Action,err)}
  b,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
  var decoded Performance
  if err:=json.Unmarshal(b,&decoded);err!=nil{t.Fatal(err)}
  if err:=decoded.Validate();err!=nil{t.Fatalf("serialized source failed %v",err)}
 }
}

func TestRejectContradictoryFlowPortAndExcitation(t *testing.T){
 baselineOut:=baseline(Expiration,Oral);baselineOut.Sources=[]Source{{Kind:AirflowNoise,Amplitude:0.2}}
 invalid:=[]Performance{}
 push:=func(f Frame){invalid=append(invalid,fixture(QuietBreath,f))}
 f:=baselineOut;f.TotalFlowM3S+=1e-3;push(f)
 f=baselineOut;f.Phase=Inspiration;push(f)
 f=baselineOut;f.Route=Nasal;push(f)
 f=baselineOut;f.MouthFreeOpening=false;push(f)
 f=baselineOut;f.OralFlowM3S=math.NaN();push(f)
 f=baselineOut;f.OralFlowM3S=math.Inf(1);push(f)
 f=baselineOut;f.DevicePort=Flute;push(f)
 f=baselineOut;f.Sources=[]Source{{Kind:EdgeTone,NominalHz:600,Amplitude:0.5}};push(f)
 f=baselineOut;f.Sources=[]Source{{Kind:LipWhistle,NominalHz:0,Amplitude:0.5}};push(f)
 f=baselineOut;f.Sources=[]Source{{Kind:GlottalVoiced,NominalHz:160,Amplitude:1.1}};push(f)
 f=baselineOut;f.Sources=[]Source{{Kind:AirflowNoise,NominalHz:100,Amplitude:0.5}};push(f)
 f=baselineOut;f.EndSample=f.StartSample;push(f)
 f=baseline(Pause,Closed);f.NasalFlowM3S=1e-4;push(f)
 f=baseline(Expiration,Nasal);f.VelumOpen=false;push(f)
 f=baseline(Expiration,Mixed);f.NasalFlowM3S=0;f.TotalFlowM3S=f.OralFlowM3S;push(f)
 f=baseline(Expiration,Oral);f.Sources=[]Source{{Kind:GlottalVoiced,NominalHz:160,Amplitude:0.3}}
 invalid=append(invalid,fixture(Hum,f))
 invalid=append(invalid,fixture(LipWhistleAction,f))
 invalid=append(invalid,fixture(FlutePlay,f))
 invalid=append(invalid,fixture(StrawSuction,object(Expiration,Straw,AirflowNoise,0)))
 invalid=append(invalid,fixture(Beatbox,baseline(Pause,Closed)))
 invalid=append(invalid,fixture(Pant,baseline(Expiration,Oral)))
 f=baseline(Inspiration,Oral);f.StartSample=4801;f.EndSample=9600
 invalid=append(invalid,fixture(Pant,baseline(Expiration,Oral),f))
 for i,p:=range invalid{if err:=p.Validate();err==nil{t.Fatalf("invalid physiological source combination %d accepted: %#v",i,p)}}
}
func TestBoundaryAndSourceClassification(t *testing.T){
 p:=fixture(QuietBreath,baseline(Expiration,Oral))
 p.Classification="PRIVATE_FINAL_CHARACTER_VOICE"
 if err:=p.Validate();err==nil{t.Fatal("private asset admitted to synthetic runner")}
 p.Classification=Classification
 p.Schema="incompatible"
 if err:=p.Validate();err==nil{t.Fatal("unexpected schema admitted")}
 p.Schema=Schema
 p.Frames=make([]Frame,257)
 if err:=p.Validate();err==nil{t.Fatal("unbounded frame count admitted")}
 p=fixture(QuietBreath,baseline(Expiration,Oral))
 if err:=p.Validate();err!=nil{t.Fatal(err)}
 b,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
 if !strings.Contains(string(b),"total_flow_m3_s")||!strings.Contains(string(b),"sample_rate_hz"){
  t.Fatal("source-neutral units/schema not machine-readable")
 }
}
