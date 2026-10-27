package envelope

import (
	"encoding/json"
	"strings"
	"testing"
)

func pint(x int) *int { return &x }
func pfloat(x float64) *float64 { return &x }
func fixture() ProofBundle {
	h:=ContentDigest([]byte("original synthetic japanese rig"))
	return ProofBundle{
		Schema:Schema,
		Fixture: FixtureSpec{
			ID:"mmd-g7-synthetic",SourceURI:"urn:synthetic:mmd-g7",SourceSHA256:h,FrameCount:31,
			Semantics: SourceSemantics{NativeFormat:"PMX",NativeBoneLabels:[]string{"腰","ひざ","足首"},
				NativeMorphLabels:[]string{},Units:"source_unit",MetersPerUnit:pfloat(0.08),Axes:"RH_Y_UP",
				FPSNumerator:30,FPSDenominator:1,FrameOrigin:pint(0),
				Rights:SourceRights{AssetRights:"ORIGINAL_SYNTHETIC",
					EvidenceURI:"urn:original:fixture",CloudAllowed:true,RedistributeAllowed:true}},
		},
		Observations:[]EngineObservation{{ID:"blender-f15",Engine:"blender",EngineVersion:"4.5",EvidenceURI:"urn:synthetic:mock",EvidenceSHA256:ContentDigest([]byte("synthetic mock receipt")),
			FixtureSHA256:h,Frame:15,TimeSeconds:pfloat(0.5),Status:"PASS",
			Measured:map[string]float64{"ankle_goal_error":0.012},DeclaredLoss:[]string{}}},
		Metrics:[]MetricEvidence{{ID:"goal-f15",ObservationID:"blender-f15",Oracle:"independent-glb-transform",
			Status:"PASS",Units:"source_unit",Value:pfloat(0.012)}},
		Verdict:"PASS",
	}
}
func TestRoundtripNativeLabelsAndFrameOriginZero(t *testing.T) {
	x:=fixture()
	raw,err:=json.Marshal(x);if err!=nil{t.Fatal(err)}
	got,err:=DecodeStrict(raw);if err!=nil{t.Fatal(err)}
	again,err:=json.Marshal(got);if err!=nil{t.Fatal(err)}
	if string(raw)!=string(again){t.Fatal("round-trip changed evidence")}
	if got.Fixture.Semantics.NativeBoneLabels[1]!="ひざ" || *got.Fixture.Semantics.FrameOrigin!=0 {
		t.Fatal("native Japanese label or valid frame zero corrupted")
	}
}
func TestRejectInadmissibleSourcesAndFalseProofs(t *testing.T) {
	tests:=[]struct{name string;mutate func(*ProofBundle)}{
		{"no frame origin",func(b *ProofBundle){b.Fixture.Semantics.FrameOrigin=nil}},
		{"fps denominator",func(b *ProofBundle){b.Fixture.Semantics.FPSDenominator=0}},
		{"unknown axis",func(b *ProofBundle){b.Fixture.Semantics.Axes="UNKNOWN"}},
		{"unknown units",func(b *ProofBundle){b.Fixture.Semantics.Units=""}},
		{"scale",func(b *ProofBundle){b.Fixture.Semantics.MetersPerUnit=pfloat(0)}},
		{"wrong native format",func(b *ProofBundle){b.Fixture.Semantics.NativeFormat="FBX"}},
		{"missing source digest",func(b *ProofBundle){b.Fixture.SourceSHA256=""}},
		{"native label duplicated",func(b *ProofBundle){b.Fixture.Semantics.NativeBoneLabels=[]string{"足首","足首"}}},
		{"source ancestry",func(b *ProofBundle){b.Observations[0].FixtureSHA256=ContentDigest([]byte("different"))}},
		{"frame disagreement",func(b *ProofBundle){b.Observations[0].TimeSeconds=pfloat(0.6)}},
		{"frame beyond capture",func(b *ProofBundle){b.Observations[0].Frame=31}},
		{"undisclosed conversion loss",func(b *ProofBundle){b.Observations[0].DeclaredLoss=nil}},
		{"no engine receipt SHA",func(b *ProofBundle){b.Observations[0].EvidenceSHA256=""}},
		{"no engine receipt URI",func(b *ProofBundle){b.Observations[0].EvidenceURI=""}},
		{"unknown engine pass",func(b *ProofBundle){b.Observations[0].Status="UNKNOWN"}},
		{"unmeasured pass",func(b *ProofBundle){b.Observations[0].Measured=map[string]float64{}}},
		{"missing oracle",func(b *ProofBundle){b.Metrics[0].Oracle=""}},
		{"unmeasured metric",func(b *ProofBundle){b.Metrics[0].Value=nil}},
		{"missing observation",func(b *ProofBundle){b.Metrics[0].ObservationID="phantom"}},
		{"unknown metric marked bundle pass",func(b *ProofBundle){b.Metrics[0].Status="NOT_TESTED"}},
		{"unknown rights",func(b *ProofBundle){b.Fixture.Semantics.Rights.AssetRights="UNKNOWN";b.Fixture.Semantics.Rights.CloudAllowed=false;b.Fixture.Semantics.Rights.RedistributeAllowed=false}},
		{"no cloud permission",func(b *ProofBundle){b.Fixture.Semantics.Rights.CloudAllowed=false}},
		{"no derivative permission",func(b *ProofBundle){b.Fixture.Semantics.Rights.RedistributeAllowed=false}},
		{"absent rights witness",func(b *ProofBundle){b.Fixture.Semantics.Rights.EvidenceURI=""}},
		{"invalid final verdict",func(b *ProofBundle){b.Verdict="ACCEPTED"}},
	}
	for _,tc:=range tests {t.Run(tc.name,func(t *testing.T){v:=fixture();tc.mutate(&v);if err:=Validate(v);err==nil {t.Fatal("invalid evidence accepted")}})}
}
func TestUnknownNeverPromoted(t *testing.T) {
	v:=fixture();v.Observations[0].Status="UNKNOWN";v.Metrics[0].Status="UNKNOWN";v.Metrics[0].Value=nil;v.Verdict="UNKNOWN"
	if err:=Validate(v);err!=nil{t.Fatal(err)}
	v.Verdict="PASS";if err:=Validate(v);err==nil{t.Fatal("UNKNOWN promoted to PASS")}
}
func TestStrictJSONUnknownKeyAndTrailingDocument(t *testing.T){
	b,err:=json.Marshal(fixture());if err!=nil{t.Fatal(err)}
	unknown:=strings.Replace(string(b), "\"schema\":", "\"shadow_authority\":true,\"schema\":",1)
	if _,err:=DecodeStrict([]byte(unknown));err==nil{t.Fatal("unknown key accepted")}
	if _,err:=DecodeStrict(append(b, []byte("{}")...));err==nil{t.Fatal("trailing JSON accepted")}
}

func TestExplicitUnknownPhysicalScale(t *testing.T) {
	p:=fixture(); p.Fixture.Semantics.MetersPerUnit=nil
	// The native source remains useful for source-unit distance tests only.
	if err:=Validate(p);err!=nil { t.Fatalf("rejected explicitly unknown physical scale: %v",err) }
	p.Fixture.Semantics.Units="m"
	if err:=Validate(p);err==nil {t.Fatal("physical meters silently inferred from unknown source scale")}
}
