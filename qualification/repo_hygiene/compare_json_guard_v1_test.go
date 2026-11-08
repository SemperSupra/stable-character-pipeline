package main

import (
    "strings"
    "testing"
)

func TestCompareJSONExactRealisticPositive(t *testing.T) {
    input := `{"status":"diverged","ahead_by":7,"behind_by":2,"total_commits":7,"merge_base_commit":{"sha":"`+strings.Repeat("a",40)+`"},"files":[{"filename":"a.go"},{"filename":"b.go"}],"unknown_future_field":{"nested":[1,true,null]}}`
    got, err := decodeCompareJSON(strings.NewReader(input))
    if err != nil { t.Fatal(err) }
    if got.Status!="diverged"||got.AheadBy!=7||got.BehindBy!=2||len(got.Files)!=2 { t.Fatalf("incorrect decoded body: %#v",got) }
}
func TestCompareJSONFirstREDsMustFailClosed(t *testing.T) {
    ok := `{"status":"ahead","ahead_by":1,"merge_base_commit":{"sha":"`+strings.Repeat("a",40)+`"},"files":[{"filename":"file.go"}]}`
    tests := []struct{name,src string}{
        {"duplicate top status",`{"status":"ahead","status":"diverged"}`},
        {"duplicate nested sha",`{"status":"ahead","merge_base_commit":{"sha":"a","sha":"b"}}`},
        {"duplicate unknown nested payload",`{"meta":[{"safe":true,"safe":false}]}`},
        {"forged trailing object",ok+`{"status":"diverged"}`},
        {"forged trailing scalar",ok+` true`},
        {"malformed suffix",ok+` <> `},
        {"truncated object",`{"status":"ahead"`},
        {"non-object JSON root",`[]`},
        {"empty body",""},
        {"oversized whitespace",strings.Repeat(" ",compareJSONMaxBytes+1)},
    }
    for _,tt:=range tests {
        t.Run(tt.name,func(t *testing.T) {
            if _,err:=decodeCompareJSON(strings.NewReader(tt.src));err==nil {
                t.Fatalf("forged or invalid upstream JSON accepted: %s",tt.name)
            }
        })
    }
}
func TestCompareJSONDepthLimit(t *testing.T) {
    deep := strings.Repeat("[",compareJSONMaxDepth+4)+"0"+strings.Repeat("]",compareJSONMaxDepth+4)
    if _,err:=decodeCompareJSON(strings.NewReader(`{"nested":`+deep+`}`));err==nil {
        t.Fatal("unbounded nesting accepted")
    }
}
