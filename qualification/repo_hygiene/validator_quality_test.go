package main

// Versioned hostile corpus measures the read-only auditor itself, not just the
// number of PRs it reports. No GitHub write permission, network, or extra service.
import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "os"
    "runtime"
    "sort"
    "strings"
    "testing"
    "time"
)

type qualityCase struct {
    Name string
    Want string
    Source Snapshot
}
type qualityCaseReceipt struct {
    Name string `json:"id"`
    Expected string `json:"expected"`
    Actual string `json:"actual"`
    SourceSHA string `json:"source_sha256"`
    LatencyNS int64 `json:"elapsed_ns"`
}
type qualityLedger struct {
    Schema string `json:"schema"`
    Validator string `json:"validator"`
    ValidatorSHA string `json:"validator_sha256"`
    Corpus string `json:"corpus"`
    CorpusSHA string `json:"corpus_sha256"`
    SourceClass string `json:"source_class"`
    CaseCount int `json:"case_count"`
    Confusion map[string]map[string]int `json:"confusion"`
    FalseAcceptanceCount int `json:"false_acceptance_count"`
    FalseRejectionCount int `json:"false_rejection_count"`
    HardErrorCount int `json:"hard_error_count"`
    ContractMismatchCount int `json:"contract_mismatch_count"`
    RejectionDetection struct {
        Detected int `json:"detected"`
        Total int `json:"total"`
    } `json:"rejection_detection"`
    Runtime struct {
        Go string `json:"go"`
        LatencyP50NS int64 `json:"latency_p50_ns"`
        LatencyP95NS int64 `json:"latency_p95_ns"`
        Scale256NS int64 `json:"scale_256_open_pr_ns"`
        Scale256ApproxBytes uint64 `json:"scale_256_alloc_bytes_approx"`
    } `json:"runtime"`
    Cases []qualityCaseReceipt `json:"cases"`
    Verdict string `json:"verdict"`
    MergeReleaseCPEApproval bool `json:"merge_release_CPE_approval"`
}
func hashJSON(v any) string {
    data,err:=json.Marshal(v);if err!=nil{panic(err)}
    d:=sha256.Sum256(data);return hex.EncodeToString(d[:])
}
func hostileAuditorCases() []qualityCase {
    cases:=[]qualityCase{}
    add:=func(name,want string, mutate func(*Snapshot)){
        s:=base() // source fixture is independent of classification output
        if mutate!=nil{mutate(&s)}
        cases=append(cases,qualityCase{Name:name,Want:want,Source:s})
    }
    add("valid-fully-open", "ACCEPT", nil)
    add("incomplete-pagination-must-hold", "ABSTAIN",func(s *Snapshot){s.Complete=false})
    add("private-repository-must-reject", "REJECT",func(s *Snapshot){s.Repo="SemperSupra/stable-character-pipeline-private"})
    add("closed-row-must-reject", "REJECT",func(s *Snapshot){s.PRs[0].State="closed"})
    add("duplicate-number-must-reject", "REJECT",func(s *Snapshot){s.PRs[1].Number=s.PRs[0].Number})
    add("short-ref-must-reject", "REJECT",func(s *Snapshot){s.PRs[0].Head.SHA="bad"})
    add("foreign-pr-url-must-reject", "REJECT",func(s *Snapshot){s.PRs[0].HTMLURL="https://other.example/pull/292"})
    add("invalid-asof-must-reject", "REJECT",func(s *Snapshot){s.AsOf="not-a-date"})
    add("merged-open-row-must-reject", "REJECT",func(s *Snapshot){now:=time.Date(2026,11,6,0,0,0,0,time.UTC);s.PRs[1].MergedAt=&now})
    add("zero-number-must-reject", "REJECT",func(s *Snapshot){s.PRs[1].Number=0})
    add("empty-head-ref-must-reject", "REJECT",func(s *Snapshot){s.PRs[1].Head.Ref=""})
    add("invalid-schema-must-reject", "REJECT",func(s *Snapshot){s.Schema="unsafe"})
    add("complete-without-pages-must-reject", "REJECT",func(s *Snapshot){s.FetchPages=0})
    add("complete-overfull-page-must-reject", "REJECT",func(s *Snapshot){
        s.FetchPages=1
        for i:=2;i<101;i++{
            p:=s.PRs[1]
            p.Number=i+100
            p.Head.Ref=fmt.Sprintf("extra-%d",i)
            p.Head.SHA=fmt.Sprintf("%040x",i)
            s.PRs=append(s.PRs,p)
        }
    })

    return cases
}
func classifyAuditor(s Snapshot) string{
    r,err:=audit(s,14);if err!=nil{return "REJECT"}
    if r.Mutations!=0{return "ERROR"}
    for _,p:=range r.Findings{if p.Action!="RETAIN_AND_REVIEW"{return "ERROR"}}
    if !r.Complete{return "ABSTAIN"}
    return "ACCEPT"
}
func rank(values []int64,num,den int)int64{
    sort.Slice(values,func(i,j int)bool{return values[i]<values[j]})
    return values[(len(values)*num+den-1)/den-1]
}
func syntheticScale(n int)Snapshot{
    s:=base()
    s.FetchPages=(n+99)/100
    s.PRs=nil
    for i:=0;i<n;i++{
        s.PRs=append(s.PRs,Pull{
            Number:i+1,State:"open",Draft:true,
            Head:CommitRef{Ref:fmt.Sprintf("test-%d",i+1),SHA:fmt.Sprintf("%040x",i+1)},
            Base:CommitRef{Ref:"main",SHA:strings.Repeat("a",40)},
            UpdatedAt:time.Date(2026,11,5,0,0,0,0,time.UTC),
        })
    }
    return s
}
func measureAuditorQuality(classify func(Snapshot)string)qualityLedger{
    cases:=hostileAuditorCases()
    classes:=[]string{"ACCEPT","ABSTAIN","REJECT","ERROR"}
    v:=qualityLedger{Schema:"scp.validator.performance.v1",
        Validator:"scp.r009.repo_hygiene.readonly",
        Corpus:"scp.r009.hygiene_auditor.hostile.v2",
        SourceClass:"ORIGINAL_SYNTHETIC_PUBLIC_READONLY_FIXTURES",
        CaseCount:len(cases),Confusion:map[string]map[string]int{},
        Cases:[]qualityCaseReceipt{},
    }
    file,err:=os.ReadFile("main.go");if err!=nil{panic(err)}
    sum:=sha256.Sum256(file);v.ValidatorSHA=hex.EncodeToString(sum[:])
    v.CorpusSHA=hashJSON(cases)
    v.Runtime.Go=runtime.Version()
    for _,label:=range classes{
        v.Confusion[label]=map[string]int{}
        for _,actual:=range classes{v.Confusion[label][actual]=0}
    }
    times:=make([]int64,0,len(cases))
    for _,c:=range cases {
        started:=time.Now()
        observed:=classify(c.Source)
        duration:=time.Since(started).Nanoseconds()
        if _,ok:=v.Confusion[c.Want][observed];!ok{observed="ERROR"}
        times=append(times,duration)
        v.Confusion[c.Want][observed]++
        v.Cases=append(v.Cases,qualityCaseReceipt{
            Name:c.Name,Expected:c.Want,Actual:observed,
            SourceSHA:hashJSON(c.Source),LatencyNS:duration,
        })
        if c.Want!=observed{v.ContractMismatchCount++}
        if c.Want!="ACCEPT"&&observed=="ACCEPT"{v.FalseAcceptanceCount++}
        if c.Want=="ACCEPT"&&observed!="ACCEPT"{v.FalseRejectionCount++}
        if observed=="ERROR"{v.HardErrorCount++}
        if c.Want=="REJECT"{v.RejectionDetection.Total++;if observed=="REJECT"{v.RejectionDetection.Detected++}}
    }
    v.Runtime.LatencyP50NS=rank(append([]int64(nil),times...),1,2)
    v.Runtime.LatencyP95NS=rank(append([]int64(nil),times...),95,100)
    var before,after runtime.MemStats
    scale:=syntheticScale(256)
    runtime.ReadMemStats(&before)
    started:=time.Now()
    result,err:=audit(scale,14)
    v.Runtime.Scale256NS=time.Since(started).Nanoseconds()
    runtime.ReadMemStats(&after)
    if after.TotalAlloc>=before.TotalAlloc{v.Runtime.Scale256ApproxBytes=after.TotalAlloc-before.TotalAlloc}
    if err!=nil||result.Mutations!=0||result.PRsScanned!=256||!result.Complete {
        v.ContractMismatchCount++
    }
    v.Verdict="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY"
    if v.ContractMismatchCount!=0{v.Verdict="FAIL_VALIDATOR_CONTROLS"}
    return v
}
func TestHygieneValidatorQualityReceipt(t *testing.T){
    r:=measureAuditorQuality(classifyAuditor)
    if r.CaseCount!=14||r.RejectionDetection.Total!=12||r.RejectionDetection.Detected!=12||
        r.FalseAcceptanceCount!=0||r.FalseRejectionCount!=0||r.ContractMismatchCount!=0||
        r.Confusion["ABSTAIN"]["ABSTAIN"]!=1||r.Verdict!="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY"{
        t.Fatalf("validator controls failed: %+v",r)
    }
    if path:=os.Getenv("SCP_VALIDATOR_PERF_OUT");path!=""{
        data,err:=json.MarshalIndent(r,"","  ");if err!=nil{t.Fatal(err)}
        if err=os.WriteFile(path,append(data,'\n'),0600);err!=nil{t.Fatal(err)}
    }
    t.Logf("VALIDATOR_QUALITY_SYNTHETIC_ONLY source=%s corpus=%s p95ns=%d scale256ns=%d",r.ValidatorSHA,r.CorpusSHA,r.Runtime.LatencyP95NS,r.Runtime.Scale256NS)
}
func TestQualityHarnessDetectsBrokenAuditor(t *testing.T){
    alwaysAccept:=func(Snapshot)string{return "ACCEPT"}
    r:=measureAuditorQuality(alwaysAccept)
    if r.FalseAcceptanceCount!=13||r.ContractMismatchCount!=13||r.Verdict!="FAIL_VALIDATOR_CONTROLS"{
        t.Fatalf("broken auditor falsely passed: %+v",r)
    }
}
func BenchmarkAuditHygiene256(b *testing.B){
    s:=syntheticScale(256)
    b.ReportAllocs()
    for i:=0;i<b.N;i++{
        out,err:=audit(s,14)
        if err!=nil||out.Mutations!=0||out.PRsScanned!=256{b.Fatal("bad audit")}
    }
}
