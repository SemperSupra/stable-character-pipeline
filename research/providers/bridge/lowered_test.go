package bridge
import(
 "encoding/json"
 "net/url"
 "strings"
 "testing"
)
func fixture() Lowered{
 var q LoweredRequest
 q.LocalRef="synthetic-execution:clause-1:0";q.Method="GET";q.URL="https://searx.example.org/search";q.Params.Q="Gehbewegung";q.Params.Format="json";q.Params.PageNo=1;q.Params.Language="de"
 vals:=url.Values{};vals.Set("q",q.Params.Q);vals.Set("format","json");vals.Set("pageno","1");vals.Set("language","de")
 q.RenderedURL=q.URL+"?"+vals.Encode();q.ConceptID="public-synthetic-walk";q.Relation="must";q.Purpose="candidate_retrieval"
 return Lowered{SchemaVersion:"experimental-v0",ExecutionID:"synthetic-execution",TargetCapabilityProfileRef:"searx-test@v1",PreflightStatus:"ready",
 Requests:[]LoweredRequest{q},Privacy:LoweredPrivacy{PolicyContextForwarded:false,LocalRequestRefsOutbound:false,ExternalDisclosure:json.RawMessage(`"query"`)}}
}
func check(p Lowered)(LoweredReceipt,error) {
 b,err:=ExportSyntheticPacket(p);if err!=nil{return LoweredReceipt{},err}
 return ValidateLowered(b,"synthetic-execution","searx-test@v1","https://searx.example.org","public_synthetic",3)
}
func TestActualLowererContractShape(t *testing.T){
 out,err:=check(fixture())
 if err!=nil{t.Fatal(err)}
 if out.State!="SOURCE_ADAPTER_SHAPE_OK"||out.NetworkCalls!=0||out.ConceptAuthorityChanged||out.SourceTermsPersisted||len(out.QueryDigests)!=1||out.LanguageCounts["de"]!=1{t.Fatalf("false claim: %+v",out)}
 b,_:=json.Marshal(out)
 if strings.Contains(string(b),"Gehbewegung")||strings.Contains(string(b),"public-synthetic-walk"){t.Fatal("outbound concept/query leaked")}
}
func TestSourceBoundDenials(t *testing.T){
 scenarios:=[]struct{name string;change func(*Lowered)}{
  {"blocked",func(p *Lowered){p.PreflightStatus="blocked"}},
  {"pending postchecks",func(p *Lowered){p.PreflightStatus="ready_with_postchecks"}},
  {"unlowered clause",func(p *Lowered){p.NotLowered=[]json.RawMessage{json.RawMessage(`{"reason":"unsupported"}`)}}},
  {"extra provider",func(p *Lowered){p.Requests[0].URL="https://other.example.org/search"}},
  {"malicious rendered host",func(p *Lowered){p.Requests[0].RenderedURL="https://searx.example.org@evil.invalid/search?q=bad"}},
  {"inconsistent query",func(p *Lowered){p.Requests[0].Params.Q="something new"}},
  {"extra url token",func(p *Lowered){p.Requests[0].RenderedURL+="&token=secret"}},
  {"private write",func(p *Lowered){p.Requests[0].Method="POST"}},
  {"language",func(p *Lowered){p.Requests[0].Params.Language="en"}},
  {"privacy",func(p *Lowered){p.Privacy.PolicyContextForwarded=true}},
  {"ref disclosure",func(p *Lowered){p.Privacy.LocalRequestRefsOutbound=true}},
  {"missing disclosure",func(p *Lowered){p.Privacy.ExternalDisclosure=nil}},
  {"duplicate",func(p *Lowered){p.Requests=append(p.Requests,p.Requests[0])}},
 }
 for _,tc:=range scenarios {
  t.Run(tc.name,func(t *testing.T){p:=fixture();tc.change(&p);o,err:=check(p);if err==nil||o.State!="HOLD"||o.NetworkCalls!=0{t.Fatalf("not held: %+v %v",o,err)}})
 }
}
func TestPrivateClassificationIsNeverAdmitted(t *testing.T){
 p:=fixture();b,_:=json.Marshal(p)
 if _,err:=ValidateLowered(b,"synthetic-execution","searx-test@v1","https://searx.example.org","private_protected",3);err==nil {t.Fatal("private source leak")}
}
