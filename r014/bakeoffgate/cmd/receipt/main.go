package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
)

func main() {
 paths:=[]string{"gate.go","gate_test.go","go.mod","cmd/receipt/main.go"}
 checksums:=map[string]string{}
 for _,p:=range paths{
  b,e:=os.ReadFile(p);if e!=nil{panic(e)}
  sum:=sha256.Sum256(b)
  checksums[p]=hex.EncodeToString(sum[:])
 }
 out:=struct{
  Schema string `json:"schema"`
  Status string `json:"status"`
  Scope string `json:"scope"`
  CheckOutSHA string `json:"github_checkout_sha_may_be_pr_merge_ref"`
  RunID string `json:"github_run_id"`
  SourceSHA256 map[string]string `json:"source_sha256"`
  ActualMHR string `json:"actual_mhr_corrective_runtime"`
  ProtectedInputs string `json:"protected_source_inputs"`
  ModelSelection string `json:"canonical_character_pack"`
 }{
  Schema:"r014.corrective_bakeoff_admission_synthetic_receipt.v1",
  Status:"PASS_ONLY_IF_PRECEDING_GO_TEST_COMMAND_SUCCEEDED",
  Scope:"original source-only validator and synthetic string-hash fixtures; no model/CMU media",
  CheckOutSHA:os.Getenv("GITHUB_SHA"),
  RunID:os.Getenv("GITHUB_RUN_ID"),
  SourceSHA256:checksums,
  ActualMHR:"NOT_RUN__HOLD",
  ProtectedInputs:"NONE",
  ModelSelection:"HOLD_OWNER_ONLY",
 }
 b,e:=json.MarshalIndent(out,"","  ");if e!=nil{panic(e)}
 fmt.Println(string(b))
}
