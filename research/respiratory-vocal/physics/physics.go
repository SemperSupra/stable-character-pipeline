// Package physics is a prescribed-flow resistance/compliance research oracle.
// It does not predict physiology, distress, injury, or medical safety.
package physics
import("errors";"fmt";"math"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior")
type Config struct{
 ReferenceVolumeM3 float64 `json:"reference_volume_m3"`
 InitialVolumeM3 float64 `json:"initial_volume_m3"`
 MinimumVolumeM3 float64 `json:"minimum_volume_m3"`
 MaximumVolumeM3 float64 `json:"maximum_volume_m3"`
 ComplianceM3PerPa float64 `json:"compliance_m3_per_pa"`
 NasalResistancePaSPerM3 float64 `json:"nasal_resistance_pa_s_per_m3"`
 OralResistancePaSPerM3 float64 `json:"oral_resistance_pa_s_per_m3"`
 PortResistancePaSPerM3 float64 `json:"port_resistance_pa_s_per_m3"`
}
type FrameReceipt struct{
 StartSample int `json:"start_sample"`
 EndSample int `json:"end_sample"`
 InitialVolumeM3 float64 `json:"initial_volume_m3"`
 FinalVolumeM3 float64 `json:"final_volume_m3"`
 FlowM3S float64 `json:"flow_m3_s"`
 ElasticGaugePressureMidPa float64 `json:"elastic_gauge_pressure_mid_pa"`
 ResistiveEquivalentPressurePa float64 `json:"resistive_equivalent_pressure_pa"`
 RequiredExternalDrivePressurePa float64 `json:"required_external_drive_pressure_pa"`
 ResistiveLossJ float64 `json:"resistive_loss_j"`
 StoredEnergyChangeJ float64 `json:"stored_energy_change_j"`
 ExternalDriveWorkJ float64 `json:"external_drive_work_j"`
 EnergyResidualJ float64 `json:"energy_balance_residual_j"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 Validity string `json:"validity"`
 SourceAction behavior.Action `json:"source_action"`
 InitialVolumeM3 float64 `json:"initial_volume_m3"`
 FinalVolumeM3 float64 `json:"final_volume_m3"`
 NetOutflowVolumeM3 float64 `json:"net_outflow_volume_m3"`
 ResistiveLossJ float64 `json:"resistive_loss_j"`
 StoredEnergyChangeJ float64 `json:"stored_energy_change_j"`
 ExternalDriveWorkJ float64 `json:"external_drive_work_j"`
 MaxAbsEnergyResidualJ float64 `json:"max_abs_energy_residual_j"`
 Frames []FrameReceipt `json:"frames"`
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func valid(c Config)error{
 v:=[]float64{c.ReferenceVolumeM3,c.InitialVolumeM3,c.MinimumVolumeM3,c.MaximumVolumeM3,c.ComplianceM3PerPa,c.NasalResistancePaSPerM3,c.OralResistancePaSPerM3,c.PortResistancePaSPerM3}
 for _,x:=range v{if !finite(x){return errors.New("nonfinite parameter")}}
 if c.MinimumVolumeM3<0||c.MinimumVolumeM3>=c.MaximumVolumeM3||c.InitialVolumeM3<c.MinimumVolumeM3||c.InitialVolumeM3>c.MaximumVolumeM3||c.ReferenceVolumeM3<c.MinimumVolumeM3||c.ReferenceVolumeM3>c.MaximumVolumeM3{return errors.New("invalid reservoir bounds")}
 if c.ComplianceM3PerPa<=0||c.NasalResistancePaSPerM3<=0||c.OralResistancePaSPerM3<=0||c.PortResistancePaSPerM3<=0{return errors.New("nonpositive compliance/resistance")}
 if c.ComplianceM3PerPa<1e-12||c.ComplianceM3PerPa>1||c.MaximumVolumeM3>1||c.NasalResistancePaSPerM3>1e14||c.OralResistancePaSPerM3>1e14||c.PortResistancePaSPerM3>1e14{return errors.New("computational parameter bound; not a clinical limit")}
 return nil
}
// Positive Q is expiration, dVlung/dt=-Q. For prescribed flow,
// Pdrive=R_equiv*Q - (Vmid-Vref)/C; work = resistive loss + delta storage.
// Mixed nasal/oral branches are physically parallel, so their pressure
// drops must agree. No inference of subglottal pressure or health is made.
func Integrate(p behavior.Performance,c Config)(Receipt,error){
 var out Receipt
 if e:=p.Validate();e!=nil{return out,fmt.Errorf("behavior: %w",e)}
 if e:=valid(c);e!=nil{return out,e}
 if p.Frames[len(p.Frames)-1].EndSample>480000{return out,errors.New("sample cap exceeded")}
 out=Receipt{Schema:"respiratory.resistance_compliance.v0",Classification:behavior.Classification,Validity:"prescribed_flow_lumped_rc_oracle_not_human_physiology",SourceAction:p.Action,InitialVolumeM3:c.InitialVolumeM3,Frames:make([]FrameReceipt,0,len(p.Frames))}
 volume:=c.InitialVolumeM3
 for i,f:=range p.Frames{
  dt:=float64(f.EndSample-f.StartSample)/behavior.Rate
  q:=f.TotalFlowM3S
  next:=volume-q*dt
  if !finite(next)||next<c.MinimumVolumeM3-1e-12||next>c.MaximumVolumeM3+1e-12{return Receipt{},fmt.Errorf("frame %d reservoir bounds",i)}
  if next<c.MinimumVolumeM3{next=c.MinimumVolumeM3};if next>c.MaximumVolumeM3{next=c.MaximumVolumeM3}
  pelastic:=((volume+next)*0.5-c.ReferenceVolumeM3)/c.ComplianceM3PerPa
  branches:=[]struct{flow,r float64}{{f.NasalFlowM3S,c.NasalResistancePaSPerM3},{f.OralFlowM3S,c.OralResistancePaSPerM3},{f.ObjectFlowM3S,c.PortResistancePaSPerM3}}
  power:=0.0;prior:=0.0;active:=false
  for _,b:=range branches{
   if b.flow==0{continue}
   drop:=b.r*b.flow
   if active&&math.Abs(drop-prior)>1e-7*math.Max(1,math.Max(math.Abs(drop),math.Abs(prior))){return Receipt{},fmt.Errorf("frame %d parallel pressure mismatch",i)}
   prior=drop;active=true;power+=b.r*b.flow*b.flow
  }
  if (q==0)==active{return Receipt{},fmt.Errorf("frame %d active flow inconsistency",i)}
  drop:=0.0;if active{drop=power/q}
  drive:=drop-pelastic
  u0:=math.Pow(volume-c.ReferenceVolumeM3,2)/(2*c.ComplianceM3PerPa)
  u1:=math.Pow(next-c.ReferenceVolumeM3,2)/(2*c.ComplianceM3PerPa)
  delta:=u1-u0;loss:=power*dt;work:=drive*q*dt
  residual:=work-loss-delta
  for _,x:=range []float64{pelastic,drop,drive,delta,loss,work,residual}{if !finite(x){return Receipt{},fmt.Errorf("frame %d numerical overflow",i)}}
  if math.Abs(residual)>1e-9*math.Max(1,math.Abs(work)+math.Abs(delta)+loss){return Receipt{},fmt.Errorf("frame %d energy mismatch",i)}
  out.Frames=append(out.Frames,FrameReceipt{StartSample:f.StartSample,EndSample:f.EndSample,InitialVolumeM3:volume,FinalVolumeM3:next,FlowM3S:q,ElasticGaugePressureMidPa:pelastic,ResistiveEquivalentPressurePa:drop,RequiredExternalDrivePressurePa:drive,ResistiveLossJ:loss,StoredEnergyChangeJ:delta,ExternalDriveWorkJ:work,EnergyResidualJ:residual})
  out.NetOutflowVolumeM3+=q*dt;out.ResistiveLossJ+=loss;out.StoredEnergyChangeJ+=delta;out.ExternalDriveWorkJ+=work
  out.MaxAbsEnergyResidualJ=math.Max(out.MaxAbsEnergyResidualJ,math.Abs(residual))
  volume=next
 }
 out.FinalVolumeM3=volume;return out,nil
}
