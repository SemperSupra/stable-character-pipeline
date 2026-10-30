package bridge
import (
 "encoding/json"
 "strings"
 "testing"
)
func good() Input {return Input{Schema:"scp.search_projection_handoff.v1",PlanRef:"fixture:plan@sha",AdapterSourceRef:"fixture:adapter@sha",CPEProjectionRef:"fixture:synthetic",TargetID:"fixture-provider",TargetOrigin:"https://search.example.org",FormLanguage:"th",Term:"การเดิน",SourceEvidenceRef:"fixture:lexicon",Classification:"public_synthetic",Operation:"search_only"}}
func allow()map[string]bool{return map[string]bool{"https://search.example.org":true}}
func TestSyntheticOnlyRedaction(t *testing.T){
 r,e:=Check(good(),allow());if e!=nil{t.Fatal(e)}
 if r.Status!="OFFLINE_PUBLIC_HANDOFF_OK"||r.OutboundCalls!=0||r.RawSearchTermPersisted||r.ConceptAuthorityMutation||len(r.TermDigest)!=64{t.Fatalf("invalid receipt %+v",r)}
 b,_:=json.Marshal(r);if strings.Contains(string(b),"การเดิน"){t.Fatal("private term serialized into public receipt")}
}
func TestDisclosureAndCapabilityHolds(t *testing.T){
 cases:=[]struct{name string;change func(*Input)}{
  {"private",func(x *Input){x.Classification="private_protected"}},
  {"user",func(x *Input){x.Classification="user_data"}},
  {"wrong origin",func(x *Input){x.TargetOrigin="https://evil.example.net"}},
  {"host injection",func(x *Input){x.TargetOrigin="https://search.example.org@evil.example.net"}},
  {"url query",func(x *Input){x.TargetOrigin="https://search.example.org/?token=secret"}},
  {"write",func(x *Input){x.Operation="upload"}},
  {"missing provenance",func(x *Input){x.CPEProjectionRef=""}},
  {"control char",func(x *Input){x.Term="walk\nheader"}},
  {"unsupported language",func(x *Input){x.FormLanguage="en US"}},
  {"forged approval",func(x *Input){x.DisclosureApprovalRef="claimed:review"}},
  {"huge",func(x *Input){x.Term=strings.Repeat("w",81)}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){x:=good();tc.change(&x);r,err:=Check(x,allow());if err==nil||r.Status!="HOLD"||r.OutboundCalls!=0{t.Fatalf("not denied: %+v %v",r,err)}})}
}
