// Command evaluate is an offline, source-venue-local contact diagnostic.
// No networking, source acquisition, protected-media serialization or auto-pass.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/SemperSupra/stable-character-pipeline/r014/contactgate"
)

type trustInput struct {
 SceneSHA256 string `json:"scene_sha256"`
 MotionSHA256 string `json:"motion_sha256"`
 SoleMeshSHA256 string `json:"sole_mesh_sha256"`
 CalibrationSHA256 string `json:"calibration_sha256"`
 StanceLabelSHA256 string `json:"stance_label_sha256"`
 PolicySHA256 string `json:"policy_sha256"`
 ReviewerProofSHA256 string `json:"reviewer_proof_sha256"`
 Reviewed bool `json:"reviewed"`
}

type receipt struct {
 Schema string `json:"schema"`
 RecordSHA256 string `json:"input_record_sha256"`
 TrustSHA256 string `json:"input_trust_sha256"`
 Metrics contactgate.Metrics `json:"metrics"`
 Rights string `json:"rights"`
 CanonicalCharacterPack string `json:"canonical_character_pack"`
}

func digest(b []byte) string {
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
func decodeTrust(b []byte)(trustInput,error){
 var v trustInput
 d:=json.NewDecoder(bytes.NewReader(b))
 d.DisallowUnknownFields()
 if e:=d.Decode(&v);e!=nil{return v,e}
 var tail any
 if e:=d.Decode(&tail);e!=io.EOF{return v,errors.New("trailing trust JSON")}
 return v,nil
}
func writeOnce(path string,b []byte)error{
 // Never rewrite an existing differing result; a repeated identical run is idempotent.
 if old,e:=os.ReadFile(path);e==nil {
  if bytes.Equal(old,b){return nil}
  return errors.New("existing output differs; refused overwrite")
 }else if !os.IsNotExist(e){return e}
 parent:=filepath.Dir(path)
 f,e:=os.CreateTemp(parent,".r014-contact-*.tmp")
 if e!=nil{return e}
 tmp:=f.Name()
 defer os.Remove(tmp)
 if e=f.Chmod(0600);e!=nil{f.Close();return e}
 if _,e=f.Write(b);e!=nil{f.Close();return e}
 if e=f.Sync();e!=nil{f.Close();return e}
 if e=f.Close();e!=nil{return e}
 // Hard-link creation is atomic and fails if the output already exists.
 if e=os.Link(tmp,path);e!=nil{
  if os.IsExist(e) {
   old,e2:=os.ReadFile(path)
   if e2==nil&&bytes.Equal(old,b){return nil}
   return errors.New("output race or different existing evidence; refused overwrite")
  }
  return e
 }
 return nil
}
func sameInput(a,b string)bool{
 fa,ea:=os.Stat(a);fb,eb:=os.Stat(b)
 return ea==nil&&eb==nil&&os.SameFile(fa,fb)
}
func execute(args []string)(int,error){
 fs:=flag.NewFlagSet("evaluate",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 recordPath:=fs.String("record","","source-venue-local 285-tick JSON record")
 trustPath:=fs.String("trust","","independently reviewed trust JSON")
 outPath:=fs.String("output","","local immutable result JSON")
 if e:=fs.Parse(args);e!=nil{return 2,e}
 if fs.NArg()!=0||*recordPath==""||*trustPath==""||*outPath==""{
  return 2,errors.New("usage: evaluate -record INPUT.json -trust EXTERNAL_REVIEW.json -output RESULT.json")
 }
 if sameInput(*recordPath,*trustPath)||
  filepath.Clean(*outPath)==filepath.Clean(*recordPath)||
  filepath.Clean(*outPath)==filepath.Clean(*trustPath)||
  sameInput(*outPath,*recordPath)||sameInput(*outPath,*trustPath){
  return 2,errors.New("record, independent trust and output must be distinct files")
 }
 b,e:=os.ReadFile(*recordPath);if e!=nil{return 2,e}
 t,e:=os.ReadFile(*trustPath);if e!=nil{return 2,e}
 record,e:=contactgate.DecodeStrict(b);if e!=nil{return 2,e}
 rawTrust,e:=decodeTrust(t);if e!=nil{return 2,e}
 trusted:=contactgate.Trust{
  SceneSHA256:rawTrust.SceneSHA256,MotionSHA256:rawTrust.MotionSHA256,
  SoleMeshSHA256:rawTrust.SoleMeshSHA256,
  CalibrationSHA256:rawTrust.CalibrationSHA256,
  StanceLabelSHA256:rawTrust.StanceLabelSHA256,
  PolicySHA256:rawTrust.PolicySHA256,
  ReviewerProofSHA256:rawTrust.ReviewerProofSHA256,Reviewed:rawTrust.Reviewed,
 }
 metrics,e:=contactgate.Evaluate(record,trusted)
 if e!=nil{return 2,e}
 res:=receipt{Schema:"r014.contactgate_offline_diagnostic.v1",
  RecordSHA256:digest(b),TrustSHA256:digest(t),
  Metrics:metrics,Rights:"LOCAL_INPUT_ADMISSION_NOT_PROVEN_BY_CLI",
  CanonicalCharacterPack:"HOLD_OWNER_ONLY"}
 output,e:=json.MarshalIndent(res,"","  ");if e!=nil{return 2,e}
 output=append(output,'\n')
 if e=writeOnce(*outPath,output);e!=nil{return 2,e}
 if metrics.Status=="RED_DECLARED_CONTACT_POLICY"{return 3,nil}
 if metrics.Status!="WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS"{
  return 2,errors.New("unknown numeric disposition")
 }
 return 0,nil
}
func main(){
 code,e:=execute(os.Args[1:])
 if e!=nil{fmt.Fprintln(os.Stderr,"contactgate diagnostic:",e)}
 os.Exit(code)
}
