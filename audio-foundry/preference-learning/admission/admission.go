// Package admission implements a fail-closed public synthetic experiment boundary.
// It is an additional custody gate, not a substitute for legal rights review.
package admission
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "strings"
)
const Public = "PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"

// Manifest is out-of-band reviewed, source-pinned proof of which exact bytes and
// reference hashes a disposable PUBLIC synthetic runner is allowed to see.
type Manifest struct {
 AllowedPayloadSHA256 map[string]bool
 AllowedReferenceSHA256 map[string]bool
}
func isSHA(s string) bool {
 if len(s)!=64 || strings.ToLower(s)!=s{return false}
 x,e:=hex.DecodeString(s);return e==nil&&len(x)==32
}
func parseUniqueObject(buf []byte)(map[string]json.RawMessage,error){
 if len(buf)==0||len(buf)>1<<20{return nil,errors.New("bounded JSON object required")}
 dec:=json.NewDecoder(bytes.NewReader(buf));dec.DisallowUnknownFields()
 tok,e:=dec.Token();if e!=nil||tok!=json.Delim('{'){return nil,errors.New("top-level JSON object required")}
 obj:=map[string]json.RawMessage{}
 for dec.More(){
  tok,e=dec.Token();if e!=nil{return nil,e}
  key,ok:=tok.(string);if !ok{return nil,errors.New("invalid JSON key")}
  if _,exists:=obj[key];exists{return nil,fmt.Errorf("duplicate key: %s",key)}
  var raw json.RawMessage;if e=dec.Decode(&raw);e!=nil{return nil,e};obj[key]=raw
 }
 tok,e=dec.Token();if e!=nil||tok!=json.Delim('}') {return nil,errors.New("invalid object closure")}
 if _,e=dec.Token();e!=io.EOF{return nil,errors.New("trailing JSON content")}
 return obj,nil
}
func getString(obj map[string]json.RawMessage,key string)(string,error){
 var s string
 raw,ok:=obj[key];if !ok{return "",fmt.Errorf("missing %s",key)}
 if e:=json.Unmarshal(raw,&s);e!=nil||s==""{return "",fmt.Errorf("invalid %s",key)}
 return s,nil
}
// AdmitPublicIntent checks exact bytes against a pre-reviewed SHA allowlist and
// checks reference classification/custody. Caller MUST separately approve rights.
// Never pass human preference events or real-person references to public runs.
func AdmitPublicIntent(buf []byte, manifest Manifest) (string,error){
 sum:=fmt.Sprintf("%x",sha256.Sum256(buf))
 if !manifest.AllowedPayloadSHA256[sum]{return "",errors.New("payload not authorized for public synthetic runner")}
 if e:=rejectNestedDuplicates(buf);e!=nil{return "",e}
 obj,e:=parseUniqueObject(buf);if e!=nil{return "",e}
 if e:=validateIntentShape(obj);e!=nil{return "",e}
 schema,e:=getString(obj,"schema");if e!=nil||schema!="audio.intent.v0"{return "",errors.New("only reviewed audio.intent.v0 is eligible")}
 c,e:=getString(obj,"classification");if e!=nil||c!=Public{return "",errors.New("protected or unknown intent class")}
 if _,e=getString(obj,"description");e!=nil{return "",e}
 var refs []struct{SHA string `json:"artifact_sha256"`;Class string `json:"classification"`;Rights string `json:"rights_receipt_ref"`}
 if raw,exists:=obj["reference_examples"];exists {
  if e=json.Unmarshal(raw,&refs);e!=nil||refs==nil{return "",errors.New("invalid reference list")}
 }
 for _,r:=range refs{
  if !isSHA(r.SHA)||r.Class!=Public||strings.TrimSpace(r.Rights)==""||!manifest.AllowedReferenceSHA256[r.SHA]{return "",errors.New("unapproved or protected reference")}
 }
 return sum,nil
}
