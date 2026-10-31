package releaseproof

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "strings"
 "github.com/sempersupra/stable-character-pipeline/releasegate"
)
const Schema="scp.release-proof.v1"
const PolicySchema="scp.trust-policy.v1"
const MaximumJSON=1<<20
const MaximumEvidence=8<<20
var label=regexp.MustCompile(`^[a-z][a-z0-9_-]{0,63}$`)
var sha=regexp.MustCompile(`^sha256:[a-f0-9]{64}$`)
type Proof struct {
 Schema string `json:"schema"`
 Gate string `json:"gate"`
 SourceSHA string `json:"source_sha"`
 ImageDigest string `json:"image_digest"`
 Scope string `json:"scope"`
 EvidenceSHA string `json:"evidence_sha"`
 Issuer string `json:"issuer"`
 Signature string `json:"signature"`
}
type TrustPolicy struct {
 Schema string `json:"schema"`
 Assignments map[string]string `json:"assignments"`
 Keys map[string]string `json:"keys"`
}
type Decision struct {Status string `json:"status"`; Code string `json:"code"`}
func tokenTree(d *json.Decoder)error{
 t,err:=d.Token();if err!=nil{return err}
 dl,ok:=t.(json.Delim);if !ok{return nil}
 switch dl{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   token,err:=d.Token();if err!=nil{return err}
   key,ok:=token.(string);if !ok{return errors.New("invalid key")}
   if seen[key]{return fmt.Errorf("duplicate key: %s",key)};seen[key]=true
   if err:=tokenTree(d);err!=nil{return err}
  }
  _,err=d.Token();return err
 case '[':
  for d.More(){if err:=tokenTree(d);err!=nil{return err}}
  _,err=d.Token();return err
 }
 return errors.New("bad JSON delimiter")
}
func DecodeStrict(r io.Reader, v any) error {
 raw,err:=io.ReadAll(io.LimitReader(r,MaximumJSON+1));if err!=nil{return err}
 if len(raw)>MaximumJSON{return errors.New("oversized JSON")}
 a:=json.NewDecoder(bytes.NewReader(raw))
 if err:=tokenTree(a);err!=nil{return err}
 if _,err:=a.Token();err!=io.EOF{return errors.New("trailing JSON")}
 b:=json.NewDecoder(bytes.NewReader(raw));b.DisallowUnknownFields()
 return b.Decode(v)
}
func DecodeFile(path string,v any)error{
 f,err:=os.Open(path);if err!=nil{return err};defer f.Close()
 return DecodeStrict(f,v)
}
func Digest(raw []byte)string{d:=sha256.Sum256(raw);return "sha256:"+hex.EncodeToString(d[:])}
func Payload(p Proof)[]byte{
 return []byte(strings.Join([]string{Schema,p.Gate,p.SourceSHA,p.ImageDigest,p.Scope,p.EvidenceSHA,p.Issuer},"\n")+"\n")
}
func readRegular(path string,limit int64)([]byte,error){
 st,err:=os.Lstat(path)
 if err!=nil{return nil,err}
 if !st.Mode().IsRegular(){return nil,errors.New("not regular file")}
 if st.Size()>limit{return nil,errors.New("file too large")}
 f,err:=os.Open(path);if err!=nil{return nil,err};defer f.Close()
 raw,err:=io.ReadAll(io.LimitReader(f,limit+1))
 if err!=nil||int64(len(raw))>limit{return nil,errors.New("file read limit")}
 return raw,nil
}
func Verify(m releasegate.Manifest,p TrustPolicy,proofDir,evidenceDir string)Decision{
 fail:=func(code string)Decision{return Decision{Status:"FAIL",Code:code}}
 decision:=releasegate.Validate(m)
 if decision.Status=="UNKNOWN"{return Decision{Status:"UNKNOWN",Code:"DRAFT_NOT_PROMOTED"}}
 if decision.Status!="PASS"{return fail("STRUCTURAL_MANIFEST_"+decision.Code)}
 if p.Schema!=PolicySchema||len(p.Assignments)!=len(releasegate.RequiredGates){return fail("TRUST_POLICY_INVALID")}
 for _,g:=range releasegate.RequiredGates{
  signer,ok:=p.Assignments[g]
  if !ok||!label.MatchString(signer){return fail("TRUST_POLICY_MISSING_ASSIGNMENT")}
  if _,ok:=p.Keys[signer];!ok{return fail("TRUST_POLICY_MISSING_KEY")}
 }
 // Separate release decision makers from the original producer's own witness.
 original:=p.Assignments["build"]
 for _,g:=range []string{"behavior","security","custody","deployment"}{
  if p.Assignments[g]==original{return fail("INDEPENDENCE_VIOLATION")}
 }
 for _,g:=range []string{"behavior","security","custody","deployment"}{
  for _,h:=range []string{"behavior","security","custody","deployment"}{
   if h!=g&&p.Assignments[h]==p.Assignments[g]{return fail("INDEPENDENCE_VIOLATION")}
  }
 }
 for _,gate:=range releasegate.RequiredGates{
  proofRaw,err:=readRegular(filepath.Join(proofDir,gate+".json"),MaximumJSON)
  if err!=nil{return fail("PROOF_FILE_UNAVAILABLE_"+strings.ToUpper(gate))}
  if Digest(proofRaw)!=m.Gates[gate].ReceiptSHA{return fail("PROOF_HASH_MISMATCH_"+strings.ToUpper(gate))}
  var proof Proof
  if err:=DecodeStrict(bytes.NewReader(proofRaw),&proof);err!=nil{return fail("PROOF_ENVELOPE_INVALID_"+strings.ToUpper(gate))}
  if proof.Schema!=Schema||proof.Gate!=gate||proof.SourceSHA!=m.SourceSHA||proof.ImageDigest!=m.ImageDigest||proof.Scope!=m.Scope||
     !sha.MatchString(proof.EvidenceSHA)||proof.Issuer!=p.Assignments[gate]||!label.MatchString(proof.Issuer){
   return fail("PROOF_BINDING_MISMATCH_"+strings.ToUpper(gate))
  }
  evidenceRaw,err:=readRegular(filepath.Join(evidenceDir,gate+".bin"),MaximumEvidence)
  if err!=nil{return fail("EVIDENCE_UNAVAILABLE_"+strings.ToUpper(gate))}
  if Digest(evidenceRaw)!=proof.EvidenceSHA{return fail("EVIDENCE_SHA_MISMATCH_"+strings.ToUpper(gate))}
  keyRaw,err:=hex.DecodeString(p.Keys[proof.Issuer])
  if err!=nil||len(keyRaw)!=ed25519.PublicKeySize{return fail("TRUST_KEY_INVALID_"+strings.ToUpper(gate))}
  sig,err:=base64.StdEncoding.Strict().DecodeString(proof.Signature)
  if err!=nil||len(sig)!=ed25519.SignatureSize||!ed25519.Verify(ed25519.PublicKey(keyRaw),Payload(proof),sig){
   return fail("ISSUER_SIGNATURE_INVALID_"+strings.ToUpper(gate))
  }
 }
 return Decision{Status:"PASS",Code:"SIGNED_BYTE_EVIDENCE_VERIFIED_NOT_OWNER_PROMOTION"}
}
