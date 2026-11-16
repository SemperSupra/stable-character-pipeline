// gasprobe compares fixed-geometry toy resonances for two synthetic ideal gases.
package main

import (
 "encoding/json"
 "fmt"
 "os"
 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium"
)
type Reading struct {
 Scenario string `json:"scenario"`
 SoundSpeed float64 `json:"sound_speed_mps"`
 Density float64 `json:"density_kg_m3"`
 FirstResonance float64 `json:"quarter_wave_f1_hz"`
 SecondResonance float64 `json:"quarter_wave_f2_hz"`
 FixedSourceF0 float64 `json:"imposed_source_f0_hz"`
}
func main(){
 base:=medium.Earthlike();altered:=medium.Earthlike();altered.Species[0].MoleFraction=0.74;altered.Species[2].MoleFraction=0.05
 out:=[]Reading{}
 for _,c:=range []struct{name string;state medium.State}{{"earthlike_reference",base},{"synthetic_argon_enriched_not_breathing_certified",altered}} {
  p,e:=c.state.Evaluate();if e!=nil {fmt.Fprintln(os.Stderr,e);os.Exit(2)}
  f1,_:=medium.QuarterWave(1,0.17,p.SoundSpeed);f2,_:=medium.QuarterWave(2,0.17,p.SoundSpeed)
  out=append(out,Reading{c.name,p.SoundSpeed,p.Density,f1,f2,150})
 }
 x:=json.NewEncoder(os.Stdout);x.SetIndent("","  ");if e:=x.Encode(out);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
}
