package main

import(
  "encoding/json"
  "os"
  "testing"
)

func fixture(t *testing.T) Manifest {
 t.Helper()
 b,err:=os.ReadFile("candidates.json")
 if err!=nil{t.Fatal(err)}
 m,err:=decode(b)
 if err!=nil{t.Fatal(err)}
 return m
}
func TestValidSourceOnly(t *testing.T){
 b,err:=os.ReadFile("candidates.json")
 if err!=nil{t.Fatal(err)}
 r,err:=run(b)
 if err!=nil{t.Fatal(err)}
 if r.CandidateCount!=5||r.WeightDownloads!=0||r.ModelInferences!=0||r.GPUExecutions!=0{t.Fatal("source survey incorrectly claimed model inference")}
 if r.Status!="SOURCE_RIGHTS_REVIEW_ONLY_NOT_MODEL_INFERENCE"{t.Fatal("incorrect qualification classification")}
 for _,c:=range r.Results{
  if c.Admission!="METADATA_ONLY_NO_WEIGHTS_NO_PRIVATE_RUNNERS"||c.ActualInference!="NOT_TESTED"{t.Fatalf("mislabelled admission %s",c.ID)}
 }
}
func TestForbiddenActions(t *testing.T){
 for _,key:=range []string{"weights","media","inference","private","paid"}{
  m:=fixture(t)
  switch key{
   case "weights":m.FetchWeights=true
   case "media":m.FetchSourceMedia=true
   case "inference":m.ExecuteModelInference=true
   case "private":m.AllowPrivateInputs=true
   case "paid":m.AllowPaidCompute=true
  }
  if err:=validate(m);err==nil{t.Fatal("accepted unsafe action "+key)}
 }
}
func TestRightsAndGPUFailClosed(t *testing.T){
 m:=fixture(t)
 m.Candidates[0].SourceMediaRights=""
 if err:=validate(m);err==nil{t.Fatal("unreviewed source/media rights accepted")}
 m=fixture(t)
 m.Candidates[1].WeightsTerms=""
 if err:=validate(m);err==nil{t.Fatal("missing weight terms accepted")}
 m=fixture(t)
 m.Candidates[2].TargetRigRights=""
 if err:=validate(m);err==nil{t.Fatal("missing rig rights accepted")}
 m=fixture(t)
 n:=-1.0
 m.Candidates[0].GPUMinVRAMGB=&n
 if err:=validate(m);err==nil{t.Fatal("invalid GPU claim accepted")}
}
func TestInferenceAndLicenseLaundering(t *testing.T){
 m:=fixture(t)
 m.Candidates[3].ActualInferenceStatus="PASS"
 if err:=validate(m);err==nil{t.Fatal("unsupported model inference evidence accepted")}
 m=fixture(t)
 m.Candidates[0].CodeLicense="ALL_RIGHTS_CLEARED"
 if err:=validate(m);err==nil{t.Fatal("rights laundering accepted")}
 m=fixture(t)
 m.Candidates[0].CodeLicenseEvidence="https://attacker.invalid/rights"
 if err:=validate(m);err==nil{t.Fatal("untrusted license evidence source accepted")}
 m=fixture(t)
 m.Candidates[1].ID=m.Candidates[0].ID
 if err:=validate(m);err==nil{t.Fatal("duplicate model accepted")}
}
func TestUnknownPropertiesAndAppendedJSON(t *testing.T){
 b,err:=os.ReadFile("candidates.json")
 if err!=nil{t.Fatal(err)}
 var x map[string]any
 if err:=json.Unmarshal(b,&x);err!=nil{t.Fatal(err)}
 x["permit_secret_exfiltration"]=true
 mutated,_:=json.Marshal(x)
 if _,err:=decode(mutated);err==nil{t.Fatal("unknown manifest field accepted")}
 if _,err:=decode(append(b,[]byte("{}")...));err==nil{t.Fatal("appended approval object accepted")}
}
