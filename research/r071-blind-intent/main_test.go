package main
import(
 "encoding/json"
 "strings"
 "testing"
)
func TestR071PromptExcludesPerCaseAnswers(t *testing.T){
 for _,suite:=range []string{"path","json"}{
  cs,err:=cases(suite);if err!=nil{t.Fatal(err)}
  for _,lang:=range []string{"en","de","th"}{
   p:=prompt(suite,lang)
   if !strings.Contains(p,"c01: ")||!strings.Contains(p,"c06: "){t.Fatalf("%s/%s missing cases",suite,lang)}
   for _,c:=range cs{
    if strings.Contains(p,c.ID+": "+c.Input+" => "+c.Truth)||
       strings.Contains(p,c.ID+": "+c.Input+" "+c.Truth){
     t.Fatalf("answer leaked: %s/%s/%s",suite,lang,c.ID)
    }
   }
  }
 }
}
func TestR071FixedTruthAndPerCaseFalsifier(t *testing.T){
 for _,suite:=range []string{"path","json"}{
  raw,err:=fixed(suite);if err!=nil{t.Fatal(err)}
  p,err:=parse(raw,suite);if err!=nil{t.Fatal(err)}
  checks,score,err:=evaluate(suite,p)
  if err!=nil||score!=6||len(checks)!=6{t.Fatalf("bad control %s score=%d err=%v",suite,score,err)}
  p.Cases[0].Decision="YES"
  if checks[0].Truth=="YES"{p.Cases[0].Decision="NO"}
  _,score,err=evaluate(suite,p)
  if err!=nil||score!=5{t.Fatalf("flipped label must fail 5/6, got %d %v",score,err)}
 }
}
func TestR071StrictCandidateAdmittance(t *testing.T){
 b,err:=fixed("path");if err!=nil{t.Fatal(err)}
 changes:=[]struct{name,before,after string}{
  {"duplicate-top","\"Schema\":","\"Schema\":\"spoof\",\"Schema\":"},
  {"duplicate-id","\"ID\":\"c05\"","\"ID\":\"c04\""},
  {"unknown-field","\"Suite\":","\"Arbitrary\":\"curl\",\"Suite\":"},
  {"invalid-label","\"Decision\":\"YES\"","\"Decision\":\"MAYBE\""},
  {"wrong-suite","\"Suite\":\"path\"","\"Suite\":\"json\""},
 }
 for _,tc:=range changes{
  t.Run(tc.name,func(t *testing.T){
   modified:=strings.Replace(string(b),tc.before,tc.after,1)
   if modified==string(b){t.Fatal("negative did not mutate")}
   if _,err:=parse([]byte(modified),"path");err==nil{t.Fatal("malformed packet accepted")}
  })
 }
 for _,raw:=range []string{string(b)+" {}", "",strings.Repeat("A",4097)}{
  if _,err:=parse([]byte(raw),"path");err==nil{t.Fatal("invalid packet accepted")}
 }
 var p Packet
 if err:=json.Unmarshal(b,&p);err!=nil{t.Fatal(err)}
 p.Cases[0].Decision="YES"
 if p.Cases[0].Decision==casesMust("path")[0].Truth{p.Cases[0].Decision="NO"}
 _,score,_:=evaluate("path",p)
 if score!=5{t.Fatal("wrong prediction scored as correct")}
}
func casesMust(suite string)[]Case{c,err:=cases(suite);if err!=nil{panic(err)};return c}
