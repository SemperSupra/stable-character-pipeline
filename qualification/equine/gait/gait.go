// Package gait generates deterministic PLANNED hoof-contact events.
// A planned footfall is NOT an evaluated skinned-hoof physical ground contact.
package gait

import (
    "errors"
    "fmt"
    "sort"
)

const Schema = "equine.contact.v1"
const Basis = "SYNTHETIC_PLANNED"

type Beat struct {
    Foot string
    Phase96 int
}
type Event struct {
    ActorID string `json:"actor_id"`
    Gait string `json:"gait"`
    Foot string `json:"foot"`
    Kind string `json:"kind"`
    ContactState string `json:"contact_state"`
    Surface string `json:"surface"`
    Frame int `json:"frame"`
    Sample int64 `json:"sample"`
    Source string `json:"source"`
}
type Receipt struct {
    Schema string `json:"schema"`
    Basis string `json:"basis"`
    ActorID string `json:"actor_id"`
    Gait string `json:"gait"`
    FPS int `json:"fps"`
    SampleRate int `json:"sample_rate"`
    FramesPerCycle int `json:"frames_per_cycle"`
    Cycles int `json:"cycles"`
    Evaluation string `json:"evaluation"`
    Events []Event `json:"events"`
}

func Beats(gait string) ([]Beat, error) {
    switch gait {
    case "idle": return []Beat{},nil
    case "walk": return []Beat{{"HL",0},{"FL",24},{"HR",48},{"FR",72}},nil
    case "trot": return []Beat{{"HL",0},{"FR",0},{"FL",48},{"HR",48}},nil
    case "canter-left": return []Beat{{"HR",0},{"HL",32},{"FR",32},{"FL",64}},nil
    case "canter-right": return []Beat{{"HL",0},{"HR",32},{"FL",32},{"FR",64}},nil
    case "gallop-left": return []Beat{{"HR",0},{"HL",24},{"FR",48},{"FL",72}},nil
    case "gallop-right": return []Beat{{"HL",0},{"HR",24},{"FL",48},{"FR",72}},nil
    }
    return nil, fmt.Errorf("unsupported gait %q",gait)
}

func Generate(actor,gait,surface string,cycles,framesPerCycle,fps,sampleRate int) (Receipt,error) {
    out:=Receipt{Schema:Schema,Basis:Basis,ActorID:actor,Gait:gait,FPS:fps,SampleRate:sampleRate,
        FramesPerCycle:framesPerCycle,Cycles:cycles,Evaluation:"PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT",
        Events:make([]Event,0)}
    if actor=="" || surface!="sand"&&surface!="stone"&&surface!="soil"&&surface!="grass" {
        return out,errors.New("empty actor or unsupported surface")
    }
    if cycles<1||cycles>16||framesPerCycle<12||framesPerCycle>240||fps<12||fps>120||sampleRate!=48000 {
        return out,errors.New("unbounded clock or sample rate")
    }
    if sampleRate%fps!=0 { return out,errors.New("non-integral frame/sample mapping") }
    beats,err:=Beats(gait)
    if err!=nil {return out,err}
    for i:=0;i<cycles;i++{
        for _,b:=range beats{
            if (framesPerCycle*b.Phase96)%96!=0{
                return out,fmt.Errorf("non-integral phase %d/96 for %d-frame cycle",b.Phase96,framesPerCycle)
            }
            frame:=i*framesPerCycle+(framesPerCycle*b.Phase96)/96
            out.Events=append(out.Events, Event{ActorID:actor,Gait:gait,Foot:b.Foot,Kind:"hoof_impact",
                ContactState:"planned_contact",Surface:surface,Frame:frame,
                Sample:int64(frame)*int64(sampleRate/fps),Source:Basis})
        }
    }
    order:=map[string]int{"HL":0,"HR":1,"FL":2,"FR":3}
    sort.Slice(out.Events,func(i,j int)bool{
        if out.Events[i].Frame!=out.Events[j].Frame{return out.Events[i].Frame<out.Events[j].Frame}
        return order[out.Events[i].Foot]<order[out.Events[j].Foot]
    })
    return out,nil
}
