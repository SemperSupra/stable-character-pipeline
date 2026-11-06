package main

// CompareSeasonalStates is a source-only continuity gate for time-indexed
// morphology/coat transitions. A source-to-source contract pass is not
// permission to promote biological accuracy, source rights or a release.
import (
    "math"
    "sort"
)

type FiberEvent struct {
    ID string `json:"id"`
    Action string `json:"action"` // grow or shed
}
type TransitionReceipt struct {
    Schema string `json:"schema"`
    Verdict string `json:"verdict"`
    Persistent int `json:"persistent"`
    Grown int `json:"grown"`
    Shed int `json:"shed"`
    MaxPersistentLengthChangeFraction float64 `json:"max_persistent_length_change_fraction"`
    Errors []string `json:"errors"`
    ScientificHold bool `json:"scientific_hold"`
    ReleaseAdmission bool `json:"release_admission"`
}
func compareSeasonalStates(before,after Groom,events []FiberEvent)TransitionReceipt {
    out:=TransitionReceipt{Schema:"equine.groom.transition.v1",
        Verdict:"REJECT_UNQUALIFIED_SOURCE_TRANSITION",Errors:[]string{},
        ScientificHold:true,ReleaseAdmission:false}
    bad:=func(s string){out.Errors=append(out.Errors,s)}
    if validate(before,[]byte("before")).Verdict!="PASS_SOURCE_SCHEMA_ONLY"||
       validate(after,[]byte("after")).Verdict!="PASS_SOURCE_SCHEMA_ONLY"{
        bad("invalid_source_groom");return out
    }
    if before.GroomID!=after.GroomID || before.SourceKind!=after.SourceKind ||
       before.SourceMeshSHA256!=after.SourceMeshSHA256 ||
       before.Seed!=after.Seed || before.Units!=after.Units{
        bad("identity_or_mesh_changed_requires_explicit_retarget")
    }
    if len(events)>40000 {bad("unbounded_transition_event_list");return out}
    changes:=map[string]string{}
    for _,e:=range events {
        if e.ID=="" || (e.Action!="grow"&&e.Action!="shed") || changes[e.ID]!="" {
            bad("duplicate_or_unknown_lifecycle_event")
        }
        changes[e.ID]=e.Action
    }
    b:=map[string]Fiber{};a:=map[string]Fiber{}
    for _,f:=range before.Fibers {b[f.ID]=f}
    for _,f:=range after.Fibers {a[f.ID]=f}
    for id,old:=range b{
        next,ok:=a[id]
        if !ok {
            out.Shed++
            if changes[id]!="shed" {bad("undeclared_shedding:"+id)}
            continue
        }
        out.Persistent++
        if changes[id]!="" {bad("redundant_event_on_retained_fiber:"+id)}
        if old.Region!=next.Region || old.SourceTriangle!=next.SourceTriangle ||
           old.Barycentric!=next.Barycentric || len(old.SkinWeights)!=len(next.SkinWeights) {
            bad("persistent_follicle_identity_mismatch:"+id)
        }
        for bone,w:=range old.SkinWeights {
            other,ok:=next.SkinWeights[bone]
            if !ok || math.Abs(other-w)>1e-6 {bad("persistent_skin_binding_changed:"+id)}
        }
        change:=math.Abs(next.RestLength-old.RestLength)/old.RestLength
        if !math.IsNaN(change) && !math.IsInf(change,0) &&
            change>out.MaxPersistentLengthChangeFraction {
                out.MaxPersistentLengthChangeFraction=change
        }
    }
    for id:=range a {
        if _,ok:=b[id];ok{continue}
        out.Grown++
        if changes[id]!="grow"{bad("undeclared_follicle_growth:"+id)}
    }
    for id,kind:=range changes{
        if kind=="grow"{
            if _,old:=b[id];old{bad("grow_event_on_existing_fiber:"+id)}
            if _,newFiber:=a[id];!newFiber{bad("unrealized_growth_event:"+id)}
        }else if kind=="shed"{
            if _,old:=b[id];!old{bad("shed_event_without_prior_fiber:"+id)}
            if _,newFiber:=a[id];newFiber{bad("shed_event_but_fiber_persists:"+id)}
        }
    }
    sort.Strings(out.Errors)
    if len(out.Errors)==0{out.Verdict="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"}
    return out
}
