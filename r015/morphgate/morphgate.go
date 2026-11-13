// Package morphgate is an R015 proposal-only consumer boundary.
// It cannot confer CharacterPack canon, adult biological age, sex, or source rights.
package morphgate

import (
 "bytes"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
)

type Measure struct {
 Region string `json:"region"`
 Method string `json:"method"`
 NativeValue float64 `json:"native_value"`
 ClaimedCentimeters *float64 `json:"claimed_centimeters,omitempty"`
 UncertaintyCentimeters *float64 `json:"uncertainty_centimeters,omitempty"`
}
type Evidence struct {
 Schema string `json:"schema"`
 SourceSceneSHA256 string `json:"source_scene_sha256"`
 MacroConfigSHA256 string `json:"source_macro_config_sha256"`
 ShapePreset string `json:"source_body_shape_preset"`
 SourceMacroValue float64 `json:"source_macro_value"`
 MatureAdultAssetDesign bool `json:"mature_adult_asset_design"`
 NativeUnit string `json:"native_scene_unit"`
 ScaleRecordID string `json:"scale_record_id,omitempty"`
 ClaimedCentimetersPerNative *float64 `json:"claimed_centimeters_per_native_unit,omitempty"`
 Measurements []Measure `json:"measurements"`
 HeldoutStatus string `json:"heldout_status"`
 OODStatus string `json:"ood_status"`
}
type TrustedScale struct { SourceSHA256 string; CentimetersPerNative float64; Admitted bool }
type Registry struct {
 PinnedMacroConfigSHA256 string
 PresetToMacro map[string]float64
 ScaleByID map[string]TrustedScale
 QualifiedRegionMethods map[string]bool // precise source semantics: "region|method"
}
type Result struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 UnitConversion string `json:"unit_conversion"`
 QualifiedLandmarkMethods int `json:"qualified_landmark_methods"`
 UnknownLandmarkMethods int `json:"unknown_landmark_methods"`
 CanonicalCharacterPack string `json:"canonical_character_pack"`
 PhysicalAnatomy string `json:"physical_anatomy"`
 IdentityOrSexFromPixels string `json:"identity_or_sex_from_pixels"`
 ClinicalAge string `json:"clinical_age"`
 SourceRights string `json:"source_rights"`
 FullBodyOOD string `json:"full_body_ood"`
 HumanReview string `json:"human_review"`
}
func digest(s string) bool {
 if len(s)!=64 {return false}
 b,e:=hex.DecodeString(s);return e==nil&&len(b)==32
}
func finite(v float64) bool {return !math.IsNaN(v)&&!math.IsInf(v,0)}
func DecodeStrict(b []byte) (Evidence,error) {
 var spec Evidence
 dec:=json.NewDecoder(bytes.NewReader(b));dec.DisallowUnknownFields()
 if e:=dec.Decode(&spec);e!=nil {return spec,e}
 var extra any
 if e:=dec.Decode(&extra);e!=io.EOF {return spec,errors.New("trailing JSON or concatenated records")}
 return spec,nil
}
func Validate(s Evidence,trust Registry) (Result,error) {
 result:=Result{Schema:"r015.morphology.consumer_diagnostic.v1",
  Status:"UNKNOWN_NEEDS_TRUSTED_CALIBRATION_AND_ANATOMY",UnitConversion:"UNKNOWN_NOT_ADMITTED",
  CanonicalCharacterPack:"HOLD_HUMAN_DECISION_ONLY",PhysicalAnatomy:"HOLD_NOT_QUALIFIED",
  IdentityOrSexFromPixels:"NEVER_INFERRED",ClinicalAge:"UNKNOWN_NOT_INFERRED",
  SourceRights:"UNKNOWN_EXTERNAL_ADMISSION",FullBodyOOD:"UNKNOWN",HumanReview:"REQUIRED"}
 if s.Schema!="r015.typed_morphology_consumer_candidate.v1" {return result,errors.New("unsupported candidate schema")}
 if !digest(s.SourceSceneSHA256)||!digest(s.MacroConfigSHA256) {return result,errors.New("unpinned source or macro configuration")}
 if !s.MatureAdultAssetDesign {return result,errors.New("asset-generation design must be independently specified mature adult")}
 if s.NativeUnit!="BLENDER_SCENE_UNIT_UNCALIBRATED" {return result,errors.New("native coordinates must not silently claim SI units")}
 if len(s.Measurements)==0 {return result,errors.New("missing measured candidates")}
 if !finite(s.SourceMacroValue) {return result,errors.New("nonfinite macro")}
 if s.MacroConfigSHA256!=trust.PinnedMacroConfigSHA256 {return result,errors.New("unadmitted macro source mapping")}
 expected,ok:=trust.PresetToMacro[s.ShapePreset]
 if !ok||math.Abs(expected-s.SourceMacroValue)>1e-12 {return result,errors.New("pinned source macro contradicts shape label")}
 // These labels name source presets, not a person's identity or sex.
 registered,hasScale:=trust.ScaleByID[s.ScaleRecordID]
 validScale:=hasScale&&registered.Admitted&&registered.SourceSHA256==s.SourceSceneSHA256&&
  finite(registered.CentimetersPerNative)&&registered.CentimetersPerNative>0
 if s.ClaimedCentimetersPerNative!=nil {
  if !finite(*s.ClaimedCentimetersPerNative)||!validScale||
      math.Abs(*s.ClaimedCentimetersPerNative-registered.CentimetersPerNative)>1e-9 {
   return result,errors.New("untrusted, mismatched or nonfinite physical scale claim")
  }
 }
 qualified:=0;unknown:=0;verifiedCentimeterMeasurements:=0
 for i,m:=range s.Measurements {
  if m.Region==""||m.Method==""||!finite(m.NativeValue)||m.NativeValue<=0 {
   return result,fmt.Errorf("invalid native measure %d",i)
  }
  key:=m.Region+"|"+m.Method
  if trust.QualifiedRegionMethods[key] {qualified++}else{unknown++}
  if m.ClaimedCentimeters!=nil {
   if !validScale||s.ClaimedCentimetersPerNative==nil {return result,fmt.Errorf("centimeter claim %d lacks explicit admitted scale",i)}
   target:=m.NativeValue*registered.CentimetersPerNative
   if !finite(*m.ClaimedCentimeters)||math.Abs(target-*m.ClaimedCentimeters)>1e-6*math.Max(1,target) {
    return result,fmt.Errorf("unit conversion contradiction %d",i)
   }
   if m.UncertaintyCentimeters==nil||!finite(*m.UncertaintyCentimeters)||*m.UncertaintyCentimeters<=0 {
    return result,fmt.Errorf("unqualified uncertainty %d",i)
   }
   verifiedCentimeterMeasurements++
  }
  if m.UncertaintyCentimeters!=nil && m.ClaimedCentimeters==nil {
   return result,fmt.Errorf("unitless uncertainty claim %d",i)
  }
 }
 result.QualifiedLandmarkMethods=qualified
 result.UnknownLandmarkMethods=unknown
 if validScale && verifiedCentimeterMeasurements>0 {
  result.UnitConversion="PASS_NUMERIC_CONVERSION_ONLY_NOT_ANATOMY"
  result.Status="PASS_ADMITTED_NUMERIC_CONVERSION_ONLY__HOLD_PHYSICAL_ACCEPTANCE"
 } else if validScale {
  // Trusted scale metadata is NOT a verified centimeter conversion by itself.
  result.UnitConversion="UNKNOWN_NO_MEASUREMENT_CONVERSION"
 } else if s.ClaimedCentimetersPerNative==nil {result.UnitConversion="UNKNOWN_NATIVE_ONLY"}
 if unknown>0 {result.Status="UNKNOWN_UNQUALIFIED_LANDMARK_METHOD__HOLD_PHYSICAL_ACCEPTANCE"}
 if s.HeldoutStatus=="NOT_TESTED"||s.OODStatus=="NOT_TESTED" {
  result.FullBodyOOD="NOT_TESTED_HOLD"
 }
 return result,nil
}
