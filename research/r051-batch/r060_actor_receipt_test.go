package main

import (
    "strings"
    "testing"
)

func exitcode(n int)*int{return &n}

func syntheticRep() ActorRep {
    return ActorRep{
        Schema:RepSchema,Actor:"synthetic-actor",Model:"synthetic-model",
        OS:"linux-original-fixture",Repo:"synthetic/repo",
        Branch:"research/r051-a",RepID:"rep-fixture-001",
        Packets:[]PacketResult{
            {ID:"SYN-A",State:"PASS_NARROW",Branch:"research/r051-a",
             SourceSHA:strings.Repeat("a",40),TestCommand:"go test -count=1 ./...",
             TestEvidenceSHA256:strings.Repeat("1",64),ObservedExitCode:exitcode(0),NegativeRejected:true},
            {ID:"SYN-B",State:"PASS_NARROW",Branch:"research/r051-b",
             SourceSHA:strings.Repeat("b",40),TestCommand:"go test -race ./...",
             TestEvidenceSHA256:strings.Repeat("2",64),ObservedExitCode:exitcode(0),NegativeRejected:true},
            {ID:"SYN-C",State:"BLOCKED",Branch:"research/r051-c",
             SourceSHA:strings.Repeat("c",40),NextBlocker:"RIGHTS_HOLD: no operation-specific source grant"},
        },
    }
}
func cloneRep(r ActorRep) ActorRep {
    r.Packets=append([]PacketResult(nil),r.Packets...)
    return r
}
func TestR060LaneHappy(t *testing.T) {
    t.Parallel()
    b:=syntheticBatch()
    r:=syntheticRep()
    s,err:=ValidateActorRep(b,r)
    if err!=nil{t.Fatal(err)}
    if s.Status!="STRUCTURALLY_VALID_SELF_REPORT_NOT_INDEPENDENTLY_VERIFIED" ||
       s.ReportedExecuted!=2 || s.ReportedBlocked!=1 || s.ReportedNotRun!=0 {
       t.Fatalf("false eligible/executed result: %+v",s)
    }
    // An exhausted actor may legitimately report no work; never fabricate PASS.
    r=cloneRep(r)
    r.Packets[0]=PacketResult{ID:"SYN-A",State:"NOT_RUN",Branch:"research/r051-a",
        SourceSHA:strings.Repeat("a",40),NextBlocker:"LOCAL_CAPACITY_EXHAUSTED"}
    r.Packets[1]=PacketResult{ID:"SYN-B",State:"BLOCKED",Branch:"research/r051-b",
        SourceSHA:strings.Repeat("b",40),NextBlocker:"ACTOR_UNAVAILABLE"}
    s,err=ValidateActorRep(b,r)
    if err!=nil||s.ReportedExecuted!=0||s.ReportedNotRun!=1||s.ReportedBlocked!=2 {
        t.Fatalf("capacity recovery invented work: %+v %v",s,err)
    }
}
func TestR060LaneAdversarial(t *testing.T) {
    cases:=map[string]func(*ActorRep){
        "duplicated-result":func(r *ActorRep){r.Packets[1].ID="SYN-A"},
        "unknown-id":func(r *ActorRep){r.Packets[0].ID="MADE_UP"},
        "wrong-branch":func(r *ActorRep){r.Packets[0].Branch="research/fake"},
        "bad-source-sha":func(r *ActorRep){r.Packets[0].SourceSHA="not-a-commit"},
        "uppercase-source-sha":func(r *ActorRep){r.Packets[0].SourceSHA=strings.Repeat("A",40)},
        "gated-fake-pass":func(r *ActorRep){r.Packets[2].State="PASS_NARROW"},
        "pass-no-test":func(r *ActorRep){r.Packets[0].TestCommand=""},
        "pass-no-evidence":func(r *ActorRep){r.Packets[0].TestEvidenceSHA256=""},
        "pass-malformed-hash":func(r *ActorRep){r.Packets[0].TestEvidenceSHA256=strings.Repeat("z",64)},
        "pass-no-negative":func(r *ActorRep){r.Packets[0].NegativeRejected=false},
        "pass-no-exit":func(r *ActorRep){r.Packets[0].ObservedExitCode=nil},
        "pass-nonzero-exit":func(r *ActorRep){r.Packets[0].ObservedExitCode=exitcode(12)},
        "pass-hidden-failure":func(r *ActorRep){r.Packets[0].FirstFailure="silent"},
        "blocked-no-next":func(r *ActorRep){r.Packets[2].NextBlocker=""},
        "blocked-claims-test":func(r *ActorRep){r.Packets[2].ObservedExitCode=exitcode(0)},
        "notrun-claims-command":func(r *ActorRep){r.Packets[0].State="NOT_RUN"},
        "fail-zero-exit":func(r *ActorRep){r.Packets[0].State="FAIL"},
        "fail-no-blocker":func(r *ActorRep){r.Packets[0].State="FAIL";r.Packets[0].ObservedExitCode=exitcode(3);r.Packets[0].FirstFailure="native BAD"},
        "unknown-state":func(r *ActorRep){r.Packets[0].State="ACCEPTED"},
        "missing-actor-model":func(r *ActorRep){r.Model=""},
        "missing-result":func(r *ActorRep){r.Packets=r.Packets[:2]},
    }
    for name,fn:=range cases{
        t.Run(name,func(t *testing.T){
            t.Parallel()
            r:=cloneRep(syntheticRep())
            fn(&r)
            got,err:=ValidateActorRep(syntheticBatch(),r)
            if err==nil||!strings.Contains(err.Error(),"R060_REP_HOLD"){
                t.Fatalf("invalid claim admitted: result=%+v err=%v",got,err)
            }
        })
    }
}
