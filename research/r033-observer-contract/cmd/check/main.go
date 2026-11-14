package main

import (
 "encoding/json"
 "fmt"
 "os"
 observer "github.com/SemperSupra/stable-character-pipeline/research/r033-observer-contract"
)
func main(){
 receipt,err:=observer.DecodeAndValidate(os.Stdin)
 if err!=nil{fmt.Fprintln(os.Stderr,"REJECT:",err);os.Exit(2)}
 // Validation is structural only; a second independent source/media/physics
 // checker must establish that the referenced evidence actually exists.
 result:=struct{Status string `json:"status"`;Claim string `json:"claim"`;Count int `json:"observation_count"`}{
  Status:receipt.Status,Claim:"SOURCE_SAFE_STRUCTURAL_VALIDATION_ONLY_NOT_VISUAL_QA_PASS",Count:len(receipt.Observations),
 }
 if err:=json.NewEncoder(os.Stdout).Encode(result);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
