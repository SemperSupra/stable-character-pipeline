// Package behavior defines source-neutral, bounded, synthetic-only
// respiratory and vocal-performance states, not a medical or acoustically
// validated human model. Continuous 3D mechanics and sound synthesis are
// separate, optional versioned capability adapters.
package behavior

import (
 "errors"
 "fmt"
 "math"
)

const Schema="respiratory.performance.v0"
const Classification="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"
const Rate=48000
const tolerance=1e-9

type Phase string
const (
 Inspiration Phase="inspiration"
 Expiration Phase="expiration"
 Pause Phase="pause"
)
type Route string
const (
 Nasal Route="nasal"
 Oral Route="oral"
 Mixed Route="mixed"
 ObjectRoute Route="external_port"
 Closed Route="closed"
)
type Port string
const (
 NoPort Port="none"
 Flute Port="flute_edge"
 Reed Port="reed"
 ExternalWhistle Port="whistle"
 Balloon Port="elastic_balloon"
 Straw Port="straw"
)
type SourceKind string
const (
 AirflowNoise SourceKind="airflow_turbulence"
 GlottalVoiced SourceKind="glottal_voiced"
 GlottalIrregular SourceKind="glottal_irregular"
 LipWhistle SourceKind="lip_jet"
 ArticulatoryClick SourceKind="articulatory_transient"
 EdgeTone SourceKind="edge_tone"
 ReedTone SourceKind="reed_tone"
 ElasticNoise SourceKind="elastic_material_noise"
)
type Action string
const (
 QuietBreath Action="quiet_breath"
 DeepBreath Action="deep_breath"
 Pant Action="pant"
 Sniff Action="sniff"
 Sigh Action="sigh"
 Gasp Action="gasp"
 Hum Action="hum"
 Sing Action="sing"
 Cry Action="cry"
 Laugh Action="laugh"
 Scream Action="scream"
 LipWhistleAction Action="lip_whistle"
 Beatbox Action="beatbox"
 FlutePlay Action="flute"
 ReedPlay Action="reed_instrument"
 BlowWhistle Action="blow_whistle"
 InflateBalloon Action="inflate_balloon"
 StrawSuction Action="straw_suction"
)
type Source struct {
 Kind SourceKind `json:"kind"`
 // Prescribed oscillator rate, NOT independently measured actual F0.
 NominalHz float64 `json:"nominal_hz"`
 Amplitude float64 `json:"normalized_amplitude"`
}
type Frame struct {
 StartSample int `json:"start_sample"`
 EndSample int `json:"end_sample"`
 Phase Phase `json:"phase"`
 Route Route `json:"route"`
 // Free nostril, free mouth, and external object flows are mutually exclusive
 // outlets and sum to the signed total. Positive=expiration; negative=inspiration.
 NasalFlowM3S float64 `json:"nasal_flow_m3_s"`
 OralFlowM3S float64 `json:"oral_free_flow_m3_s"`
 ObjectFlowM3S float64 `json:"external_port_flow_m3_s"`
 TotalFlowM3S float64 `json:"total_flow_m3_s"`
 SubglottalGaugePressurePa float64 `json:"subglottal_gauge_pressure_pa"`
 // Geometry control metadata, not measured 3D tissue shape.
 VelumOpen bool `json:"velopharyngeal_open"`
 MouthFreeOpening bool `json:"mouth_free_open"`
 DevicePort Port `json:"external_port"`
 Sources []Source `json:"sources"`
}
type Performance struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 Action Action `json:"action"`
 SampleRateHz int `json:"sample_rate_hz"`
 // Exact clock, state provenance is event-level, no subject/person data.
 Frames []Frame `json:"frames"`
}

