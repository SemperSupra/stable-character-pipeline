package main

// Executed synthetic byte-source admission validator performance, not a real
// camera or rights attestation. The adversarial labels are defined independently
// of the admission implementation. No network, model, private media or DB.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "runtime"
 "sort"
 "testing"
 "time"
)
type admissionOracle func(string,[]byte)(Receipt,error)
type admissionCase struct{
 ID string
 Expected string
 Mutate func(string,*Manifest)([]byte,error)
}
type admissionCaseResult struct{
 ID string `json:"id"`
 Expected string `json:"expected"`
 Actual string `json:"actual"`
 ManifestSHA string `json:"manifest_sha256"`
 InputByteSHA string `json:"input_byte_sha256"`
 ElapsedNS int64 `json:"elapsed_ns"`
}
type admissionQuality struct{
 Schema string `json:"schema"`
 Validator string `json:"validator"`
 ValidatorSHA string `json:"validator_sha256"`
 Corpus string `json:"corpus"`
 CorpusSHA string `json:"corpus_sha256"`
 SourceClass string `json:"source_class"`
 CaseCount int `json:"case_count"`
 Confusion map[string]map[string]int `json:"confusion"`
 RejectionDetection struct{Detected int `json:"detected"`;Total int `json:"total"`} `json:"rejection_detection"`
 FalseAcceptanceCount int `json:"false_acceptance_count"`
 FalseRejectionCount int `json:"false_rejection_count"`
 HardErrorCount int `json:"hard_error_count"`
 ContractMismatchCount int `json:"contract_mismatch_count"`
 Runtime struct{Go string `json:"go"`;LatencyP50NS int64 `json:"latency_p50_ns"`;LatencyP95NS int64 `json:"latency_p95_ns"`} `json:"runtime"`
 Cases []admissionCaseResult `json:"cases"`
 Verdict string `json:"verdict"`
 IndependentCameraCalibrated bool `json:"independent_camera_calibrated"`
 ExternalPhotoFit string `json:"external_photo_fit"`
 MergeReleaseCPEApproval bool `json:"merge_release_CPE_approval"`
}
func qualitySHA(b []byte)string{v:=sha256.Sum256(b);return hex.EncodeToString(v[:])}
func admissionCorpus()[]admissionCase{
 return []admissionCase{
  {ID:"valid-byte-verified-original",Expected:"ACCEPT"},
  {ID:"permuted-observation-order",Expected:"ACCEPT",Mutate:func(_ string,m *Manifest)([]byte,error){
   m.Observations[0],m.Observations[2]=m.Observations[2],m.Observations[0];return nil,nil
  }},
  {ID:"protected-source-denied",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.SubjectClass="private_human";return nil,nil}},
  {ID:"unverified-rights-denied",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.RightsClass="web_scraped";return nil,nil}},
  {ID:"capture-family-leak",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[2].CaptureFamily=m.Observations[0].CaptureFamily;return nil,nil}},
  {ID:"source-root-leak",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[2].SourceRootSHA256=m.Observations[0].SourceRootSHA256;return nil,nil}},
  {ID:"heldout-image-byte-leak",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[2].SHA256=m.Observations[0].SHA256;return nil,nil}},
  {ID:"duplicate-observation-id",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[1].ID=m.Observations[0].ID;return nil,nil}},
  {ID:"same-training-camera",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[1].CameraID=m.Observations[0].CameraID;return nil,nil}},
  {ID:"path-outside-root",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[0].Path="../outside.png";return nil,nil}},
  {ID:"tampered-png-bytes",Expected:"REJECT",Mutate:func(root string,m *Manifest)([]byte,error){
   return nil,os.WriteFile(filepath.Join(root,m.Observations[0].Path),[]byte("different bytes"),0600)
  }},
  {ID:"bad-png-even-with-good-hash",Expected:"REJECT",Mutate:func(root string,m *Manifest)([]byte,error){
   b:=[]byte("not decoded PNG");if err:=os.WriteFile(filepath.Join(root,m.Observations[0].Path),b,0600);err!=nil{return nil,err}
   m.Observations[0].SHA256=qualitySHA(b);return nil,nil
  }},
  {ID:"duplicate-json-schema-key",Expected:"REJECT",Mutate:func(_ string,_ *Manifest)([]byte,error){
   return []byte(`{"schema":"a","schema":"b"}`),nil
  }},
  {ID:"trailing-json-payload",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){
   return append(encoded(*m),[]byte(" {}")...),nil
  }},
  {ID:"no-heldout-observations",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[2].Split="training";return nil,nil}},
  {ID:"unsupported-capture-type",Expected:"REJECT",Mutate:func(_ string,m *Manifest)([]byte,error){m.Observations[2].Path="model.glb";return nil,nil}},
 }
}
func admissionClassify(root string,raw []byte,oracle admissionOracle)string{
 r,err:=oracle(root,raw)
 if err!=nil{return "REJECT"}
 if r.Schema!="scp.synthetic_observation_receipt.v1" ||
    r.ScientificResult!="UNKNOWN" || r.ExternalPhotoAdmission!="NOT_RUN" ||
    r.CameraIndependence!="UNKNOWN_NO_EXTERNAL_CALIBRATION" || r.Mutation {
    return "ERROR"
 }
 return "ACCEPT"
}
func scoreAdmissionQuality(t *testing.T,oracle admissionOracle) admissionQuality{
 t.Helper()
 entries:=admissionCorpus()
 labels:=[]string{"ACCEPT","ABSTAIN","REJECT","ERROR"}
 q:=admissionQuality{Schema:"scp.validator.performance.v1",
   Validator:"scp.original_synthetic_byte_observation_admission",
   Corpus:"scp.source_byte_capture_holdout_quality.v1",
   SourceClass:"ORIGINAL_SYNTHETIC_PNG_AND_MANIFEST_BYTES_ONLY",
   CaseCount:len(entries),Confusion:map[string]map[string]int{},
   ExternalPhotoFit:"NOT_RUN",Cases:[]admissionCaseResult{}}
 b,err:=os.ReadFile("main.go");if err!=nil{t.Fatal(err)}
 q.ValidatorSHA=qualitySHA(b)
 q.Runtime.Go=runtime.Version()
 for _,label:=range labels{
  q.Confusion[label]=map[string]int{}
  for _,value:=range labels{q.Confusion[label][value]=0}
 }
 times:=make([]int64,0,len(entries))
 corpusLabels:=[]string{}
 for _,test:=range entries{
  root,m:=setup(t)
  raw:=encoded(m)
  if test.Mutate!=nil{
   replacement,err:=test.Mutate(root,&m);if err!=nil{t.Fatal(err)}
   if replacement!=nil{raw=replacement}else{raw=encoded(m)}
  }
  // Test-source fingerprint includes every root PNG byte, even when a bogus
  // manifest points outside the root or contains a false digest.
  inputs:=[]byte{}
  paths,err:=filepath.Glob(filepath.Join(root,"*.png"));if err!=nil{t.Fatal(err)}
  sort.Strings(paths)
  for _,p:=range paths{
   data,err:=os.ReadFile(p);if err!=nil{t.Fatal(err)}
   inputs=append(inputs,[]byte(filepath.Base(p)+":")...)
   inputs=append(inputs,[]byte(qualitySHA(data))...)
  }
  inSHA:=qualitySHA(inputs)
  manifestSHA:=qualitySHA(raw)
  corpusLabels=append(corpusLabels,test.ID+"|"+test.Expected+"|"+manifestSHA+"|"+inSHA)
  start:=time.Now()
  got:=admissionClassify(root,raw,oracle)
  elapsed:=time.Since(start).Nanoseconds()
  times=append(times,elapsed)
  q.Confusion[test.Expected][got]++
  q.Cases=append(q.Cases,admissionCaseResult{
   ID:test.ID,Expected:test.Expected,Actual:got,
   ManifestSHA:manifestSHA,InputByteSHA:inSHA,ElapsedNS:elapsed,
  })
  if test.Expected!=got{q.ContractMismatchCount++}
  if test.Expected!="ACCEPT"&&got=="ACCEPT"{q.FalseAcceptanceCount++}
  if test.Expected=="ACCEPT"&&got!="ACCEPT"{q.FalseRejectionCount++}
  if got=="ERROR"{q.HardErrorCount++}
  if test.Expected=="REJECT"{
   q.RejectionDetection.Total++
   if got=="REJECT"{q.RejectionDetection.Detected++}
  }
 }
 basis,_:=json.Marshal(corpusLabels)
 q.CorpusSHA=qualitySHA(basis)
 sort.Slice(times,func(i,j int)bool{return times[i]<times[j]})
 q.Runtime.LatencyP50NS=times[(len(times)+1)/2-1]
 q.Runtime.LatencyP95NS=times[(95*len(times)+99)/100-1]
 q.Verdict="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY"
 if q.ContractMismatchCount!=0{q.Verdict="FAIL_VALIDATOR_CONTROLS"}
 return q
}
func TestAdmissionValidatorQualityReceipt(t *testing.T){
 q:=scoreAdmissionQuality(t,admit)
 if q.CaseCount!=16||q.RejectionDetection.Total!=14||q.RejectionDetection.Detected!=14||
 q.Confusion["ACCEPT"]["ACCEPT"]!=2||q.FalseAcceptanceCount!=0||
 q.FalseRejectionCount!=0||q.HardErrorCount!=0||q.ContractMismatchCount!=0||
 q.Verdict!="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY"{t.Fatalf("admission quality red %+v",q)}
 if path:=os.Getenv("SCP_ADMISSION_VALIDATOR_PERF_OUT");path!=""{
  blob,err:=json.MarshalIndent(q,"","  ");if err!=nil{t.Fatal(err)}
  if err=os.WriteFile(path,append(blob,'\n'),0600);err!=nil{t.Fatal(err)}
 }
 t.Logf("ADMISSION_VALIDATOR_QUALITY source=%s corpus=%s p95ns=%d",q.ValidatorSHA,q.CorpusSHA,q.Runtime.LatencyP95NS)
}
func TestAdmissionMetaOracleDetectsAlwaysAcceptAndReject(t *testing.T){
 acceptAll:=func(_ string,_ []byte)(Receipt,error){
  return Receipt{Schema:"scp.synthetic_observation_receipt.v1",
   ScientificResult:"UNKNOWN",ExternalPhotoAdmission:"NOT_RUN",
   CameraIndependence:"UNKNOWN_NO_EXTERNAL_CALIBRATION",Mutation:false},nil
 }
 a:=scoreAdmissionQuality(t,acceptAll)
 if a.FalseAcceptanceCount!=14||a.ContractMismatchCount!=14||a.Verdict!="FAIL_VALIDATOR_CONTROLS"{
  t.Fatalf("broken always-accept admitted: %+v",a)
 }
 rejectAll:=func(_ string,_ []byte)(Receipt,error){return Receipt{},errors.New("broken")}
 b:=scoreAdmissionQuality(t,rejectAll)
 if b.FalseRejectionCount!=2||b.ContractMismatchCount!=2||b.Verdict!="FAIL_VALIDATOR_CONTROLS"{
  t.Fatalf("broken always-reject admitted: %+v",b)
 }
}
