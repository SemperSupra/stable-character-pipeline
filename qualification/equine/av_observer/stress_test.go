package avobserver

// Bounded, independent synthetic signal stress observation. This is telemetry,
// not a claim of real pony acoustic identity or a replacement onset algorithm.
// A failing stress case must stay visible rather than tuning the source threshold.
import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "math"
    "os"
    "sort"
    "testing"
    "time"
)

type stressCase struct{
    ID string
    Expected string
    PCM []int16
    Clock Clock
}
type stressOutcome struct{
    ID string `json:"id"`
    Expected string `json:"expected"`
    Observed string `json:"observed"`
    DecodedPCMSHA256 string `json:"decoded_pcm_sha256"`
    CountOnsets int `json:"count_onsets"`
    CountMatches int `json:"count_matches"`
    Reasons []string `json:"reasons"`
    ElapsedNS int64 `json:"elapsed_ns"`
}
type stressTelemetry struct{
    Schema string `json:"schema"`
    ValidatorSHA256 string `json:"validator_sha256"`
    Corpus string `json:"corpus"`
    CorpusSHA256 string `json:"corpus_sha256"`
    SourceClass string `json:"source_class"`
    Cases []stressOutcome `json:"cases"`
    PositiveCount int `json:"positive_count"`
    NegativeCount int `json:"negative_count"`
    UncalibratedCount int `json:"uncalibrated_count"`
    FalseAcceptanceCount int `json:"false_acceptance_count"`
    FalseRejectionCount int `json:"false_rejection_count"`
    UncalibratedCasesWithPass int `json:"uncalibrated_cases_with_pass"`
    RuntimeP95NS int64 `json:"runtime_p95_ns"`
    Verdict string `json:"verdict"`
    PhysicalContact string `json:"physical_contact"`
    AnimalSoundIdentity string `json:"animal_sound_identity"`
    MergeReleaseCPEApproval bool `json:"merge_release_CPE_approval"`
}
func stressSHA(blob []byte)string{sum:=sha256.Sum256(blob);return hex.EncodeToString(sum[:])}
func layerWind(pcm []int16,amplitude float64)[]int16{
    out:=append([]int16(nil),pcm...)
    for i,v:=range out{
        sec:=float64(i)/Rate
        // Repeatable uncorrelated-ish mixed low-frequency room/wind surrogate.
        delta:=amplitude*32767*(.7*math.Sin(2*math.Pi*23*sec)+
                    .3*math.Sin(2*math.Pi*61*sec))
        candidate:=int(math.Round(float64(v)+delta))
        if candidate>32767{candidate=32767}
        if candidate< -32768{candidate= -32768}
        out[i]=int16(candidate)
    }
    return out
}
func buildAVStressCorpus()[]stressCase{
    source:=fixtureClock()
    valid:=[]int{0,24000,48000,72000}
    dense:=fixtureClock()
    dense.Events[1].Frame=1
    dense.Events[1].Sample=2000
    dense.Events[2].Frame=24
    dense.Events[2].Sample=48000
    dense.Events[3].Frame=36
    dense.Events[3].Sample=72000
    return []stressCase{
        {"clean-source-four-events","ACCEPT",synthetic(valid),source},
        {"codec-like-ten-ms-positive-jitter","ACCEPT",synthetic([]int{0,24480,48000,72000}),source},
        {"dry-silent-missing-events","REJECT",synthetic([]int{}),source},
        {"dry-fifth-unplanned-event","REJECT",synthetic([]int{0,24000,48000,62000,72000}),source},
        {"low-wind-positive-uncalibrated","UNCALIBRATED",layerWind(synthetic(valid),.008),source},
        {"medium-wind-positive-uncalibrated","UNCALIBRATED",layerWind(synthetic(valid),.035),source},
        {"high-wind-positive-uncalibrated","UNCALIBRATED",layerWind(synthetic(valid),.09),source},
        {"close-spaced-doublet-uncalibrated","UNCALIBRATED",synthetic([]int{0,2000,48000,72000}),dense},
        {"wind-plus-extra-transient-uncalibrated","UNCALIBRATED",layerWind(synthetic([]int{0,24000,48000,62000,72000}),.025),source},
    }
}
func measureAVStress(t *testing.T)stressTelemetry{
    t.Helper()
    raw,err:=os.ReadFile("observer.go");if err!=nil{t.Fatal(err)}
    corpus:=buildAVStressCorpus()
    out:=stressTelemetry{Schema:"scp.equine.av_stress_telemetry.v1",
        ValidatorSHA256:stressSHA(raw),
        Corpus:"scp.equine.audio_stress_original_synthetic.v1",
        SourceClass:"ORIGINAL_SYNTHETIC_DRY_PCM_AND_DETERMINISTIC_WIND",
        Cases:[]stressOutcome{},PhysicalContact:"UNKNOWN_NOT_MEASURED",
        AnimalSoundIdentity:"UNKNOWN_UNIDENTIFIED_TRANSIENTS",
        Verdict:"STRESS_OBSERVATION_ONLY_SCIENTIFIC_HOLD"}
    durations:=[]int64{}
    basis:=[]string{}
    for _,c:=range corpus{
        clockBytes,err:=json.Marshal(c.Clock);if err!=nil{t.Fatal(err)}
        // Each source's exact PCM hash is also in observer Receipt; do not
        // permit the planned events to define measured onset positions.
        pcmSHA:=audioQualityHashPCM(c.PCM)
        basis=append(basis,c.ID+"|"+c.Expected+"|"+stressSHA(clockBytes)+"|"+pcmSHA)
        started:=time.Now()
        r,err:=Observe(c.Clock,c.PCM)
        elapsed:=time.Since(started).Nanoseconds()
        if err!=nil{t.Fatalf("stress source invalid %s: %v",c.ID,err)}
        durations=append(durations,elapsed)
        actual:="REJECT"
        if r.Verdict=="PASS_SYNTHETIC_TRANSIENT_ALIGNMENT_ONLY"{actual="ACCEPT"}else
        if r.Verdict!="FAIL_AUDIO_TRANSIENT_ALIGNMENT"{t.Fatalf("unsupported verdict %s",r.Verdict)}
        if r.AnimalAcousticRealism!="UNKNOWN"||r.ContactEvidence!="PLANNED_ONLY_NOT_PHYSICAL_CONTACT"||r.AudioIdentity!="UNIDENTIFIED_IMPULSE_TRANSIENTS"{t.Fatal("science promotion")}
        if c.Expected=="ACCEPT"{out.PositiveCount++;if actual!="ACCEPT"{out.FalseRejectionCount++}}
        if c.Expected=="REJECT"{out.NegativeCount++;if actual=="ACCEPT"{out.FalseAcceptanceCount++}}
        if c.Expected=="UNCALIBRATED"{out.UncalibratedCount++;if actual=="ACCEPT"{out.UncalibratedCasesWithPass++}}
        out.Cases=append(out.Cases,stressOutcome{ID:c.ID,Expected:c.Expected,Observed:actual,
            DecodedPCMSHA256:r.DecodedPCMSHA256,CountOnsets:len(r.ObservedOnsets),
            CountMatches:len(r.Matched),Reasons:r.Reasons,ElapsedNS:elapsed})
    }
    bytes,_:=json.Marshal(basis);out.CorpusSHA256=stressSHA(bytes)
    sort.Slice(durations,func(i,j int)bool{return durations[i]<durations[j]})
    out.RuntimeP95NS=durations[(95*len(durations)+99)/100-1]
    return out
}
func TestAudioStressTelemetryWithScientificHold(t *testing.T){
    s:=measureAVStress(t)
    if len(s.Cases)!=9||s.PositiveCount!=2||s.NegativeCount!=2||s.UncalibratedCount!=5||
       s.MergeReleaseCPEApproval||s.Verdict!="STRESS_OBSERVATION_ONLY_SCIENTIFIC_HOLD"{
        t.Fatalf("invalid stress qualification envelope %+v",s)
    }
    if s.FalseAcceptanceCount!=0||s.FalseRejectionCount!=0{
        t.Fatalf("existing clean/dry negative controls regressed %+v",s)
    }
    if p:=os.Getenv("SCP_AUDIO_STRESS_OUT");p!=""{
        b,err:=json.MarshalIndent(s,"","  ");if err!=nil{t.Fatal(err)}
        if err=os.WriteFile(p,append(b,'\n'),0600);err!=nil{t.Fatal(err)}
    }
    t.Logf("AV_STRESS_SCIENCE_HELD oracle=%s corpus=%s uncalibrated_pass=%d/%d p95ns=%d",
        s.ValidatorSHA256,s.CorpusSHA256,s.UncalibratedCasesWithPass,s.UncalibratedCount,s.RuntimeP95NS)
}
