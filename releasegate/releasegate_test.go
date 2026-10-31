package releasegate
import ("bytes";"encoding/json";"strings";"testing")
func golden()Manifest{
 m:=Manifest{Schema:Schema,Phase:"candidate",Scope:"public-synthetic",SourceSHA:strings.Repeat("a",40),ImageDigest:"sha256:"+strings.Repeat("b",64),Gates:map[string]Evidence{}}
 for _,k:=range RequiredGates{m.Gates[k]=Evidence{Status:"PASS",ReceiptSHA:"sha256:"+strings.Repeat("c",64)}}
 return m
}
func TestCandidatePass(t *testing.T){if v:=Validate(golden());v.Status!="PASS"{t.Fatal(v)}}
func TestDraftCannotPromote(t *testing.T){m:=golden();m.Phase="draft";m.Gates["behavior"]=Evidence{Status:"UNKNOWN"};if v:=Validate(m);v.Status!="UNKNOWN"{t.Fatal(v)}}
func TestHoldAgainstFalsePromotion(t *testing.T){
 cases:=[]struct{name string;f func(*Manifest);code string}{
 {"missing gate",func(m *Manifest){delete(m.Gates,"behavior")},"MISSING_GATE_BEHAVIOR"},
 {"unknown gait",func(m *Manifest){m.Gates["behavior"]=Evidence{Status:"UNKNOWN"}},"UNQUALIFIED_GATE_BEHAVIOR"},
 {"failed rights",func(m *Manifest){m.Gates["security"]=Evidence{Status:"FAIL"}},"UNQUALIFIED_GATE_SECURITY"},
 {"receipt absent",func(m *Manifest){m.Gates["render"]=Evidence{Status:"PASS"}},"PASS_WITHOUT_RECEIPT"},
 {"wrong digest",func(m *Manifest){m.ImageDigest="sha256:BAD"},"INVALID_IMAGE_DIGEST"},
 {"missing image",func(m *Manifest){m.ImageDigest=""},"IMAGE_DIGEST_REQUIRED"},
 {"bad source",func(m *Manifest){m.SourceSHA=strings.Repeat("a",39)},"INVALID_SOURCE_SHA"},
 {"wrong schema",func(m *Manifest){m.Schema="cmp.assessment-result.v1"},"SCHEMA_MISMATCH"},
 {"invalid status",func(m *Manifest){m.Gates["custody"]=Evidence{Status:"YES"}},"INVALID_GATE_STATUS"},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){m:=golden();tc.f(&m);v:=Validate(m);if v.Code!=tc.code{t.Fatalf("got %+v want %s",v,tc.code)}})}
}
func TestStrictEnvelope(t *testing.T){
 cases:=[]string{
  `{"schema":"one","schema":"two"}`,
  `{"gates":{"behavior":{"status":"PASS","status":"FAIL"}}}`,
  `{"schema":"foo"}{"schema":"bar"}`,
  `{"schema":"foo","host_private":"oops"}`,
  strings.Repeat("x",(1<<20)+1),
 }
 for i,s:=range cases{
  _,err:=Parse(strings.NewReader(s))
  if i==3 {if err==nil{t.Fatal("expected non-JSON malformed")};continue}
  if err==nil{t.Fatalf("case %d erroneously parsed",i)}
 }
}
func TestUnknownField(t *testing.T){raw:=[]byte(`{"schema":"scp.release-manifest.v1","phase":"draft","scope":"public-synthetic","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","gates":{},"unrecognized_secret":"x"}`);if _,err:=Parse(bytes.NewReader(raw));err==nil{t.Fatal("unknown field accepted")}}
func TestRoundTrip(t *testing.T){b,err:=json.Marshal(golden());if err!=nil{t.Fatal(err)};v,err:=Check(bytes.NewReader(b));if err!=nil||v.Status!="PASS"{t.Fatalf("%v %v",v,err)}}
