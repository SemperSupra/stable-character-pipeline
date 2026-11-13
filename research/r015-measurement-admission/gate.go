package r015gate

import "math"

type Status string
const (
 Pass Status = "PASS_STRUCTURAL_ONLY"
 Unknown Status = "UNKNOWN_ABSTAIN"
 Reject Status = "REJECT"
)

type Measurement struct { Name string; Value float64; Unit string; Method string; SourceSHA string; LandmarkProvenance string }
type Evidence struct {
 AdultAsserted bool
 RightsKnown bool
 EvaluatedMesh bool
 NativeReopened bool
 IndependentScaleCalibrated bool
 OutOfDistributionKnown bool
 HeldoutIndependent bool
 Measurements []Measurement
}
type Result struct { Status Status; Reasons []string }
func Check(e Evidence) Result {
 out := Result{Status:Pass}
 fail := func(status Status, reason string) {
  if status == Reject || out.Status != Reject && status == Unknown {out.Status=status}
  out.Reasons=append(out.Reasons,reason)
 }
 if !e.AdultAsserted {fail(Reject,"adult_assertion_missing")}
 if !e.RightsKnown {fail(Unknown,"rights_unknown")}
 if !e.EvaluatedMesh || !e.NativeReopened {fail(Unknown,"native_geometry_unverified")}
 if !e.IndependentScaleCalibrated {fail(Unknown,"physical_scale_uncalibrated")}
 if !e.OutOfDistributionKnown || !e.HeldoutIndependent {fail(Unknown,"ood_or_holdout_unverified")}
 if len(e.Measurements)==0 {fail(Unknown,"measurements_missing")}
 names:=map[string]bool{}
 for _,m:=range e.Measurements {
  if m.Name=="" || names[m.Name] {fail(Reject,"invalid_or_duplicate_measurement_name")}
  names[m.Name]=true
  if math.IsNaN(m.Value)||math.IsInf(m.Value,0)||m.Value<=0 {fail(Reject,"nonpositive_or_nonfinite_measurement")}
  if m.Unit!="cm" && m.Unit!="m" {fail(Unknown,"unqualified_measurement_unit")}
  if m.Method=="" || m.SourceSHA=="" || m.LandmarkProvenance=="" {fail(Unknown,"measurement_provenance_incomplete")}
 }
 return out
}
