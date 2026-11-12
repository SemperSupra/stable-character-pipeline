package main

import (
    "encoding/json"
    "os"
    "path/filepath"
    "testing"
)

func TestUnlabelledCorpusDoesNotInventOracle(t *testing.T) {
    dir := t.TempDir()
    raw, err := os.ReadFile("../../fixtures/clean.json")
    if err != nil { t.Fatal(err) }
    if err := os.WriteFile(filepath.Join(dir, "clean.json"), raw, 0600); err != nil { t.Fatal(err) }
    manifest := []byte(`{"schema":"scp.video-bakeoff-cases.v1","cases":[{"id":"unlabelled-motion","kind":"motion","path":"clean.json"}]}`)
    path := filepath.Join(dir, "manifest.json")
    if err := os.WriteFile(path, manifest, 0600); err != nil { t.Fatal(err) }
    dest := filepath.Join(dir, "receipt.json")
    if err := run(path, dest); err != nil { t.Fatalf("diagnostic run should not fail: %v",err) }
    data, err := os.ReadFile(dest)
    if err != nil { t.Fatal(err) }
    var result Receipt
    if err := json.Unmarshal(data, &result); err != nil { t.Fatal(err) }
    if result.Total != 1 || result.Matched != 0 || result.Discrepancies != 0 { t.Fatalf("bad no-oracle accounting: %+v",result) }
    if len(result.Results) != 1 || result.Results[0].Verdict != "PASS" || result.Results[0].MatchesOracle || result.Results[0].Expected != "" { t.Fatalf("invented oracle: %+v",result.Results) }
}

func TestInvalidExplicitOracleFails(t *testing.T) {
    dir := t.TempDir()
    path := filepath.Join(dir,"manifest.json")
    raw := []byte(`{"schema":"scp.video-bakeoff-cases.v1","cases":[{"id":"bad","kind":"motion","path":"x","expect":"MAYBE"}]}`)
    if err := os.WriteFile(path,raw,0600); err != nil { t.Fatal(err) }
    if err := run(path,""); err == nil { t.Fatal("invalid oracle accepted") }
}
