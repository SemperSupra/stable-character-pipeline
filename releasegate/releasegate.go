package releasegate

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "regexp"
 "strings"
)
const Schema = "scp.release-manifest.v1"
var gitSHA = regexp.MustCompile("^[a-f0-9]{40}$")
var digest = regexp.MustCompile("^sha256:[a-f0-9]{64}$")
var RequiredGates = []string{"build","contract","source_motion","render","behavior","audiences","security","custody","deployment"}
type Evidence struct {
 Status string `json:"status"`
 ReceiptSHA string `json:"receipt_sha"`
}
type Manifest struct {
 Schema string `json:"schema"`
 Phase string `json:"phase"`
 Scope string `json:"scope"`
 SourceSHA string `json:"source_sha"`
 ImageDigest string `json:"image_digest,omitempty"`
 Gates map[string]Evidence `json:"gates"`
}
type Decision struct {
 Status string `json:"status"`
 Code string `json:"code"`
}
func uniqueJSONValue(d *json.Decoder) error {
 t, err := d.Token()
 if err != nil {return err}
 del, ok := t.(json.Delim)
 if !ok {return nil}
 switch del {
 case '{':
  seen := map[string]bool{}
  for d.More() {
   k,err:=d.Token(); if err!=nil{return err}
   key,ok:=k.(string);if !ok{return errors.New("object key is not a string")}
   if seen[key] {return fmt.Errorf("duplicate JSON key: %s", key)}
   seen[key]=true
   if err:=uniqueJSONValue(d);err!=nil{return err}
  }
  _,err=d.Token();return err
 case '[':
  for d.More(){if err:=uniqueJSONValue(d);err!=nil{return err}}
  _,err=d.Token();return err
 default: return fmt.Errorf("unexpected JSON delimiter %q",del)
 }
}
func Parse(r io.Reader) (Manifest,error) {
 raw,err:=io.ReadAll(io.LimitReader(r,(1<<20)+1))
 if err!=nil {return Manifest{},err}
 if len(raw)>(1<<20){return Manifest{},errors.New("manifest exceeds 1 MiB")}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if err:=uniqueJSONValue(d);err!=nil{return Manifest{},err}
 if _,err:=d.Token();err!=io.EOF {return Manifest{},errors.New("trailing JSON document")}
 strict:=json.NewDecoder(bytes.NewReader(raw));strict.DisallowUnknownFields()
 var m Manifest
 if err:=strict.Decode(&m);err!=nil{return Manifest{},err}
 return m,nil
}
func Validate(m Manifest) Decision {
 fail:=func(code string)Decision{return Decision{Status:"FAIL",Code:code}}
 if m.Schema!=Schema{return fail("SCHEMA_MISMATCH")}
 if m.Phase!="draft"&&m.Phase!="candidate"&&m.Phase!="released"{return fail("INVALID_PHASE")}
 if m.Scope!="public-synthetic"&&m.Scope!="protected-product"{return fail("INVALID_SCOPE")}
 if !gitSHA.MatchString(m.SourceSHA){return fail("INVALID_SOURCE_SHA")}
 if m.ImageDigest!=""&&!digest.MatchString(m.ImageDigest){return fail("INVALID_IMAGE_DIGEST")}
 if m.Phase!="draft"&&m.ImageDigest==""{return fail("IMAGE_DIGEST_REQUIRED")}
 if len(m.Gates)==0{return fail("NO_GATES")}
 for _,k:=range RequiredGates{if _,ok:=m.Gates[k];!ok{return fail("MISSING_GATE_"+strings.ToUpper(k))}}
 for k,g:=range m.Gates{
  if strings.TrimSpace(k)!=k||k==""{return fail("INVALID_GATE_NAME")}
  if g.Status!="PASS"&&g.Status!="FAIL"&&g.Status!="UNKNOWN"{return fail("INVALID_GATE_STATUS")}
  if g.ReceiptSHA!=""&&!digest.MatchString(g.ReceiptSHA){return fail("INVALID_RECEIPT_SHA")}
  if g.Status=="PASS"&&g.ReceiptSHA==""{return fail("PASS_WITHOUT_RECEIPT")}
  if m.Phase!="draft"&&g.Status!="PASS"{return fail("UNQUALIFIED_GATE_"+strings.ToUpper(k))}
 }
 if m.Phase=="draft"{return Decision{Status:"UNKNOWN",Code:"DRAFT_NOT_PROMOTED"}}
 return Decision{Status:"PASS",Code:"GATES_QUALIFIED"}
}
func Check(r io.Reader)(Decision,error){m,err:=Parse(r);if err!=nil{return Decision{Status:"FAIL",Code:"INVALID_JSON"},err};return Validate(m),nil}
