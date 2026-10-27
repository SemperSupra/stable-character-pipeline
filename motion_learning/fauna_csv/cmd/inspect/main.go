package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"

 horse "github.com/SemperSupra/stable-character-pipeline/motion_learning/fauna_csv"
)

func main(){
 source:=flag.String("source","","only original synthetic fixture CSV")
 id:=flag.String("source-id","","synthetic source stable ID")
 family:=flag.String("capture-family","","synthetic recording family")
 out:=flag.String("out","","exclusive-create report path")
 flag.Parse()
 if *source==""||*id==""||*family==""||*out=="" {fmt.Fprintln(os.Stderr,"usage: inspect -source X -source-id Y -capture-family Z -out report.json");os.Exit(4)}
 data,err:=os.ReadFile(*source);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 observation,err:=horse.Parse(data,*id,*family)
 if err!=nil{fmt.Fprintln(os.Stderr,"SOURCE_HOLD:",err);os.Exit(3)}
 sensitivity,err:=horse.Falsify(observation,data,[]float64{.08,.12,.20})
 if err!=nil{fmt.Fprintln(os.Stderr,"EVIDENCE_HOLD:",err);os.Exit(3)}
 f,err:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{fmt.Fprintln(os.Stderr,"output must be new:",err);os.Exit(4)}
 defer f.Close()
 report:=struct{
  Observation horse.Observation `json:"observation"`
  Sensitivity horse.Sensitivity `json:"sensitivity"`
 }{observation,sensitivity}
 enc:=json.NewEncoder(f);enc.SetIndent("","  ")
 if err:=enc.Encode(report);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
}
