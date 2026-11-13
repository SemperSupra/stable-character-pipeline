package morphgate

import (
 "encoding/json"
 "math"
 "strings"
 "testing"
)

var sHash=strings.Repeat("a",64)
var macroHash=strings.Repeat("b",64)
func f(x float64)*float64{return &x}
func example() Evidence{return Evidence{
 Schema:"r015.typed_morphology_consumer_candidate.v1",
 SourceSceneSHA256:sHash,MacroConfigSHA256:macroHash,
 ShapePreset:"female",SourceMacroValue:0,MatureAdultAssetDesign:true,
 NativeUnit:"BLENDER_SCENE_UNIT_UNCALIBRATED",
 Measurements:[]Measure{{Region:"left_arm",Method:"landmark_distance",NativeValue:2}},
 HeldoutStatus:"NOT_TESTED",OODStatus:"NOT_TESTED"}}
func registry() Registry{return Registry{PinnedMacroConfigSHA256:macroHash,
 PresetToMacro:map[string]float64{"female":0,"male":1},
 ScaleByID:map[string]TrustedScale{},
 QualifiedRegionMethods:map[string]bool{"left_arm|landmark_distance":true}}}
func requireReject(t *testing.T,s Evidence,r Registry) {
 t.Helper();if _,err:=Validate(s,r);err==nil{t.Fatal("unsafe evidence accepted")}
}
func TestUncalibratedNativeEvidenceMustAbstain(t *testing.T) {
 result,e:=Validate(example(),registry());if e!=nil {t.Fatal(e)}
 if result.UnitConversion!="UNKNOWN_NATIVE_ONLY"||result.PhysicalAnatomy!="HOLD_NOT_QUALIFIED"||
  result.CanonicalCharacterPack!="HOLD_HUMAN_DECISION_ONLY" {t.Fatal(result)}
}
func TestSourceMacroInversionRejected(t *testing.T) {
 s:=example();s.SourceMacroValue=1
 requireReject(t,s,registry())
}
func TestUnpinnedMacroSourceRejected(t *testing.T) {
 s:=example();s.MacroConfigSHA256=strings.Repeat("c",64)
 requireReject(t,s,registry())
}
func TestUntrustedPhysicalUnitsRejected(t *testing.T) {
 s:=example();s.ScaleRecordID="self-declared";s.ClaimedCentimetersPerNative=f(10)
 s.Measurements[0].ClaimedCentimeters=f(20);s.Measurements[0].UncertaintyCentimeters=f(.5)
 requireReject(t,s,registry())
}
func TestCorrectlyAdmittedSyntheticScaleIsStillNotAnatomy(t *testing.T) {
 s:=example();s.ScaleRecordID="synthetic-fixture";s.ClaimedCentimetersPerNative=f(2)
 s.Measurements[0].ClaimedCentimeters=f(4);s.Measurements[0].UncertaintyCentimeters=f(.1)
 r:=registry();r.ScaleByID["synthetic-fixture"]=TrustedScale{SourceSHA256:sHash,CentimetersPerNative:2,Admitted:true}
 result,e:=Validate(s,r);if e!=nil {t.Fatal(e)}
 if result.Status!="PASS_ADMITTED_NUMERIC_CONVERSION_ONLY__HOLD_PHYSICAL_ACCEPTANCE"||
 result.PhysicalAnatomy!="HOLD_NOT_QUALIFIED"||result.FullBodyOOD!="NOT_TESTED_HOLD" {t.Fatal(result)}
}
func TestSpoofedScaleIssuerRejected(t *testing.T){
 s:=example();s.ScaleRecordID="synthetic-fixture";s.ClaimedCentimetersPerNative=f(2)
 r:=registry();r.ScaleByID["synthetic-fixture"]=TrustedScale{SourceSHA256:strings.Repeat("c",64),CentimetersPerNative:2,Admitted:true}
 requireReject(t,s,r)
}
func TestContradictoryMeasurementRejected(t *testing.T){
 s:=example();s.ScaleRecordID="synthetic-fixture";s.ClaimedCentimetersPerNative=f(2)
 s.Measurements[0].ClaimedCentimeters=f(3);s.Measurements[0].UncertaintyCentimeters=f(.1)
 r:=registry();r.ScaleByID["synthetic-fixture"]=TrustedScale{SourceSHA256:sHash,CentimetersPerNative:2,Admitted:true}
 requireReject(t,s,r)
}
func TestNegativeOrMissingUncertaintyRejected(t *testing.T) {
 s:=example();s.ScaleRecordID="synthetic-fixture";s.ClaimedCentimetersPerNative=f(2)
 s.Measurements[0].ClaimedCentimeters=f(4);s.Measurements[0].UncertaintyCentimeters=f(-.1)
 r:=registry();r.ScaleByID["synthetic-fixture"]=TrustedScale{SourceSHA256:sHash,CentimetersPerNative:2,Admitted:true}
 requireReject(t,s,r)
}
func TestUnknownLandmarkCannotPass(t *testing.T){
 s:=example();s.Measurements[0].Method="bounding_box_slice_not_circumference"
 r:=registry();r.ScaleByID["synthetic-fixture"]=TrustedScale{SourceSHA256:sHash,CentimetersPerNative:2,Admitted:true}
 s.ScaleRecordID="synthetic-fixture";s.ClaimedCentimetersPerNative=f(2)
 result,e:=Validate(s,r);if e!=nil {t.Fatal(e)}
 if result.UnknownLandmarkMethods!=1||!strings.HasPrefix(result.Status,"UNKNOWN_"){t.Fatal(result)}
}
func TestNonfiniteReject(t *testing.T){
 s:=example();s.Measurements[0].NativeValue=math.NaN()
 requireReject(t,s,registry())
}
func TestUnderspecifiedDesignRejected(t *testing.T){
 s:=example();s.MatureAdultAssetDesign=false
 requireReject(t,s,registry())
}
func TestStrictDecoderRejectsSelfAssertedCanonicalApproval(t *testing.T){
 raw,_:=json.Marshal(example())
 raw=append(raw[:len(raw)-1],[]byte(`,"HumanApprovalID":"trust-me"}`)...)
 if _,e:=DecodeStrict(raw);e==nil{t.Fatal("unknown authority field accepted")}
}
func TestStrictDecoderRejectsTrailingJSON(t *testing.T){
 raw,_:=json.Marshal(example())
 raw=append(raw,[]byte(` {"schema":"forged"}`)...)
 if _,e:=DecodeStrict(raw);e==nil{t.Fatal("trailing document accepted")}
}
