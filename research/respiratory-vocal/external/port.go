// Package external is a passive, prescribed-flow lumped boundary research model.
// It does NOT synthesize authentic flute/reed/whistle oscillations, reflect
// distributed pressure waves, diagnose respiratory effort, or model an actual
// elastic balloon membrane. These require separately qualified subsystems.
package external

import (
 "errors"
 "fmt"
 "math"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
)

// Config uses SI units. Positive volume flow leaves the human airway; negative
// flows inward. ResistivePaSPerM3 is a constant phenomenological loss. Only a
// toy elastic balloon retains a lumped storage volume across frames.
type Config struct{
 Port behavior.Port `json:"port"`
 ResistancePaSPerM3 float64 `json:"resistance_pa_s_per_m3"`
 BalloonComplianceM3PerPa float64 `json:"balloon_compliance_m3_per_pa"`
 InitialBalloonVolumeM3 float64 `json:"initial_balloon_volume_m3"`
 BalloonCapacityM3 float64 `json:"balloon_capacity_m3"`
}
type FrameReceipt struct{
 StartSample int `json:"start_sample"`
 EndSample int `json:"end_sample"`
 SignedFlowM3S float64 `json:"signed_flow_m3_s"`
 NetTransferredVolumeM3 float64 `json:"net_transferred_volume_m3"`
 InitialBalloonVolumeM3 float64 `json:"initial_balloon_volume_m3"`
 FinalBalloonVolumeM3 float64 `json:"final_balloon_volume_m3"`
 ResistivePressureDropPa float64 `json:"resistive_pressure_drop_pa"`
 ElasticPressureMidPa float64 `json:"elastic_pressure_mid_pa"`
 TotalPressureDropPa float64 `json:"total_pressure_drop_pa"`
 DissipatedEnergyJ float64 `json:"dissipated_energy_j"`
 StoredEnergyChangeJ float64 `json:"stored_energy_change_j"`
 SourceWorkJ float64 `json:"source_work_j"`
 EnergyResidualJ float64 `json:"energy_balance_residual_j"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 Validity string `json:"validity"`
 Port behavior.Port `json:"port"`
 Action behavior.Action `json:"action"`
 SignedNetVolumeM3 float64 `json:"signed_net_volume_m3"`
 FinalBalloonVolumeM3 float64 `json:"final_balloon_volume_m3"`
 DissipatedEnergyJ float64 `json:"dissipated_energy_j"`
 StoredEnergyChangeJ float64 `json:"stored_energy_change_j"`
 SourceWorkJ float64 `json:"source_work_j"`
 MaxAbsEnergyResidualJ float64 `json:"max_abs_energy_residual_j"`
 Frames []FrameReceipt `json:"frames"`
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func isPhysicalPort(p behavior.Port)bool{
 switch p{case behavior.Flute,behavior.Reed,behavior.ExternalWhistle,behavior.Balloon,behavior.Straw:return true}
 return false
}
func validate(c Config)error{
 if !isPhysicalPort(c.Port){return errors.New("unknown or unattached object port")}
 vals:=[]float64{c.ResistancePaSPerM3,c.BalloonComplianceM3PerPa,c.InitialBalloonVolumeM3,c.BalloonCapacityM3}
 for _,x:=range vals{if !finite(x){return errors.New("nonfinite port parameter")}}
 if c.ResistancePaSPerM3<=0||c.ResistancePaSPerM3>1e12{return errors.New("invalid bounded resistance")}
 if c.Port==behavior.Balloon {
  if c.BalloonComplianceM3PerPa<1e-12||c.BalloonComplianceM3PerPa>1||c.BalloonCapacityM3<=0||c.BalloonCapacityM3>1||
     c.InitialBalloonVolumeM3<0||c.InitialBalloonVolumeM3>c.BalloonCapacityM3{
   return errors.New("invalid toy elastic capacity/compliance")
  }
 } else if c.BalloonComplianceM3PerPa!=0||c.InitialBalloonVolumeM3!=0||c.BalloonCapacityM3!=0{
  return errors.New("nonballoon port cannot silently store balloon volume")
 }
 return nil
}
// Evaluate uses prescribed flow from a previously validated human performance.
// Port pressure and resistance are external boundary proxies; they are not the
// human glottal/subglottal pressures nor authentic acoustic input impedance.
// An equivalent *frequency-dependent* reed/edge/bore feedback is NOT simulated.
func Evaluate(p behavior.Performance,c Config)(Receipt,error){
 var empty Receipt
 if e:=p.Validate();e!=nil{return empty,fmt.Errorf("performance: %w",e)}
 if e:=validate(c);e!=nil{return empty,e}
 if p.Frames[len(p.Frames)-1].EndSample>480000{return empty,errors.New("source clock exceeds 10-second cap")}
 volume:=c.InitialBalloonVolumeM3
 out:=Receipt{Schema:"respiratory.external_port_passivity.v0",Classification:behavior.Classification,Validity:"constant_resistance_balloon_linear_compliance_toy_not_instrument_physics",Port:c.Port,Action:p.Action,Frames:make([]FrameReceipt,0,len(p.Frames))}
 for i,f:=range p.Frames{
  if f.Route!=behavior.ObjectRoute||f.DevicePort!=c.Port{
   return empty,fmt.Errorf("frame %d unsupported or mismatched physical port",i)
  }
  q:=f.ObjectFlowM3S
  dt:=float64(f.EndSample-f.StartSample)/behavior.Rate
  if !finite(q)||q==0{return empty,fmt.Errorf("frame %d requires signed object flow",i)}
  transfer:=q*dt
  vNext:=volume
  elasticMid:=0.0
  stored:=0.0
  if c.Port==behavior.Balloon{
   if q<=0{return empty,fmt.Errorf("frame %d toy inflation is expiration-only",i)}
   vNext+=transfer
   if vNext>c.BalloonCapacityM3+1e-12{return empty,fmt.Errorf("frame %d balloon capacity exhausted",i)}
   if vNext>c.BalloonCapacityM3{vNext=c.BalloonCapacityM3}
   elasticMid:=(volume+vNext)/(2*c.BalloonComplianceM3PerPa)
   stored=(vNext*vNext-volume*volume)/(2*c.BalloonComplianceM3PerPa)
   _=elasticMid
  }
  // In-place assignment is intentionally after volume update; the delta
  // matches the midpoint quadrature of a linear potential exactly.
  if c.Port==behavior.Balloon{elasticMid=(volume+vNext)/(2*c.BalloonComplianceM3PerPa)}
  resistiveDrop:=c.ResistancePaSPerM3*q
  pressure:=resistiveDrop+elasticMid
  loss:=c.ResistancePaSPerM3*q*q*dt
  work:=pressure*transfer
  residual:=work-loss-stored
  for _,v:=range []float64{transfer,vNext,pressure,loss,stored,work,residual}{
   if !finite(v){return empty,fmt.Errorf("frame %d numerical overflow",i)}
  }
  if math.Abs(pressure)>1e9{return empty,fmt.Errorf("frame %d numerical pressure cap",i)}
  if loss<0||math.Abs(residual)>1e-9*math.Max(1,math.Abs(work)+loss+math.Abs(stored)){
   return empty,fmt.Errorf("frame %d port energy/passivity balance failed",i)
  }
  out.Frames=append(out.Frames,FrameReceipt{
   StartSample:f.StartSample,EndSample:f.EndSample,SignedFlowM3S:q,NetTransferredVolumeM3:transfer,
   InitialBalloonVolumeM3:volume,FinalBalloonVolumeM3:vNext,
   ResistivePressureDropPa:resistiveDrop,ElasticPressureMidPa:elasticMid,TotalPressureDropPa:pressure,
   DissipatedEnergyJ:loss,StoredEnergyChangeJ:stored,SourceWorkJ:work,EnergyResidualJ:residual,
  })
  out.SignedNetVolumeM3+=transfer
  out.DissipatedEnergyJ+=loss;out.StoredEnergyChangeJ+=stored;out.SourceWorkJ+=work
  out.MaxAbsEnergyResidualJ=math.Max(out.MaxAbsEnergyResidualJ,math.Abs(residual))
  volume=vNext
 }
 out.FinalBalloonVolumeM3=volume
 return out,nil
}
