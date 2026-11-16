package main

import (
    "encoding/json"
    "strings"
    "testing"
)

func syntheticBatch() Batch {
    return Batch{
        Schema:Schema,
        Authority:map[string]string{
            "project":"synthetic/source-safe fixture", "owning_dle":"synthetic fixture",
            "wow":"canonical governance source pointer",
        },
        Scope:"PUBLIC_ORIGINAL_SYNTHETIC_TEST_ONLY",
        MaxConcurrent:3,MinEligible:2,
        Admission:Admission{true,true,true,true},
        Packets:[]Packet{
            {ID:"SYN-A",Owner:"ci-probe",State:"READY",Venue:"PUBLIC_SOURCE_ONLY",
                AssetClass:"SOURCE_ONLY",SourceDLE:"synthetic",
                OwnedPaths:[]string{"research/r051-batch/a/**"},
                Branch:"research/r051-a",Deliverable:"Independent indexed geometry fixture",
                Oracle:"Raw source hash and deterministic exact-coordinate test",
                Negative:"Reject corrupt glTF target",Fallback:"Report HOLD and switch lane",
                MaxCorrectiveCycles:1},
            {ID:"SYN-B",Owner:"ci-probe",State:"READY",Venue:"PUBLIC_SOURCE_ONLY",
                AssetClass:"SOURCE_ONLY",SourceDLE:"synthetic",
                OwnedPaths:[]string{"research/r051-batch/b/**"},
                Branch:"research/r051-b",Deliverable:"Independent morph control test",
                Oracle:"Exactly 24 checked commands",Negative:"Reject stale plan",
                Fallback:"Report HOLD and switch lane",MaxCorrectiveCycles:1},
            {ID:"SYN-C",Owner:"ci-probe",State:"GATED",Venue:"LOCAL_PRIVATE_METADATA_ONLY",
                AssetClass:"RESTRICTED",SourceDLE:"synthetic",
                OwnedPaths:[]string{"research/r051-batch/c/**"},
                Branch:"research/r051-c",Requires:[]string{"rights"},Deliverable:"Rights preflight",
                Oracle:"Typed rights gate",Negative:"Reject unknown rights",
                Fallback:"Use only synthetic metadata",MaxCorrectiveCycles:1},
        },
        RepReceiptRequired:[]string{"actor","model","os","cwd","source_sha","branches",
            "context_tokens","eligible_packet_ids","completed_ids","status","test_receipt"},
        StopRule:"At most one correction then switch to another eligible lane",
        Reconciliation:"DLE is the single authoritative workset",
    }
}
func TestLaneStructure(t *testing.T) {
    t.Parallel()
    b:=syntheticBatch()
    r,err:=Validate(b)
    if err!=nil{t.Fatal(err)}
    if r.Status!="VALID_SOURCE_SAFE_CONTRACT_ONLY"||r.Packets!=3||
        r.Eligible!=2||r.Gated!=1||r.IndependentPairs!=1 {
        t.Fatalf("bad eligibility or packet statistics %+v",r)
    }
    raw,err:=json.Marshal(b)
    if err!=nil{t.Fatal(err)}
    var decoded Batch
    if err:=json.Unmarshal(raw,&decoded);err!=nil{t.Fatal(err)}
    if _,err:=Validate(decoded);err!=nil{t.Fatal(err)}
}
func TestLaneAdversarial(t *testing.T) {
    cases:=map[string]func(*Batch){
        "shared-path":func(b *Batch){b.Packets[1].OwnedPaths[0]="research/r051-batch/a/sub/**"},
        "same-branch":func(b *Batch){b.Packets[1].Branch=b.Packets[0].Branch},
        "rightless-ready":func(b *Batch){b.Packets[2].State="READY"},
        "private-public":func(b *Batch){b.Packets[2].Venue="PUBLIC_SOURCE_ONLY"},
        "missing-negative":func(b *Batch){b.Packets[0].Negative=""},
        "no-oracle":func(b *Batch){b.Packets[1].Oracle=""},
        "unbounded-correction":func(b *Batch){b.Packets[1].MaxCorrectiveCycles=99},
        "fake-parallel":func(b *Batch){b.Packets[1].State="GATED";b.Packets[1].Requires=[]string{"no source"}},
        "file-traversal":func(b *Batch){b.Packets[2].OwnedPaths=[]string{"../../sensitive/**"}},
        "missing-data-gate":func(b *Batch){b.Admission.NoProtectedMediaInPublic=false},
        "unsupported-asset":func(b *Batch){b.Packets[0].AssetClass="UNKNOWN"},
        "unscoped-branch":func(b *Batch){b.Packets[0].OwnedPaths=nil},
    }
    for name,mutate:=range cases{
        t.Run(name,func(t *testing.T){
            t.Parallel()
            b:=syntheticBatch()
            mutate(&b)
            _,err:=Validate(b)
            if err==nil||!strings.Contains(err.Error(),"R051_BATCH_HOLD"){
                t.Fatalf("negative guard passed unexpectedly: %v",err)
            }
        })
    }
}
func TestLaneThroughput(t *testing.T) {
    t.Parallel()
    b:=syntheticBatch()
    // A nominal rep has 2 READY packets and 1 gate; the gate cannot be
    // counted as throughput. Never confuse declared with actual overlap.
    r,err:=Validate(b)
    if err!=nil{t.Fatal(err)}
    if r.IndependentPairs!=1||r.Eligible!=2{t.Fatal(r)}
    if strings.Contains(r.Status,"ACTUAL_RUNNING") {t.Fatal("fabricated concurrency")}
    // Even if desired concurrency is four, actual evidence remains unknown.
    b.MaxConcurrent=4
    r,err=Validate(b)
    if err!=nil||r.MaxConcurrent!=4||r.Eligible!=2{t.Fatal(r,err)}
    // If a blocked packet is listed as READY with no authorized path,
    // it must not magically create a successful 3-lane rep.
    b.Packets[2].State="READY"
    _,err=Validate(b)
    if err==nil{t.Fatal("gated rights incorrectly counted as active")}
}
