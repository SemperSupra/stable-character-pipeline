package avobserver

// Independent, versioned evaluator of the decoded synthetic hoof-onset oracle.
// This test does not qualify acoustic identity, horse contact, or natural speech.
import (
    "crypto/sha256"
    "encoding/binary"
    "encoding/hex"
    "encoding/json"
    "os"
    "runtime"
    "sort"
    "testing"
    "time"
)

type audioQualityCase struct {
    ID string
    Expected string
    Clock Clock
    PCM []int16
}
type audioQualityCaseReceipt struct {
    ID string `json:"id"`
    Expected string `json:"expected"`
    Actual string `json:"actual"`
    ClockSHA string `json:"clock_sha256"`
    PCMSHA string `json:"pcm_sha256"`
    ElapsedNS int64 `json:"elapsed_ns"`
}
type audioValidatorQuality struct {
    Schema string `json:"schema"`
    Validator string `json:"validator"`
    ValidatorSHA string `json:"validator_sha256"`
    Corpus string `json:"corpus"`
    CorpusSHA string `json:"corpus_sha256"`
    SourceClass string `json:"source_class"`
    CaseCount int `json:"case_count"`
    Confusion map[string]map[string]int `json:"confusion"`
    RejectionDetection struct{
        Detected int `json:"detected"`
        Total int `json:"total"`
    } `json:"rejection_detection"`
    FalseAcceptanceCount int `json:"false_acceptance_count"`
    FalseRejectionCount int `json:"false_rejection_count"`
    HardErrorCount int `json:"hard_error_count"`
    ContractMismatchCount int `json:"contract_mismatch_count"`
    Runtime struct {
        Go string `json:"go"`
        LatencyP50NS int64 `json:"latency_p50_ns"`
        LatencyP95NS int64 `json:"latency_p95_ns"`
        LatencyMaxNS int64 `json:"latency_max_ns"`
    } `json:"runtime"`
    Cases []audioQualityCaseReceipt `json:"cases"`
    Verdict string `json:"verdict"`
    AnimalAcousticRealism string `json:"animal_acoustic_realism"`
    PhysicalContact string `json:"physical_contact"`
    MergeReleaseCPEApproval bool `json:"merge_release_CPE_approval"`
}
func bytesSHA(b []byte)string {
    h:=sha256.Sum256(b)
    return hex.EncodeToString(h[:])
}
func audioQualityHashPCM(pcm []int16)string {
    b:=make([]byte,2*len(pcm))
    for i,v:=range pcm {binary.LittleEndian.PutUint16(b[2*i:],uint16(v))}
    return bytesSHA(b)
}
func fixtureQualityCorpus()[]audioQualityCase{
    rows:=[]audioQualityCase{}
    add:=func(id,want string,at []int,clockChange func(*Clock),audioChange func([]int16)[]int16){
        c:=fixtureClock()
        if clockChange!=nil {clockChange(&c)}
        pcm:=synthetic(at)
        if audioChange!=nil{pcm=audioChange(pcm)}
        rows=append(rows,audioQualityCase{ID:id,Expected:want,Clock:c,PCM:pcm})
    }
    valid:=[]int{0,24000,48000,72000}
    add("valid-planned-dry-hoof-alignment","ACCEPT",valid,nil,nil)
    add("simultaneous-events-one-audible-group","ACCEPT",[]int{0,48000},func(c *Clock){
        c.Events[1].Frame=0;c.Events[1].Sample=0
        c.Events[2].Frame=24;c.Events[2].Sample=48000
        c.Events[3].Frame=24;c.Events[3].Sample=48000
    },nil)
    add("ten-ms-source-onset-jitter-in-tolerance","ACCEPT",[]int{0,24000,48480,72000},nil,nil)
    add("encoded-track-silent-equivalent","REJECT",[]int{},nil,nil)
    add("missing-audible-beat","REJECT",[]int{0,24000,72000},nil,nil)
    add("extra-audible-beat","REJECT",[]int{0,24000,48000,62000,72000},nil,nil)
    add("late-outside-forty-ms-tolerance","REJECT",[]int{0,24000,52800,72000},nil,nil)
    add("early-outside-forty-ms-tolerance","REJECT",[]int{0,19200,48000,72000},nil,nil)
    add("near-silent-subthreshold-track","REJECT",valid,nil,func(p []int16)[]int16{
        for i:=range p{p[i]/=100};return p
    })
    add("unauthorized-physical-contact-claim","REJECT",valid,func(c *Clock){c.Basis="PHYSICALLY_OBSERVED"},nil)
    add("unsupported-fps","REJECT",valid,func(c *Clock){c.FPS=29},nil)
    add("duplicate-source-hoof-event","REJECT",valid,func(c *Clock){c.Events[1]=c.Events[0]},nil)
    add("truncated-decoded-track","REJECT",valid,nil,func(p []int16)[]int16{return p[:len(p)/2]})
    add("foreign-actor-event","REJECT",valid,func(c *Clock){c.Events[0].ActorID="other-pony"},nil)
    return rows
}
func qualityClassify(c Clock,pcm []int16,oracle func(Clock,[]int16)(Receipt,error))string{
    r,err:=oracle(c,pcm)
    if err!=nil{return "REJECT"}
    if r.Verdict=="PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY"{return "ACCEPT"}
    if r.Verdict=="FAIL_AUDIO_TRANSIENT_ALIGNMENT"{return "REJECT"}
    return "ERROR"
}
func measureAudioValidatorQuality(oracle func(Clock,[]int16)(Receipt,error))audioValidatorQuality{
    corpus:=fixtureQualityCorpus()
    labels:=[]string{"ACCEPT","ABSTAIN","REJECT","ERROR"}
    q:=audioValidatorQuality{
        Schema:"scp.validator.performance.v1",
        Validator:"scp.equine.av.decoded_pcm_onset",
        Corpus:"scp.equine.av.planned_dry_pcm_quality.v1",
        SourceClass:"ORIGINAL_SYNTHETIC_DECODED_EQUIVALENT_PCM",
        CaseCount:len(corpus),Confusion:map[string]map[string]int{},
        Cases:[]audioQualityCaseReceipt{},AnimalAcousticRealism:"UNKNOWN",
        PhysicalContact:"UNKNOWN",
    }
    data,err:=os.ReadFile("observer.go");if err!=nil{panic(err)}
    q.ValidatorSHA=bytesSHA(data)
    q.Runtime.Go=runtime.Version()
    for _,label:=range labels{
        q.Confusion[label]=map[string]int{}
        for _,actual:=range labels{q.Confusion[label][actual]=0}
    }
    times:=[]int64{}
    sourceLabels:=[]string{}
    for _,c:=range corpus{
        cblob,_:=json.Marshal(c.Clock)
        clockSHA,pcmSHA:=bytesSHA(cblob),audioQualityHashPCM(c.PCM)
        sourceLabels=append(sourceLabels,c.ID+"|"+c.Expected+"|"+clockSHA+"|"+pcmSHA)
        now:=time.Now()
        actual:=qualityClassify(c.Clock,c.PCM,oracle)
        delta:=time.Since(now).Nanoseconds()
        times=append(times,delta)
        q.Confusion[c.Expected][actual]++
        q.Cases=append(q.Cases,audioQualityCaseReceipt{
            ID:c.ID,Expected:c.Expected,Actual:actual,
            ClockSHA:clockSHA,PCMSHA:pcmSHA,ElapsedNS:delta,
        })
        if actual!=c.Expected{q.ContractMismatchCount++}
        if actual=="ACCEPT"&&c.Expected!="ACCEPT"{q.FalseAcceptanceCount++}
        if actual!="ACCEPT"&&c.Expected=="ACCEPT"{q.FalseRejectionCount++}
        if actual=="ERROR"{q.HardErrorCount++}
        if c.Expected=="REJECT"{
            q.RejectionDetection.Total++
            if actual=="REJECT"{q.RejectionDetection.Detected++}
        }
    }
    labelsData,_:=json.Marshal(sourceLabels)
    q.CorpusSHA=bytesSHA(labelsData)
    sort.Slice(times,func(i,j int)bool{return times[i]<times[j]})
    q.Runtime.LatencyP50NS=times[(len(times)+1)/2-1]
    q.Runtime.LatencyP95NS=times[(95*len(times)+99)/100-1]
    q.Runtime.LatencyMaxNS=times[len(times)-1]
    q.Verdict="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY"
    if q.ContractMismatchCount!=0{q.Verdict="FAIL_VALIDATOR_CONTROLS"}
    return q
}
func TestAudioValidatorQualityAndReceipt(t *testing.T){
    q:=measureAudioValidatorQuality(Observe)
    if q.CaseCount!=14||q.RejectionDetection.Total!=11||q.RejectionDetection.Detected!=11||
       q.FalseAcceptanceCount!=0||q.FalseRejectionCount!=0||
       q.ContractMismatchCount!=0||q.HardErrorCount!=0||q.Confusion["ACCEPT"]["ACCEPT"]!=3||
       q.Verdict!="PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY" {
        t.Fatalf("SYNTHETIC_AUDIO_VALIDATOR_QUALITY_RED %+v",q)
    }
    if path:=os.Getenv("SCP_AUDIO_VALIDATOR_PERF_OUT");path!=""{
        blob,err:=json.MarshalIndent(q,"","  ");if err!=nil{t.Fatal(err)}
        if err=os.WriteFile(path,append(blob,'\n'),0600);err!=nil{t.Fatal(err)}
    }
    t.Logf("AUDIO_VALIDATOR_QUALITY source=%s corpus=%s p95ns=%d",q.ValidatorSHA,q.CorpusSHA,q.Runtime.LatencyP95NS)
}
func TestAudioQualityHarnessRejectsBrokenOracles(t *testing.T){
    alwaysAccept:=func(Clock,[]int16)(Receipt,error){
        return Receipt{Verdict:"PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY"},nil
    }
    accepted:=measureAudioValidatorQuality(alwaysAccept)
    if accepted.FalseAcceptanceCount!=11||accepted.ContractMismatchCount!=11{
        t.Fatalf("always-accept oracle fooled measurement: %+v",accepted)
    }
    alwaysReject:=func(Clock,[]int16)(Receipt,error){
        return Receipt{Verdict:"FAIL_AUDIO_TRANSIENT_ALIGNMENT"},nil
    }
    rejected:=measureAudioValidatorQuality(alwaysReject)
    if rejected.FalseRejectionCount!=3||rejected.ContractMismatchCount!=3{
        t.Fatalf("always-reject oracle fooled measurement: %+v",rejected)
    }
}
