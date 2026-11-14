package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
)

func main() {
 files:=[]string{"contactgate.go","contactgate_test.go","go.mod","cmd/receipt/main.go"}
 hashes:=map[string]string{}
 for _,path:=range files {
  b,e:=os.ReadFile(path);if e!=nil{panic(e)}
  x:=sha256.Sum256(b)
  hashes[path]=hex.EncodeToString(x[:])
 }
 receipt:=struct{
  Schema string `json:"schema"`
  Status string `json:"status"`
  SourceClassification string `json:"source_classification"`
  SourceFiles map[string]string `json:"source_file_sha256"`
  GitHubRunID string `json:"github_run_id"`
  GitHubCheckoutRef string `json:"github_checkout_ref_may_be_pr_merge_ref"`
  ActualBigMacGait string `json:"actual_bigmac_r009_gait"`
  ActualProtectedHuman string `json:"protected_source_human"`
  ActualAnatomy string `json:"actual_anatomy_or_contact_quality"`
  HumanOwnerCanon string `json:"character_pack_canon"`
 }{
  Schema:"r014.contact_quarter_frame_source_safe_receipt.v1",
  Status:"SYNTHETIC_ONLY__DOES_NOT_PROVE_STANCE_FOOT_CONTACT",
  SourceClassification:"ORIGINAL_GO_CODE_AND_FICTIONAL_MARKER_TRAJECTORIES_ONLY",
  SourceFiles:hashes,
  GitHubRunID:os.Getenv("GITHUB_RUN_ID"),GitHubCheckoutRef:os.Getenv("GITHUB_SHA"),
  ActualBigMacGait:"NOT_RUN",ActualProtectedHuman:"NONE",
  ActualAnatomy:"NOT_EVALUATED",HumanOwnerCanon:"HOLD_OWNER_ONLY",
 }
 b,e:=json.MarshalIndent(receipt,"","  ");if e!=nil{panic(e)}
 fmt.Println(string(b))
}
