package main

import (
    "bytes"
    "strings"
    "testing"
)

func TestNormalizeRightsFailClosed(t *testing.T){
    got,err:=normalize(Probe{
        Provider:"polyhaven",Lane:"A",Endpoint:"https://api.polyhaven.com/files/sample",
        RightsGate:"not accepted",Status:200,Result:"API_METADATA_OK",
        SampleSHA256:strings.Repeat("a",64),
    })
    if err!=nil {t.Fatal(err)}
    if got.Schema!=schema || got.DiscoveryState!="ANONYMOUS_API_METADATA" || got.RightsState!="UNVERIFIED" || got.AssetAcquisitionState!="NOT_ADMITTED" || got.AssetBytesIngested!=0 {
        t.Fatalf("silent promotion: %+v",got)
    }
}
func TestNormalizeRejectForgedStatus(t *testing.T){
    _,err:=normalize(Probe{
        Provider:"x",Lane:"A",Endpoint:"https://example.org/metadata",
        RightsGate:"unknown",Status:403,Result:"API_METADATA_OK",
        SampleSHA256:strings.Repeat("a",64),
    })
    if err==nil{t.Fatal("403 must not become API qualified")}
}
func TestNormalizeRejectNonHTTPS(t *testing.T){
    _,err:=normalize(Probe{
        Provider:"x",Lane:"C",Endpoint:"http://example.org",
        RightsGate:"unknown",Status:200,Result:"HTML_ONLY_REVIEW",
    })
    if err==nil{t.Fatal("HTTP not permitted")}
}
func TestNormalizeHoldsPreserved(t *testing.T){
    got,err:=normalize(Probe{Provider:"open3dlab-project",Lane:"C",Endpoint:"https://open3dlab.com/project/id",RightsGate:"unknown",Status:200,Result:"CHALLENGE_HOLD"})
    if err!=nil{t.Fatal(err)}
    if got.DiscoveryState!="HOLD"||got.ProbeResult!="CHALLENGE_HOLD"{t.Fatalf("challenge incorrectly promoted: %+v",got)}
}
func TestNormalizeReadRejectsDuplicate(t *testing.T){
    line := "{\"provider\":\"x\",\"lane\":\"A\",\"endpoint\":\"https://example.org\",\"rights_gate\":\"unknown\",\"result\":\"TRANSPORT_HOLD\"}\n"
    _,err:=readProbes(strings.NewReader(line+line))
    if err==nil{t.Fatal("duplicate receipt must fail")}
}
func TestNormalizeMarkdownHumanAndJSON(t *testing.T){
    caps:=[]Capability{{Schema:schema,ProviderID:"x",Lane:"B",DiscoveryState:"HOLD",ProbeResult:"ACCESS_HOLD",RightsState:"UNVERIFIED",AssetAcquisitionState:"NOT_ADMITTED"}}
    for _,kind:=range []string{"md","jsonl"}{
        var b bytes.Buffer
        if err:=writeCaps(&b,caps,kind);err!=nil{t.Fatal(err)}
        if !strings.Contains(b.String(),"NOT_ADMITTED"){t.Fatalf("missing rights guard: %s",b.String())}
    }
}
