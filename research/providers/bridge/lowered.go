package bridge

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "net/url"
 "strings"
)
type Lowered struct {
 SchemaVersion string `json:"schema_version"`
 ExecutionID string `json:"execution_id"`
 TargetCapabilityProfileRef string `json:"target_capability_profile_ref"`
 PreflightStatus string `json:"preflight_status"`
 Requests []LoweredRequest `json:"requests"`
 NotLowered []json.RawMessage `json:"not_lowered"`
 Privacy LoweredPrivacy `json:"privacy"`
}
type LoweredRequest struct {
 LocalRef string `json:"local_request_ref"`
 Method string `json:"method"`
 URL string `json:"url"`
 Params struct {
  Q string `json:"q"`
  Format string `json:"format"`
  PageNo int `json:"pageno"`
  Language string `json:"language,omitempty"`
 } `json:"params"`
 RenderedURL string `json:"rendered_url"`
 ConceptID string `json:"concept_id"`
 Relation string `json:"relation"`
 Purpose string `json:"purpose"`
}
type LoweredPrivacy struct {
 PolicyContextForwarded bool `json:"policy_context_forwarded"`
 LocalRequestRefsOutbound bool `json:"local_request_refs_are_outbound_parameters"`
 ExternalDisclosure json.RawMessage `json:"external_disclosure"`
}
type LoweredReceipt struct {
 Schema string `json:"schema"`
 State string `json:"state"`
 QueryDigests []string `json:"query_digests"`
 LanguageCounts map[string]int `json:"language_counts"`
 NetworkCalls int `json:"network_calls"`
 SourceTermsPersisted bool `json:"source_terms_persisted"`
 ConceptAuthorityChanged bool `json:"concept_authority_changed"`
 Reason string `json:"reason"`
}
func ValidateLowered(data []byte,expectedExecutionID,expectedTargetRef,targetOrigin,sourceClass string,maxQueries int)(LoweredReceipt,error){
 out:=LoweredReceipt{Schema:"scp.searxng_lowered_research_receipt.v1",State:"HOLD",LanguageCounts:map[string]int{},NetworkCalls:0,SourceTermsPersisted:false,ConceptAuthorityChanged:false}
 deny:=func(reason string)(LoweredReceipt,error){out.Reason=reason;return out,errors.New(reason)}
 if sourceClass!="public_synthetic"||expectedExecutionID==""||expectedTargetRef=="" {return deny("source and projection scope not public-synthetic")}
 origin,err:=url.Parse(targetOrigin)
 if err!=nil||origin.Scheme!="https"||origin.Host==""||origin.User!=nil||origin.Path!=""||origin.RawQuery!="" {return deny("invalid approved SearXNG origin")}
 if len(data)>131072||maxQueries<1||maxQueries>8 {return deny("unbounded packet")}
 dec:=json.NewDecoder(bytes.NewReader(data));dec.DisallowUnknownFields()
 var packet Lowered
 if err:=dec.Decode(&packet);err!=nil{return deny("unrecognized source adapter packet")}
 if dec.More(){return deny("trailing unknown input")}
 if packet.SchemaVersion!="experimental-v0"||packet.ExecutionID!=expectedExecutionID||
  packet.TargetCapabilityProfileRef!=expectedTargetRef||packet.PreflightStatus!="ready"||len(packet.NotLowered)!=0||
  len(packet.Requests)==0||len(packet.Requests)>maxQueries {return deny("source adapter revision, preflight or budget not admitted")}
 if packet.Privacy.PolicyContextForwarded||packet.Privacy.LocalRequestRefsOutbound||len(packet.Privacy.ExternalDisclosure)==0||string(packet.Privacy.ExternalDisclosure)=="null" {return deny("source adapter privacy contract not verified")}
 seen:=map[string]bool{}
 for _,r:=range packet.Requests {
  if r.LocalRef==""||r.Method!="GET"||r.Purpose!="candidate_retrieval"||
    (r.Relation!="must"&&r.Relation!="should")||r.ConceptID==""||
    r.Params.Q==""||len([]rune(r.Params.Q))>80||strings.ContainsAny(r.Params.Q,"\r\n")||
    r.Params.Format!="json"||r.Params.PageNo!=1||r.Params.Language==""||!safeLang(r.Params.Language) {return deny("unsupported request or lexical form")}
  expectedEndpoint:=targetOrigin+"/search"
  if r.URL!=expectedEndpoint {return deny("untrusted provider endpoint")}
  parsed,err:=url.Parse(r.RenderedURL)
  if err!=nil||parsed.Scheme!="https"||parsed.Host!=origin.Host||parsed.Path!="/search"||
   parsed.User!=nil||parsed.Fragment!="" {return deny("untrusted rendered URL")}
  q:=parsed.Query()
  if len(q)!=4||len(q["q"])!=1||len(q["format"])!=1||len(q["pageno"])!=1||len(q["language"])!=1||
   q.Get("q")!=r.Params.Q||q.Get("format")!="json"||q.Get("pageno")!="1"||
   q.Get("language")!=r.Params.Language {return deny("source URL and request parameters disagree or leak extras")}
  h:=sha256.Sum256([]byte(packet.ExecutionID+"|"+r.LocalRef+"|"+r.Params.Language+"|"+r.Params.Q))
  digest:=hex.EncodeToString(h[:])
  if seen[digest] {return deny("duplicate request observation")}
  seen[digest]=true
  out.QueryDigests=append(out.QueryDigests,digest)
  out.LanguageCounts[r.Params.Language]++
 }
 out.State="SOURCE_ADAPTER_SHAPE_OK"
 out.Reason="offline synthetic adapter-output shape only; no private CPE execution or external query"
 return out,nil
}
func safeLang(s string)bool {
 if len(s)<2||len(s)>12{return false}
 for _,r:=range s{if !(r>='a'&&r<='z')&&r!='-'{return false}}
 return true
}
func ExportSyntheticPacket(in Lowered) ([]byte,error){
 if in.SchemaVersion!="experimental-v0" {return nil,fmt.Errorf("wrong adapter schema")}
 return json.Marshal(in)
}
