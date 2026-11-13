package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"

 qa "github.com/SemperSupra/stable-character-pipeline/r014/shellqa"
)
func hash(paths ...string) (map[string]string,error) {
 out:=map[string]string{}
 for _,path:=range paths {
  b,e:=os.ReadFile(path);if e!=nil{return nil,e}
  sum:=sha256.Sum256(b);out[filepath.Base(path)]=hex.EncodeToString(sum[:])
 }
 return out,nil
}
func main() {
 base:=qa.Patch()
 cases:=[]struct{Name string;Mesh qa.Mesh}{
  {"rigid_y120",qa.RotateY(base,120)},
  {"natural_hinge45",qa.Hinge(base,45)},
  {"opposing_hinge160",qa.Hinge(base,160)},
 }
 type Item struct{Name string `json:"name"`; Receipt qa.Receipt `json:"receipt"`}
 all:=[]Item{}
 for _,x:=range cases {
  r,e:=qa.Analyze(base,x.Mesh);if e!=nil {panic(e)}
  all=append(all,Item{x.Name,r})
 }
 digest,e:=hash("shellqa.go","shellqa_test.go","cmd/receipt/main.go")
 if e!=nil {panic(e)}
 doc:=struct {
  Schema string `json:"schema"`
  Status string `json:"status"`
  GitHubSHA string `json:"github_sha_checkout_may_be_pr_merge_ref"`
  GitHubRunID string `json:"github_run_id"`
  SourceSHA256 map[string]string `json:"source_sha256"`
  Inputs string `json:"inputs"`
  Cases []Item `json:"cases"`
  Holds []string `json:"holds"`
 }{
  Schema:"r014.shellqa.synthetic_oracle_receipt.v1",
  Status:"PASS_SYNTHETIC_DIAGNOSTICS_ONLY",
  GitHubSHA:os.Getenv("GITHUB_SHA"),GitHubRunID:os.Getenv("GITHUB_RUN_ID"),
  SourceSHA256:digest,
  Inputs:"original procedural mesh only; no external model/media/mocap",
  Cases:all,
  Holds:[]string{"No actual CMU07 source tested","No MHR 18439-vertex native mesh tested","No self-intersection BVH","No human pose realism, contact, unit calibration or release acceptance"},
 }
 b,e:=json.MarshalIndent(doc,"","  ");if e!=nil {panic(e)}
 fmt.Println(string(b))
}
