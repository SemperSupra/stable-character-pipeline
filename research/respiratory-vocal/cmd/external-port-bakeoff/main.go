// external-port-bakeoff produces source-neutral numeric receipts only.
// It does not publish private performance media or claim instrument realism.
package main

import(
 "encoding/json"
 "fmt"
 "os"
 "sort"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/external"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Row struct{
 Name string `json:"name"`
 external.Receipt
}
type Report struct{
 Schema string `json:"schema"`
 Validity string `json:"validity"`
 Cases []Row `json:"cases"`
}
func main(){
 names:=[]string{"balloon_airflow","external_whistle","flute_jet","reed_instrument","straw_suction"}
 sort.Strings(names)
 ports:=map[string]behavior.Port{
  "balloon_airflow":behavior.Balloon,"external_whistle":behavior.ExternalWhistle,
  "flute_jet":behavior.Flute,"reed_instrument":behavior.Reed,"straw_suction":behavior.Straw,
 }
 report:=Report{Schema:"respiratory.external_port_bakeoff.v0",
  Validity:"5_pinned_original_synthetic_ports_not_real_instrument_sound",Cases:[]Row{}}
 for _,name:=range names{
  p,ok:=preview.Fixtures()[name];if !ok{fail(fmt.Errorf("missing source case %s",name))}
  c:=external.Config{Port:ports[name],ResistancePaSPerM3:8e6}
  if c.Port==behavior.Balloon{
   c.BalloonComplianceM3PerPa=1e-7;c.InitialBalloonVolumeM3=.001;c.BalloonCapacityM3=.01
  }
  receipt,err:=external.Evaluate(p,c);if err!=nil{fail(err)}
  report.Cases=append(report.Cases,Row{Name:name,Receipt:receipt})
 }
 if len(report.Cases)!=5{fail(fmt.Errorf("incomplete source fixtures"))}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if err:=enc.Encode(report);err!=nil{fail(err)}
}
func fail(err error){fmt.Fprintln(os.Stderr,"INVALID:",err);os.Exit(2)}
