package main
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
)
func main(){
 paths:=[]string{"jointmap.go","jointmap_test.go","go.mod","cmd/receipt/main.go"}
 hashes:=map[string]string{}
 for _,path:=range paths{
  b,e:=os.ReadFile(path);if e!=nil{panic(e)}
  sum:=sha256.Sum256(b);hashes[path]=hex.EncodeToString(sum[:])
 }
 data:=struct{
  Schema string `json:"schema"`
  Status string `json:"status"`
  Source string `json:"source"`
  SourceFiles map[string]string `json:"source_file_sha256"`
  GhaRun string `json:"github_run_id"`
  GhaCheckout string `json:"github_checkout_may_be_pr_merge_ref"`
  UpstreamMHRCodeBlob string `json:"reviewed_mhr_mhr_py_blob"`
  UpstreamMHRIOBlob string `json:"reviewed_mhr_io_py_blob"`
  ActualNativeAsset string `json:"actual_native_mhr_asset"`
  ActualMapping string `json:"actual_127_to_126_mapping"`
  SourceRights string `json:"source_rights"`
  Acceptance string `json:"characterpack_acceptance"`
 }{
  Schema:"r014.mhr_jointmap_structural_negative_control.v1",
  Status:"SYNTHETIC_GO_TEST_PASS_ONLY_IF_PRECEDING_TEST_STEP_SUCCESS",
  Source:"only generated fictional 127/126 graph and original Go source",
  SourceFiles:hashes,GhaRun:os.Getenv("GITHUB_RUN_ID"),GhaCheckout:os.Getenv("GITHUB_SHA"),
  UpstreamMHRCodeBlob:"28f2e57b00f98ca63a32315d45d10c2fc49aee8f",
  UpstreamMHRIOBlob:"8325a469edc6c00dd317d8320fc0c29e52fb57dc",
  ActualNativeAsset:"NOT_LOADED",
  ActualMapping:"UNKNOWN_NOT_OBSERVED",
  SourceRights:"UNREVIEWED_MODEL_AND_MEDIA_OPERATION",
  Acceptance:"HOLD_OWNER_ONLY",
 }
 b,e:=json.MarshalIndent(data,"","  ");if e!=nil{panic(e)}
 fmt.Println(string(b))
}
