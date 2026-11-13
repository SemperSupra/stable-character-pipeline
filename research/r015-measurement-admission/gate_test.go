package r015gate
import "testing"
func qualified() Evidence {return Evidence{AdultAsserted:true,RightsKnown:true,EvaluatedMesh:true,NativeReopened:true,IndependentScaleCalibrated:true,OutOfDistributionKnown:true,HeldoutIndependent:true,Measurements:[]Measurement{{Name:"stature",Value:170,Unit:"cm",Method:"evaluated_mesh_landmarks",SourceSHA:"sha256:fixture",LandmarkProvenance:"synthetic:heel_to_crown"}}}}
func TestQualifiedStructuralOnly(t *testing.T){if r:=Check(qualified());r.Status!=Pass{t.Fatalf("%+v",r)}}
func TestFailClosedControls(t *testing.T){
 cases:=[]struct{name string;modify func(*Evidence);expect Status}{
 {"no_adult",func(e *Evidence){e.AdultAsserted=false},Reject},
 {"unknown_rights",func(e *Evidence){e.RightsKnown=false},Unknown},
 {"raw_base_not_evaluated",func(e *Evidence){e.EvaluatedMesh=false},Unknown},
 {"not_reopened",func(e *Evidence){e.NativeReopened=false},Unknown},
 {"blender_units",func(e *Evidence){e.IndependentScaleCalibrated=false;e.Measurements[0].Unit="BU"},Unknown},
 {"no_ood",func(e *Evidence){e.OutOfDistributionKnown=false},Unknown},
 {"leaked_holdout",func(e *Evidence){e.HeldoutIndependent=false},Unknown},
 {"no_landmarks",func(e *Evidence){e.Measurements[0].LandmarkProvenance=""},Unknown},
 {"invalid_value",func(e *Evidence){e.Measurements[0].Value=-1},Reject},
 {"duplicates",func(e *Evidence){e.Measurements=append(e.Measurements,e.Measurements[0])},Reject},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){e:=qualified();tc.modify(&e);if r:=Check(e);r.Status!=tc.expect{t.Fatalf("got %+v want %s",r,tc.expect)}})}
}
