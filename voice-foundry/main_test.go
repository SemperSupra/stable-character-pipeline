package main

import (
  "context"
  "os"
  "path/filepath"
  "strings"
  "testing"
)

func TestValidate(t *testing.T){
  good:=Config{Engine:"auto",Out:"test.wav",Voice:"en-us",Text:"Hello",Rate:165,Pitch:55}
  if e:=good.Validate();e!=nil{t.Fatal(e)}
  cases:=[]Config{
    {Engine:"auto",Out:"test.wav",Voice:"en-us",Text:"",Rate:165,Pitch:55},
    {Engine:"auto",Out:"test.wav",Voice:"-f",Text:"Hi",Rate:165,Pitch:55},
    {Engine:"auto",Out:"test.wav",Voice:"en-us",Text:"Hi",Rate:1,Pitch:55},
    {Engine:"auto",Out:"test.wav",Voice:"en-us",Text:"Hi",Rate:165,Pitch:100},
    {Engine:"invalid",Out:"test.wav",Voice:"en-us",Text:"Hi",Rate:165,Pitch:55},
  }
  for i,c:=range cases {if c.Validate()==nil{t.Fatalf("negative case %d accepted",i)}}
}
func TestSyntheticCandidateIfEngineAvailable(t *testing.T){
  if _,e:=findEngine("auto");e!=nil{t.Skip("speech engine not installed")}
  p:=filepath.Join(t.TempDir(),"candidate.wav")
  c:=Config{Engine:"auto",Out:p,Voice:"en-us",Text:"This is a disposable synthetic test.",Rate:165,Pitch:55}
  result,e:=makeVoice(context.Background(),c);if e!=nil{t.Fatal(e)}
  if result["classification"]!="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"{t.Fatal("classification mismatch")}
  if _,e:=os.Stat(p);e!=nil{t.Fatal(e)}
  if _,e:=makeVoice(context.Background(),c);e==nil || !strings.Contains(e.Error(),"overwrite"){t.Fatalf("must refuse overwrite, got %v",e)}
}
