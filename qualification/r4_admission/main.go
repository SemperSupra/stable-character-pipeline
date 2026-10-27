package main

// R4 source-only upstream admission: immutable JSON evidence, no network, no
// model inference or credential access. Source/weights/assets rights are distinct.
import (
  "crypto/sha256"
  "encoding/json"
  "errors"
  "flag"
  "fmt"
  "io"
  "net/url"
  "os"
  "sort"
  "strings"
)

type Candidate struct {
  ID string `json:"id"`
  Capability string `json:"capability"`
  Upstream string `json:"upstream"`
  CodeLicense string `json:"code_license"`
  CodeLicenseEvidence string `json:"code_license_evidence"`
  WeightsTerms string `json:"weights_terms"`
  WeightsEvidence string `json:"weights_evidence"`
  WeightsAccess string `json:"weights_access"`
  GPUMinVRAMGB *float64 `json:"gpu_min_vram_gb_upstream"`
  GPURequired *bool `json:"gpu_required_upstream"`
  ExternalAssets []string `json:"external_assets"`
  SourceMediaRights string `json:"source_media_rights"`
  TargetRigRights string `json:"target_rig_rights"`
  ActualInferenceStatus string `json:"actual_inference_status"`
}
type Manifest struct {
  Schema string `json:"schema"`
  ReviewedUTCDate string `json:"reviewed_utc_date"`
  ResearchLane string `json:"research_lane"`
  FetchWeights bool `json:"fetch_weights"`
  FetchSourceMedia bool `json:"fetch_source_media"`
  ExecuteModelInference bool `json:"execute_model_inference"`
  AllowPrivateInputs bool `json:"allow_private_inputs"`
  AllowPaidCompute bool `json:"allow_paid_compute"`
  Candidates []Candidate `json:"candidates"`
}
type Result struct {
  ID string `json:"id"`
  Capability string `json:"capability"`
  CodeLicense string `json:"code_license"`
  WeightsAccess string `json:"weights_access"`
  GpuMinVRAMGB *float64 `json:"gpu_min_vram_gb_upstream"`
  ActualInference string `json:"actual_inference"`
  Admission string `json:"admission"`
  SourceRights string `json:"source_media_rights"`
  RigRights string `json:"target_rig_rights"`
  WeightTerms string `json:"weights_terms"`
}
type Receipt struct{
  Schema string `json:"schema"`
  InputSHA256 string `json:"input_sha256"`
  Status string `json:"status"`
  SourceLicenseSurveyOnly bool `json:"source_license_survey_only"`
  CandidateCount int `json:"candidate_count"`
  WeightDownloads int `json:"weight_downloads"`
  ModelInferences int `json:"model_inferences"`
  GPUExecutions int `json:"gpu_executions"`
  Results []Result `json:"results"`
  Next string `json:"next_admission_baton"`
}
func allowedURL(s string) bool {
  u,e:=url.Parse(s)
  return e==nil && u.Scheme=="https" && u.User==nil &&
    (u.Hostname()=="github.com" || u.Hostname()=="huggingface.co") &&
    u.Port()=="" && u.Fragment=="" && u.Path!="" && u.RawQuery==""
}
func validate(m Manifest)error{
  if m.Schema!="stable-character/r4-upstream-admission/1" ||
    m.ResearchLane!="PUBLIC_CPU_SOURCE_METADATA_ONLY" || m.ReviewedUTCDate=="" {
    return errors.New("unrecognized source-only candidate schema/authority")
  }
  if m.FetchWeights||m.FetchSourceMedia||m.ExecuteModelInference||m.AllowPrivateInputs||m.AllowPaidCompute {
    return errors.New("forbidden download, inference, private or paid execution was requested")
  }
  if len(m.Candidates)!=5{return fmt.Errorf("fixed upstream source set must contain 5 candidates, got %d",len(m.Candidates))}
  seen:=map[string]bool{}
  for _,c:=range m.Candidates{
    if c.ID=="" || seen[c.ID]{return fmt.Errorf("duplicate/empty candidate ID: %s",c.ID)}
    seen[c.ID]=true
    switch c.Capability{
      case "MESH_TO_SKELETON_AND_WEIGHTS", "VIDEO_AND_REFERENCE_RIG_TO_MOTION", "PHOTO_TO_MODEL_ESTIMATED_BODY_MESH","PHOTO_OR_VIDEO_TO_EXISTING_RIG_MOTION":
      default:return fmt.Errorf("unrecognized model capability %s",c.ID)
    }
    if c.CodeLicense!="MIT"&&c.CodeLicense!="Apache-2.0"&&c.CodeLicense!="SAM-License"{
      return fmt.Errorf("unreviewed code license for %s",c.ID)
    }
    if c.ActualInferenceStatus!="NOT_TESTED"{
      return fmt.Errorf("no actual model inference observed for %s",c.ID)
    }
    if !allowedURL(c.Upstream)||!allowedURL(c.CodeLicenseEvidence)||!allowedURL(c.WeightsEvidence) {
      return fmt.Errorf("unallowlisted upstream/evidence host or URL for %s",c.ID)
    }
    if !strings.HasPrefix(c.Upstream,"https://github.com/") {
      return fmt.Errorf("upstream source must be official GitHub project for %s",c.ID)
    }
    if c.WeightsTerms==""||c.WeightsAccess==""||len(c.ExternalAssets)==0 ||
      c.SourceMediaRights!="PER_FILE_REVIEW"||c.TargetRigRights==""{
      return fmt.Errorf("three independently recorded rights ledgers required for %s",c.ID)
    }
    if c.GPUMinVRAMGB!=nil && (*c.GPUMinVRAMGB < 0 || *c.GPUMinVRAMGB > 200){
      return fmt.Errorf("invalid upstream GPU memory field %s",c.ID)
    }
    for _,asset:=range c.ExternalAssets{
      if strings.TrimSpace(asset)=="" || strings.ContainsAny(asset,"\n\r") {
        return fmt.Errorf("invalid asset rights entry for %s",c.ID)
      }
    }
  }
  for _,expected:=range []string{"unirig","skintokens","mocapanything-v2","sam-3d-body","motion2mixamorig"}{
    if !seen[expected]{return fmt.Errorf("missing reviewed upstream %s",expected)}
  }
  return nil
}
func decode(b []byte)(Manifest,error){
  var m Manifest
  d:=json.NewDecoder(strings.NewReader(string(b)))
  d.DisallowUnknownFields()
  if err:=d.Decode(&m);err!=nil{return m,err}
  // Decoder cannot accept appended extra JSON objects as undocumented policy.
  var tail any
  if err:=d.Decode(&tail);err==nil{return m,errors.New("trailing JSON values not allowed")} else if !errors.Is(err,io.EOF){return m,err}
  return m,nil
}
func run(manifestBytes []byte)(Receipt,error){
  m,err:=decode(manifestBytes);if err!=nil{return Receipt{},err}
  if err:=validate(m);err!=nil{return Receipt{},err}
  sum:=sha256.Sum256(manifestBytes)
  r:=Receipt{
    Schema:"stable-character/r4-admission-receipt/1",
    InputSHA256:fmt.Sprintf("%x",sum),
    Status:"SOURCE_RIGHTS_REVIEW_ONLY_NOT_MODEL_INFERENCE",
    SourceLicenseSurveyOnly:true,
    CandidateCount:len(m.Candidates),
    WeightDownloads:0, ModelInferences:0, GPUExecutions:0,
    Next:"PIN_UPSTREAM_COMMIT_AND_FIXTURE_RIGHTS_THEN_ADMIT_SEPARATE_CUDA_MODEL_INFERENCE",
  }
  for _,c:=range m.Candidates{
    r.Results=append(r.Results,Result{
      ID:c.ID,Capability:c.Capability,CodeLicense:c.CodeLicense,
      WeightsAccess:c.WeightsAccess, GpuMinVRAMGB:c.GPUMinVRAMGB,
      ActualInference:c.ActualInferenceStatus, Admission:"METADATA_ONLY_NO_WEIGHTS_NO_PRIVATE_RUNNERS",
      SourceRights:c.SourceMediaRights,RigRights:c.TargetRigRights,WeightTerms:c.WeightsTerms,
    })
  }
  sort.Slice(r.Results,func(i,j int)bool{return r.Results[i].ID<r.Results[j].ID})
  return r,nil
}
func main(){
  path:=flag.String("manifest","qualification/r4_admission/candidates.json","pinned, reviewed source registry JSON")
  out:=flag.String("out","r4-admission-receipt.json","no-network evaluated admission receipt JSON")
  flag.Parse()
  in,err:=os.ReadFile(*path)
  if err!=nil{fmt.Fprintln(os.Stderr,"R4_FAIL",err);os.Exit(4)}
  receipt,err:=run(in)
  if err!=nil{fmt.Fprintln(os.Stderr,"R4_FAIL",err);os.Exit(4)}
  body,err:=json.MarshalIndent(receipt,"","  ")
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
  if err:=os.WriteFile(*out,append(body,10),0644);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
  fmt.Println(string(body))
}
