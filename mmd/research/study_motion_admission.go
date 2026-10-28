// Metadata-only dance/movement source study gate. It NEVER downloads motion,
// never decides owner admission, and never claims source footage is reusable.
// Pure Go stdlib, red probes are compulsory for any GREEN report.
package main
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strings"
)
type Source struct {
 ID string `json:"id"`
 Name string `json:"name"`
 Kind string `json:"kind"`
 Format []string `json:"format"`
 SourceURL string `json:"source_url"`
 RightsURL string `json:"rights_url"`
 LicenseSummary string `json:"license_summary"`
 Scope string `json:"scope"`
 CandidateIDs []string `json:"candidate_ids"`
 FileSHA *string `json:"source_file_sha256"`
 FileVerified bool `json:"file_verified"`
 SourceAdmission string `json:"source_data_admission"`
 PublicRunner string `json:"public_runner"`
 MMDPath string `json:"mmd_path"`
 Risks []string `json:"risks"`
}
type Catalog struct{
 Schema string `json:"schema"`
 DataPolicy string `json:"data_policy"`
 DefaultStatus string `json:"default_status"`
 FirstTrials []string `json:"first_planned_trials"`
 Sources []Source `json:"sources"`
}
func sha(b []byte)string{d:=sha256.Sum256(b);return hex.EncodeToString(d[:])}
func check(c Catalog)error{
 if c.Schema!="scp.mmd.study_motion_source_admission.v1"||c.DataPolicy!="METADATA_ONLY_NO_CAPTURE_BYTES_COPIED"||c.DefaultStatus!="NOT_ADMITTED"{
  return errors.New("unexpected admission authority or metadata-only mode")
 }
 if len(c.Sources)<10||len(c.FirstTrials)!=4{return errors.New("missing candidate source or trial")}
 seen:=map[string]bool{}
 trials:=map[string]bool{}
 for _,x:=range c.FirstTrials{
  if x==""||trials[x]{return errors.New("duplicate/empty trial nomination")};trials[x]=true
 }
 firstCandidates:=map[string]bool{}
 for _,x:=range c.Sources{
  if x.ID==""||seen[x.ID]||len(x.Name)<8||len(x.Format)==0{return fmt.Errorf("bad candidate identity: %q",x.ID)}
  seen[x.ID]=true
  if x.SourceURL==""||!strings.HasPrefix(x.SourceURL,"https://")||
    x.RightsURL==""||!strings.HasPrefix(x.RightsURL,"https://")||len(x.LicenseSummary)<12||
    len(x.Scope)<5||len(x.MMDPath)<12||len(x.Risks)==0{
   return fmt.Errorf("missing source-rights/context/adapter coverage: %s",x.ID)
  }
  if x.FileSHA!=nil||x.FileVerified{return fmt.Errorf("file-level motion falsely verified without bytes: %s",x.ID)}
  if x.SourceAdmission!="NOT_ADMITTED"||!(x.PublicRunner=="HOLD"||x.PublicRunner=="BLOCKED"){
    return fmt.Errorf("source/public execution admission was fabricated: %s",x.ID)
  }
  if strings.Contains(x.MMDPath,"AUTO_QUALIFIED")||strings.Contains(x.LicenseSummary,"public domain all models"){
   return fmt.Errorf("forbidden unearned universal claim: %s",x.ID)
  }
  for _,t:=range x.CandidateIDs{firstCandidates[t]=true}
 }
 for _,t:=range c.FirstTrials{if !firstCandidates[t]{return fmt.Errorf("initial CMU trial missing: %s",t)}}
 if c.Sources[0].ID!="cmu-modern-dance"||c.Sources[0].Scope!="FREE_USE_NO_DATA_RESALE"{return errors.New("first pilot source grant not pinned")}
 return nil
}
func clone(x Catalog)Catalog{
 b,_:=json.Marshal(x);var z Catalog;_ =json.Unmarshal(b,&z);return z
}
func runNegative(c Catalog)([]string,error){
 tests:=[]struct{name string;mutate func(*Catalog)}{
  {"invented_real_capture_admission",func(x *Catalog){x.Sources[0].SourceAdmission="PUBLIC_ADMITTED"}},
  {"bypass_public_runner_hold",func(x *Catalog){x.Sources[0].PublicRunner="GO"}},
  {"forged_file_sha",func(x *Catalog){v:=strings.Repeat("a",64);x.Sources[0].FileSHA=&v}},
  {"missing_rights_url",func(x *Catalog){x.Sources[0].RightsURL=""}},
  {"missing_candidate_trial",func(x *Catalog){x.Sources[0].CandidateIDs=[]string{}}},
  {"duplicate_catalog_source",func(x *Catalog){x.Sources[1].ID=x.Sources[0].ID}},
 }
 rejected:=[]string{}
 for _,t:=range tests{
  q:=clone(c);t.mutate(&q)
  if err:=check(q);err==nil{return nil,fmt.Errorf("adversarial source promotion not rejected: %s",t.name)}
  rejected=append(rejected,t.name)
 }
 return rejected,nil
}
func main(){
 input:=flag.String("catalog","mmd/research/study_motion_admission.v1.json","source catalog (metadata only)")
 output:=flag.String("out","", "optional machine-readable JSON receipt")
 flag.Parse()
 b,err:=os.ReadFile(*input);if err!=nil{panic(err)}
 var c Catalog;if err=json.Unmarshal(b,&c);err!=nil{panic(err)}
 if err=check(c);err!=nil{panic(err)}
 rejected,err:=runNegative(c);if err!=nil{panic(err)}
 report:=map[string]any{
  "schema":"scp.mmd.study_motion_source_admission_receipt.v1",
  "status":"PASS_METADATA_ONLY_SOURCE_GATES_AND_SIX_ADVERSARIAL_CONTROLS",
  "source_sha256":sha(b),"candidate_source_count":len(c.Sources),
  "first_trial_nominations":c.FirstTrials,"actual_external_capture_count":0,
  "actual_vmd_from_study_count":0,
  "red_controls_rejected":rejected,
  "real_data_admission":"BLOCKED_PENDING_FILE_LEVEL_RIGHTS_AND_AUTHORITY",
  "limits":[]string{"source descriptions not equivalent to recovered kinematics",
   "rights of derivative video/music/body model checked independently",
   "native BVH/ASF-to-VMD/SMPL-to-VMD converter is a later separate measured-data rep"},
 }
 p,_:=json.MarshalIndent(report,"","  ")
 fmt.Println(string(p))
 if *output!=""{
  if err=os.MkdirAll(filepath.Dir(*output),0755);err!=nil{panic(err)}
  if err=os.WriteFile(*output,append(p,'\n'),0644);err!=nil{panic(err)}
 }
}
