// R060 verifies a bounded local-actor rep receipt against the existing R051
// batch manifest, without granting execution, admission, acceptance or authority.
// This is a passive validator. Public fixtures are synthetic only.
package main

import (
    "encoding/hex"
    "fmt"
    "slices"
    "strings"
)

const RepSchema = "scp.r060.actor-rep-observation.v1"

type PacketResult struct {
    ID string `json:"id"`
    State string `json:"state"`
    Branch string `json:"branch"`
    SourceSHA string `json:"source_sha"`
    TestCommand string `json:"test_command,omitempty"`
    TestEvidenceSHA256 string `json:"test_evidence_sha256,omitempty"`
    NegativeRejected bool `json:"negative_rejected"`
    ObservedExitCode *int `json:"observed_exit_code,omitempty"`
    FirstFailure string `json:"first_failure,omitempty"`
    NextBlocker string `json:"next_blocker,omitempty"`
}

type ActorRep struct {
    Schema string `json:"schema"`
    Actor string `json:"actor"`
    Model string `json:"model"`
    OS string `json:"os"`
    Repo string `json:"repo"`
    Branch string `json:"branch"`
    RepID string `json:"rep_id"`
    Packets []PacketResult `json:"packets"`
}
type RepReview struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    ReportedExecuted int `json:"reported_executed"`
    ReportedBlocked int `json:"reported_blocked"`
    ReportedNotRun int `json:"reported_not_run"`
    Limits string `json:"limits"`
}

func isHex(s string, bytes int) bool {
    if len(s)!=bytes*2{return false}
    _,err:=hex.DecodeString(s)
    return err==nil && strings.ToLower(s)==s
}

func ValidateActorRep(manifest Batch, rep ActorRep) (RepReview,error) {
    out:=RepReview{
        Schema:"r060.actor-rep-review.v1",
        Status:"HOLD_SOURCE_RECEIPT_NOT_ACCEPTED",
        Limits:"Static manifest/receipt consistency only; actor execution, actual concurrency, native Blender assets, rights, independent test results and owner acceptance NOT VERIFIED",
    }
    reject:=func(s string)(RepReview,error) {return out,fmt.Errorf("R060_REP_HOLD %s",s)}
    if _,err:=Validate(manifest);err!=nil{return reject("base R051 batch invalid: "+err.Error())}
    if rep.Schema!=RepSchema||rep.Actor==""||rep.Model==""||rep.OS==""||rep.Repo==""||rep.Branch==""||rep.RepID=="" {
        return reject("missing source-scoped actor identity or rep schema")
    }
    if len(rep.Packets)!=len(manifest.Packets){return reject("packet results do not cover exact manifest")}
    byID:=make(map[string]Packet,len(manifest.Packets))
    for _,p:=range manifest.Packets {byID[p.ID]=p}
    seen:=map[string]bool{}
    for _,r:=range rep.Packets {
        p,exists:=byID[r.ID]
        if !exists||seen[r.ID]{return reject("unknown or duplicate packet result")}
        seen[r.ID]=true
        if r.Branch!=p.Branch||!isHex(r.SourceSHA,20){return reject("source/branch lineage missing or changed: "+r.ID)}
        if p.State=="GATED" && !slices.Contains([]string{"BLOCKED","NOT_RUN"},r.State) {
            return reject("gated rights/prerequisite packet falsely executed: "+r.ID)
        }
        if p.State=="GATED" && len(p.Requires)==0 {
            return reject("missing gated prerequisite")
        }
        switch r.State {
        case "PASS_NARROW":
            if p.State!="READY" {return reject("ineligible packet reported pass")}
            if r.TestCommand==""||!isHex(r.TestEvidenceSHA256,32)||!r.NegativeRejected||
                r.ObservedExitCode==nil||*r.ObservedExitCode!=0 {
                return reject("pass lacks exact observed test, digest, negative and zero exit: "+r.ID)
            }
            if r.FirstFailure!=""||r.NextBlocker!=""{
                return reject("passing packet hides unresolved failure/blocker")}
            out.ReportedExecuted++
        case "FAIL":
            if p.State!="READY" {return reject("ineligible packet reported failure as execution")}
            if r.TestCommand==""||r.ObservedExitCode==nil||*r.ObservedExitCode==0||
                r.FirstFailure==""||r.NextBlocker==""{
                return reject("failure missing observed command/nonzero first failure/next blocker")
            }
            out.ReportedExecuted++
        case "BLOCKED":
            if r.NextBlocker=="" {return reject("blocked packet missing typed frontier")}
            if r.TestEvidenceSHA256!=""||r.ObservedExitCode!=nil||r.NegativeRejected {
                return reject("blocked packet pretends test execution")}
            out.ReportedBlocked++
        case "NOT_RUN":
            if r.TestCommand!=""||r.TestEvidenceSHA256!=""||r.ObservedExitCode!=nil||
                r.NegativeRejected||r.FirstFailure!=""{
                return reject("NOT_RUN packet carries claimed observed work")}
            out.ReportedNotRun++
        default:
            return reject("unknown packet execution state: "+r.ID)
        }
    }
    // Self-reported receipts must not be promoted into CI/owner-reviewed PASS.
    out.Status="STRUCTURALLY_VALID_SELF_REPORT_NOT_INDEPENDENTLY_VERIFIED"
    return out,nil
}