func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func nonzero(x float64)bool{return math.Abs(x)>tolerance}
func sourceKnown(k SourceKind)bool{
 switch k{case AirflowNoise,GlottalVoiced,GlottalIrregular,LipWhistle,ArticulatoryClick,EdgeTone,ReedTone,ElasticNoise:return true}
 return false
}
func actionKnown(a Action)bool{
 switch a{case QuietBreath,DeepBreath,Pant,Sniff,Sigh,Gasp,Hum,Sing,Cry,Laugh,Scream,LipWhistleAction,Beatbox,FlutePlay,ReedPlay,BlowWhistle,InflateBalloon,StrawSuction:return true}
 return false
}
func portKnown(p Port)bool{
 switch p{case NoPort,Flute,Reed,ExternalWhistle,Balloon,Straw:return true}
 return false
}
func validateFrame(f Frame)error{
 if f.EndSample<=f.StartSample||f.StartSample<0{return errors.New("nonmonotone frame clock")}
 values:=[]float64{f.NasalFlowM3S,f.OralFlowM3S,f.ObjectFlowM3S,f.TotalFlowM3S,f.SubglottalGaugePressurePa}
 for _,x:=range values{if !finite(x){return errors.New("nonfinite airflow or pressure")}}
 if !portKnown(f.DevicePort){return errors.New("unknown external port")}
 sum:=f.NasalFlowM3S+f.OralFlowM3S+f.ObjectFlowM3S
 if math.Abs(sum-f.TotalFlowM3S)>1e-8*math.Max(1,math.Abs(f.TotalFlowM3S)){return errors.New("flow branch conservation failure")}
 switch f.Phase{
 case Inspiration:
  if f.TotalFlowM3S>=-tolerance{return errors.New("inspiration must have inward flow")}
  for _,x:=range values[:3]{if x>tolerance{return errors.New("inspiration has reverse branch")}}
 case Expiration:
  if f.TotalFlowM3S<=tolerance{return errors.New("expiration must have outward flow")}
  for _,x:=range values[:3]{if x< -tolerance{return errors.New("expiration has reverse branch")}}
 case Pause:
  if nonzero(f.TotalFlowM3S)||nonzero(f.NasalFlowM3S)||nonzero(f.OralFlowM3S)||nonzero(f.ObjectFlowM3S){return errors.New("pause requires no signed bulk flow")}
 default:return errors.New("unknown respiratory phase")
 }
 if nonzero(f.NasalFlowM3S)&&!f.VelumOpen{return errors.New("nasal flow with closed velum")}
 if nonzero(f.OralFlowM3S)&&!f.MouthFreeOpening{return errors.New("oral free flow with sealed mouth")}
 if f.DevicePort==NoPort&&nonzero(f.ObjectFlowM3S){return errors.New("flow without object port")}
 if f.DevicePort!=NoPort&&f.Route!=ObjectRoute{return errors.New("object attached outside external-port route")}
 switch f.Route{
 case Nasal:
  if !nonzero(f.NasalFlowM3S)||nonzero(f.OralFlowM3S)||nonzero(f.ObjectFlowM3S){return errors.New("inconsistent nasal route")}
 case Oral:
  if !nonzero(f.OralFlowM3S)||nonzero(f.NasalFlowM3S)||nonzero(f.ObjectFlowM3S){return errors.New("inconsistent oral route")}
 case Mixed:
  if !nonzero(f.OralFlowM3S)||!nonzero(f.NasalFlowM3S)||nonzero(f.ObjectFlowM3S){return errors.New("mixed route requires nasal and oral branches")}
 case ObjectRoute:
  if f.DevicePort==NoPort||!nonzero(f.ObjectFlowM3S)||nonzero(f.OralFlowM3S)||nonzero(f.NasalFlowM3S){return errors.New("invalid exclusive external-port route")}
 case Closed:
  if f.Phase!=Pause||nonzero(f.TotalFlowM3S){return errors.New("closed route must have no bulk flow")}
 default:return errors.New("unknown respiratory route")
 }
 if len(f.Sources)>8{return errors.New("unbounded concurrent source count")}
 for _,s:=range f.Sources{
  if !sourceKnown(s.Kind)||!finite(s.NominalHz)||!finite(s.Amplitude)||s.Amplitude<0||s.Amplitude>1{return errors.New("invalid excitation source")}
  switch s.Kind{
  case GlottalVoiced,GlottalIrregular,LipWhistle,EdgeTone,ReedTone:
   if s.NominalHz<=0||s.NominalHz>5000||f.Phase==Pause{return errors.New("tonal excitation requires valid source and airflow")}
  default:
   if s.NominalHz!=0{return errors.New("non-tonal source declared an oscillator")}
  }
  if (s.Kind==EdgeTone||s.Kind==ReedTone||s.Kind==ElasticNoise)&&f.Route!=ObjectRoute{
   return errors.New("external-device excitation without object port")
  }
  if s.Kind==EdgeTone&&f.DevicePort!=Flute&&f.DevicePort!=ExternalWhistle{
   return errors.New("edge tone without flute or whistle port")
  }
  if s.Kind==ReedTone&&f.DevicePort!=Reed{return errors.New("reed tone without reed port")}
  if s.Kind==ElasticNoise&&f.DevicePort!=Balloon{return errors.New("elastic noise without balloon port")}
  if s.Kind==LipWhistle&&f.Route!=Oral{return errors.New("lip whistle without free oral jet")}
  if s.Kind==ArticulatoryClick&&f.DevicePort!=NoPort{return errors.New("articulatory click assigned to external object")}
 }
 return nil
}
func hasSource(f Frame,k SourceKind)bool{
 for _,s:=range f.Sources{if s.Kind==k{return true}}
 return false
}
func(p Performance)Validate()error{
 if p.Schema!=Schema||p.Classification!=Classification||p.SampleRateHz!=Rate{return errors.New("invalid schema, data classification or sample clock")}
 if !actionKnown(p.Action)||len(p.Frames)==0||len(p.Frames)>256{return errors.New("unknown or unbounded performance")}
 if p.Frames[0].StartSample!=0{return errors.New("performance must start at sample zero")}
 seenIn,seenOut:=false,false
 for i,f:=range p.Frames{
  if i>0&&f.StartSample!=p.Frames[i-1].EndSample{return fmt.Errorf("frame %d has gap/overlap",i)}
  if err:=validateFrame(f);err!=nil{return fmt.Errorf("frame %d: %w",i,err)}
  if f.Phase==Inspiration{seenIn=true};if f.Phase==Expiration{seenOut=true}
  switch p.Action{
  case Hum:
   if f.Phase!=Expiration||f.Route!=Nasal||!hasSource(f,GlottalVoiced){return errors.New("hum requires expiratory nasal voiced source")}
  case Sing:
   if f.Phase!=Expiration||!hasSource(f,GlottalVoiced){return errors.New("sing requires expiratory voiced source")}
  case LipWhistleAction:
   if f.Phase!=Expiration||!hasSource(f,LipWhistle){return errors.New("lip whistling requires oral jet excitation")}
  case Beatbox:
   if !hasSource(f,ArticulatoryClick){return errors.New("beatboxing fixture requires articulatory transient")}
  case FlutePlay:
   if f.Phase!=Expiration||f.DevicePort!=Flute||!hasSource(f,EdgeTone){return errors.New("flute requires expiratory external edge-tone source")}
  case ReedPlay:
   if f.Phase!=Expiration||f.DevicePort!=Reed||!hasSource(f,ReedTone){return errors.New("reed performance requires external reed source")}
  case BlowWhistle:
   if f.Phase!=Expiration||f.DevicePort!=ExternalWhistle||!hasSource(f,EdgeTone){return errors.New("object whistle requires external edge-tone source")}
  case InflateBalloon:
   if f.Phase!=Expiration||f.DevicePort!=Balloon{return errors.New("balloon inflation requires expiratory port")}
  case StrawSuction:
   if f.Phase!=Inspiration||f.DevicePort!=Straw{return errors.New("straw suction requires inspiratory object port")}
  }
 }
 if p.Action==Pant&&(!seenIn||!seenOut){return errors.New("pant requires both inspiratory and expiratory events")}
 return nil
}
