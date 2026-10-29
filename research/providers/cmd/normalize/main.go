package main

import (
    "bufio"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "io"
    "net/url"
    "os"
    "strings"
)

const schema = "scp.provider_capability.v1"

type Probe struct {
    Provider string `json:"provider"`
    Lane string `json:"lane"`
    Endpoint string `json:"endpoint"`
    RightsGate string `json:"rights_gate"`
    Status int `json:"http_status"`
    ContentType string `json:"content_type"`
    SampleSHA256 string `json:"sample_sha256"`
    Result string `json:"result"`
    TransportKind string `json:"transport_kind"`
}
type Capability struct {
    Schema string `json:"schema"`
    ProviderID string `json:"provider_id"`
    Lane string `json:"lane"`
    SourceURL string `json:"source_url"`
    Scope string `json:"scope"`
    AnonymousObservation string `json:"anonymous_observation"`
    DiscoveryState string `json:"discovery_state"`
    RightsState string `json:"rights_state"`
    AssetAcquisitionState string `json:"asset_acquisition_state"`
    AssetBytesIngested int `json:"asset_bytes_ingested"`
    RightsNote string `json:"rights_note"`
    ProbeResult string `json:"probe_result"`
    HTTPStatus int `json:"http_status"`
    TransportKind string `json:"transport_kind,omitempty"`
    SampleSHA256 string `json:"metadata_sample_sha256,omitempty"`
}
func normalize(p Probe) (Capability,error) {
    u,err:=url.Parse(p.Endpoint)
    if err!=nil || u.Scheme!="https" || u.Host=="" || u.User!=nil {return Capability{},errors.New("not an approved HTTPS endpoint")}
    if p.Provider=="" || (p.Lane!="A" && p.Lane!="B" && p.Lane!="C") || p.RightsGate=="" {return Capability{},errors.New("incomplete source provenance")}
    state:="HOLD"
    switch p.Result {
    case "API_METADATA_OK":
        if p.Status!=200 || len(p.SampleSHA256)!=64 {return Capability{},errors.New("invalid API receipt")}
        state="ANONYMOUS_API_METADATA"
    case "FEED_METADATA_OK":
        if p.Status!=200 || len(p.SampleSHA256)!=64 {return Capability{},errors.New("invalid feed receipt")}
        state="ANONYMOUS_FEED_METADATA"
    case "TEXT_METADATA_OK", "HTML_ONLY_REVIEW":
        if p.Status!=200 {return Capability{},errors.New("invalid document receipt")}
        state="DOCUMENTATION_ONLY"
    }
    return Capability{
        Schema:schema, ProviderID:p.Provider, Lane:p.Lane, SourceURL:p.Endpoint,
        Scope:"SOURCE_METADATA_ONLY", AnonymousObservation:"NO_CREDENTIALS_SENT",
        DiscoveryState:state, RightsState:"UNVERIFIED",
        AssetAcquisitionState:"NOT_ADMITTED", AssetBytesIngested:0,
        RightsNote:p.RightsGate, ProbeResult:p.Result, HTTPStatus:p.Status,
        TransportKind:p.TransportKind,SampleSHA256:p.SampleSHA256,
    },nil
}
func readProbes(rd io.Reader)([]Capability,error){
    scan:=bufio.NewScanner(rd)
    scan.Buffer(make([]byte,4096), 1024*1024)
    var caps []Capability
    seen:=map[string]bool{}
    for scan.Scan(){
        line:=strings.TrimSpace(scan.Text())
        if line=="" {continue}
        var p Probe
        if err:=json.Unmarshal([]byte(line),&p);err!=nil {return nil,err}
        if seen[p.Provider] {return nil,fmt.Errorf("duplicate provider %s",p.Provider)}
        seen[p.Provider]=true
        c,err:=normalize(p)
        if err!=nil {return nil,fmt.Errorf("%s: %w",p.Provider,err)}
        caps=append(caps,c)
    }
    if err:=scan.Err();err!=nil{return nil,err}
    if len(caps)==0 {return nil,errors.New("empty report")}
    return caps,nil
}
func writeCaps(w io.Writer,caps []Capability,format string) error {
    if format=="jsonl" {
        enc:=json.NewEncoder(w)
        for _,cap:=range caps{if err:=enc.Encode(cap);err!=nil{return err}}
        return nil
    }
    if format!="md" {return errors.New("format must be jsonl or md")}
    if _,err:=fmt.Fprintln(w,"# Source-provider qualification — research only\n\nCI passing means the harness ran; no asset downloads or license admissions.\n\n| Provider | Batch | Discovery | Original probe result | Asset acquisition |\n|---|---|---|---|---|");err!=nil{return err}
    for _,cap:=range caps{
        _,err:=fmt.Fprintf(w,"| %s | %s | %s | %s | %s |\n",cap.ProviderID,cap.Lane,cap.DiscoveryState,cap.ProbeResult,cap.AssetAcquisitionState)
        if err!=nil{return err}
    }
    _,err:=fmt.Fprintln(w,"\nEvery record has rights_state=UNVERIFIED and asset_bytes_ingested=0. Respect per-provider terms, source-custody and private character gates.")
    return err
}
func main(){
    input:=flag.String("input","","Path to the local JSONL probe receipt (never fetches network)")
    format:=flag.String("format","jsonl","jsonl or md")
    flag.Parse()
    if *input=="" {fmt.Fprintln(os.Stderr,"-input required");os.Exit(2)}
    file,err:=os.Open(*input)
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(1)}
    defer file.Close()
    caps,err:=readProbes(file)
    if err==nil{err=writeCaps(os.Stdout,caps,*format)}
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
