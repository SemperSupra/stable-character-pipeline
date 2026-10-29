package main

import (
    "net/url"
    "strings"
    "testing"
)

func TestClassifyNegativeControls(t *testing.T) {
    cases := []struct{
        name string
        status int
        kind, mime, body string
        truncated bool
        want string
    }{
        {"valid JSON",200,"json","application/json","{}",false,"API_METADATA_OK"},
        {"JSON is HTML",200,"json","text/html","<html>OK</html>",false,"CONTENT_MISMATCH_HOLD"},
        {"fake JSON",200,"json","application/json","<html></html>",false,"CONTENT_MISMATCH_HOLD"},
        {"Anubis challenge",200,"html","text/html","<html>Anubis proof-of-work</html>",false,"CHALLENGE_HOLD"},
        {"403",403,"json","application/json","{}",false,"ACCESS_HOLD"},
        {"401",401,"json","application/json","{}",false,"ACCESS_HOLD"},
        {"rate limited",429,"json","application/json","{}",false,"RATE_LIMIT_HOLD"},
        {"redirect",302,"json","application/json","{}",false,"REDIRECT_HOLD"},
        {"truncated",200,"json","application/json","{}",true,"TRUNCATED_REVIEW"},
        {"empty JSON",200,"json","application/json","",false,"CONTENT_MISMATCH_HOLD"},
        {"RSS",200,"xml","application/rss+xml","<?xml version=\"1.0\"?><rss version=\"2.0\"></rss>",false,"FEED_METADATA_OK"},
        {"RSS mismatch",200,"xml","text/html","<rss/>",false,"CONTENT_MISMATCH_HOLD"},
        {"HTML only",200,"html","text/html","<html></html>",false,"HTML_ONLY_REVIEW"},
        {"text",200,"text","text/plain","# test",false,"TEXT_METADATA_OK"},
        {"offline",0,"json","application/json","{}",false,"TRANSPORT_HOLD"},
        {"server",500,"json","application/json","{}",false,"SERVER_HOLD"},
    }
    for _, tc := range cases {
        t.Run(tc.name,func(t *testing.T){
            got:=classify(tc.status,tc.kind,tc.mime,[]byte(tc.body),tc.truncated)
            if got!=tc.want {t.Fatalf("got %s, want %s",got,tc.want)}
        })
    }
}
func TestStaticTargetSafety(t *testing.T) {
    seen:=map[string]bool{}
    counts:=map[string]int{}
    for _, target:=range targets {
        if seen[target.Provider] {t.Fatalf("duplicate %s",target.Provider)}
        seen[target.Provider]=true
        u,err:=url.Parse(target.URL)
        if err!=nil||u.Scheme!="https"||u.Host==""||u.User!=nil {t.Fatalf("invalid URL for %s",target.Provider)}
        if strings.Contains(strings.ToLower(target.URL),"token=")||strings.Contains(strings.ToLower(target.URL),"key=") {t.Fatalf("possible secret %s",target.Provider)}
        if target.Rights=="" {t.Fatalf("missing rights gate %s",target.Provider)}
        counts[target.Lane]++
    }
    if counts["A"]!=4||counts["B"]!=5||counts["C"]!=6 {t.Fatalf("unexpected lane distribution: %+v",counts)}
}
