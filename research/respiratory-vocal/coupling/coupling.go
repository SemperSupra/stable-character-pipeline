// Package coupling connects the separate signed-flow RC numerical oracle to
// the original synthetic sound preview under an explicitly UNCALIBRATED
// mechanical-energy-to-audio amplitude adaptation. No biological validity,
// human loudness, airflow safety or native Physical Vocal v0 is claimed.
package coupling

import(
 "errors"
 "fmt"
 "math"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/physics"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Config struct{
 Mechanics physics.Config `json:"mechanics"`
 // Synthetic, measured-in-Joules normalization. This is NOT a clinically
 // calibrated sound power conversion or source-to-ear transfer efficiency.
 NormalizationLossJ float64 `json:"normalization_loss_j"`
}
type FrameGain struct{
 StartSample int `json:"start_sample"`
 EndSample int `json:"end_sample"`
 SignedFlowM3S float64 `json:"signed_flow_m3_s"`
 MechanicalDissipationJ float64 `json:"mechanical_dissipation_j"`
 NormalizedAmplitudeGain float64 `json:"normalized_amplitude_gain"`
 NonPulmonaryClicksRetained int `json:"nonpulmonary_clicks_retained"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Validity string `json:"validity"`
 Action behavior.Action `json:"action"`
 Mechanics physics.Receipt `json:"mechanics"`
 Audio preview.Receipt `json:"audio"`
 Frames []FrameGain `json:"frames"`
}
func validNorm(x float64)bool{
 return !math.IsNaN(x)&&!math.IsInf(x,0)&&x>=1e-9&&x<=1e6
}
// Render first validates the entire canonical source and its mass/energy
// accounting. It then scales only simulated pulmonary acoustic source
// amplitudes according to relative dissipative work. It DOES NOT rewrite
// pressure or volume, and never mutates the supplied Performance. Nonlung
// articulatory clicks stay independent of pulmonary bulk flow.
func Render(p behavior.Performance,c Config)([]byte,Receipt,error){
 var empty Receipt
 if !validNorm(c.NormalizationLossJ){return nil,empty,errors.New("invalid uncalibrated acoustic normalization")}
 mechanics,err:=physics.Integrate(p,c.Mechanics)
 if err!=nil{return nil,empty,fmt.Errorf("unadmitted respiratory mechanics: %w",err)}
 if len(mechanics.Frames)!=len(p.Frames){return nil,empty,errors.New("mechanical frame contract mismatch")}
 copied:=p
 copied.Frames=append([]behavior.Frame(nil),p.Frames...)
 gains:=make([]FrameGain,0,len(copied.Frames))
 for i,frame:=range copied.Frames{
  state:=mechanics.Frames[i]
  if state.StartSample!=frame.StartSample||state.EndSample!=frame.EndSample||
   state.FlowM3S!=frame.TotalFlowM3S{
   return nil,empty,fmt.Errorf("frame %d uncoupled source clock or signed flow",i)
  }
  loss:=state.ResistiveLossJ
  if loss<0||math.IsNaN(loss)||math.IsInf(loss,0){return nil,empty,fmt.Errorf("frame %d invalid signed energy",i)}
  gain:=math.Sqrt(loss/c.NormalizationLossJ)
  if gain>1{gain=1}
  if !math.IsNaN(gain)&&!math.IsInf(gain,0)&&gain>=0&&gain<=1{
   // Do not change original p.Sources slice or mutate source identities.
   sources:=append([]behavior.Source(nil),frame.Sources...)
   clicks:=0
   for j:=range sources{
    if sources[j].Kind==behavior.ArticulatoryClick{
     clicks++;continue
    }
    sources[j].Amplitude*=gain
   }
   copied.Frames[i].Sources=sources
   gains=append(gains,FrameGain{
    StartSample:frame.StartSample,EndSample:frame.EndSample,
    SignedFlowM3S:frame.TotalFlowM3S,
    MechanicalDissipationJ:loss,NormalizedAmplitudeGain:gain,
    NonPulmonaryClicksRetained:clicks,
   })
  }else{return nil,empty,fmt.Errorf("frame %d invalid bounded audio adaptation",i)}
 }
 wav,audio,err:=preview.Render(copied)
 if err!=nil{return nil,empty,fmt.Errorf("adapted synthetic audio: %w",err)}
 receipt:=Receipt{
  Schema:"respiratory.mechanics_audio_adapter.v0",
  Validity:"uncalibrated_relative_mechanical_energy_gain_not_physical_audio_power",
  Action:p.Action,Mechanics:mechanics,Audio:audio,Frames:gains,
 }
 return wav,receipt,nil
}
