// R069: models propose typed test intents, not executable Go. Original synthetic only.
// All executable Go is emitted from hardcoded templates after strict source admission.
package main

import (
 "bytes"
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net/http"
 "os"
 "path/filepath"
 "sort"
 "strings"
 "time"
)

type TestCase struct { ID string; Expect string }
type Intent struct { Schema string; Suite string; Cases []TestCase }
type GenerateRequest struct { Model string; Prompt string; Stream bool; Format string; Options map[string]any }
type GenerateReply struct { Response string; Error string }
type Receipt struct {
 Schema string
 Suite string
 Mode string
 Model string
 SourceSHA string
 IntentSHA string
 Cases int
 Status string
 Reason string
 Scope string
}
const schema = "scp.r069.test-intent.v1"
var allowed=map[string]map[string]string{
 "path-boundaries":{"absolute":"reject","parent":"reject","subtree":"true","sibling":"false"},
 "strict-json":{"nested-duplicate":"reject","trailing-document":"reject","empty-valid":"accept","unknown-field":"reject"},
}
var pivotal=map[string]string{"path-boundaries":"subtree","strict-json":"nested-duplicate"}
func scanValue(d *json.Decoder,depth int) error {
 if depth>16{return errors.New("NESTING_LIMIT")}
 tok,err:=d.Token();if err!=nil{return err}
 delim,ok:=tok.(json.Delim);if !ok{return nil}
 switch delim{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   tok,err:=d.Token();if err!=nil{return err}
   key,ok:=tok.(string);if !ok{return errors.New("OBJECT_KEY_TYPE")}
   if seen[key]{return errors.New("DUPLICATE_JSON_KEY")}
   seen[key]=true
   if err:=scanValue(d,depth+1);err!=nil{return err}
  }
  close,err:=d.Token();if err!=nil{return err}
  if close!=json.Delim('}') {return errors.New("UNCLOSED_OBJECT")}
 case '[':
  for d.More(){if err:=scanValue(d,depth+1);err!=nil{return err}}
  close,err:=d.Token();if err!=nil{return err}
  if close!=json.Delim(']'){return errors.New("UNCLOSED_ARRAY")}
 default:return errors.New("INVALID_DELIMITER")
 }
 return nil
}
func parse(raw []byte,suite string)(Intent,error){
 if len(raw)<20||len(raw)>4096{return Intent{},errors.New("INTENT_BYTES_BOUND")}
 guard:=json.NewDecoder(bytes.NewReader(raw))
 if err:=scanValue(guard,0);err!=nil{return Intent{},err}
 if _,err:=guard.Token();err!=io.EOF{return Intent{},errors.New("TRAILING_DOCUMENT")}
 var x Intent
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&x);err!=nil{return Intent{},err}
 if _,err:=d.Token();err!=io.EOF{return Intent{},errors.New("EXTRA_DATA")}
 if x.Schema!=schema||x.Suite!=suite{return Intent{},errors.New("SCHEMA_OR_SUITE_MISMATCH")}
 options,ok:=allowed[suite];if !ok{return Intent{},errors.New("UNSUPPORTED_SUITE")}
 if len(x.Cases)<3||len(x.Cases)>len(options){return Intent{},errors.New("COVERAGE_BOUND")}
 seen:=map[string]bool{}
 for _,c:=range x.Cases{
  expected,ok:=options[c.ID];if !ok{return Intent{},errors.New("UNKNOWN_CASE")}
  if seen[c.ID]{return Intent{},errors.New("DUPLICATE_CASE")}
  if c.Expect!=expected{return Intent{},errors.New("INDEPENDENT_ORACLE_MISMATCH")}
  seen[c.ID]=true
 }
 if !seen[pivotal[suite]]{return Intent{},errors.New("MISSING_MUTANT_SENSITIVE_CASE")}
 return x,nil
}
func fixture(suite string)([]byte,error){
 table,ok:=allowed[suite];if !ok{return nil,errors.New("UNSUPPORTED_SUITE")}
 ids:=make([]string,0,len(table));for k:=range table{ids=append(ids,k)};sort.Strings(ids)
 x:=Intent{Schema:schema,Suite:suite}
 for _,id:=range ids{x.Cases=append(x.Cases,TestCase{ID:id,Expect:table[id]})}
 return json.Marshal(x)
}
func prompt(suite string)string{
 b,_:=fixture(suite)
 return "The task is to select bounded test intentions, NOT to write code. Return ONLY this EXACT valid JSON object with all cases and exactly these field names and values, no explanation, no markdown or package/import definitions: "+string(b)
}
func askModel(ctx context.Context,model,suite string)([]byte,error){
 reqRaw,err:=json.Marshal(GenerateRequest{Model:model,Prompt:prompt(suite),Stream:false,Format:"json",
  Options:map[string]any{"temperature":0,"num_ctx":1536,"num_predict":320,"seed":17}})
 if err!=nil{return nil,err}
 req,err:=http.NewRequestWithContext(ctx,http.MethodPost,"http://127.0.0.1:11434/api/generate",bytes.NewReader(reqRaw))
 if err!=nil{return nil,err}
 req.Header.Set("Content-Type","application/json")
 response,err:=(&http.Client{Timeout:160*time.Second}).Do(req)
 if err!=nil{return nil,err};defer response.Body.Close()
 raw,err:=io.ReadAll(io.LimitReader(response.Body,8192));if err!=nil{return nil,err}
 if response.StatusCode!=200{return nil,fmt.Errorf("MODEL_HTTP_%d",response.StatusCode)}
 var reply GenerateReply
 if err:=json.Unmarshal(raw,&reply);err!=nil{return nil,err}
 if reply.Error!=""{return nil,errors.New("MODEL_ENGINE_ERROR")}
 return []byte(strings.TrimSpace(reply.Response)),nil
}
func bodyFor(id string)string{
 switch id{
 case "absolute":return "if err:=cleanPath(\"/absolute\");err==nil{t.Fatal(\"accepted absolute path\")}"
 case "parent":return "if err:=cleanPath(\"../escape\");err==nil{t.Fatal(\"accepted parent escape\")}"
 case "subtree":return "if !overlap(\"src/a/**\",\"src/a/b/**\"){t.Fatal(\"lost subtree overlap\")}"
 case "sibling":return "if overlap(\"src/a/**\",\"src/ab/**\"){t.Fatal(\"invented sibling overlap\")}"
 case "nested-duplicate":return "raw:=\"{\\\"authority\\\":{\\\"x\\\":1,\\\"x\\\":2}}\";p:=filepath.Join(t.TempDir(),\"sample.json\");if err:=os.WriteFile(p,[]byte(raw),0600);err!=nil{t.Fatal(err)};var b Batch;if err:=decodeLocalBounded(p,&b);err==nil{t.Fatal(\"nested duplicate accepted\")}"
 case "trailing-document":return "p:=filepath.Join(t.TempDir(),\"sample.json\");if err:=os.WriteFile(p,[]byte(\"{} {}\"),0600);err!=nil{t.Fatal(err)};var b Batch;if err:=decodeLocalBounded(p,&b);err==nil{t.Fatal(\"trailing document accepted\")}"
 case "empty-valid":return "p:=filepath.Join(t.TempDir(),\"sample.json\");if err:=os.WriteFile(p,[]byte(\"{}\"),0600);err!=nil{t.Fatal(err)};var b Batch;if err:=decodeLocalBounded(p,&b);err!=nil{t.Fatal(\"valid JSON rejected:\",err)}"
 case "unknown-field":return "p:=filepath.Join(t.TempDir(),\"sample.json\");if err:=os.WriteFile(p,[]byte(\"{\\\"unknown_not_in_batch\\\":1}\"),0600);err!=nil{t.Fatal(err)};var b Batch;if err:=decodeLocalBounded(p,&b);err==nil{t.Fatal(\"unknown field accepted\")}"
 }
 return ""
}
func emit(x Intent)string{
 var s strings.Builder
 s.WriteString("// R069 source-only: all Go statements originate from static compiler templates.\n")
 s.WriteString("package main\n")
 if x.Suite=="strict-json"{s.WriteString("import (\"os\";\"path/filepath\";\"testing\")\n")}else{s.WriteString("import \"testing\"\n")}
 s.WriteString("func TestR069IntentQualified(t *testing.T){\n")
 for _,c:=range x.Cases{s.WriteString(fmt.Sprintf("t.Run(%q,func(t *testing.T){ %s })\n",c.ID,bodyFor(c.ID)))}
 s.WriteString("}\n")
 return s.String()
}
func main(){
 suite:=flag.String("suite","","strict-json or path-boundaries")
 mode:=flag.String("mode","fixture","fixture or model")
 model:=flag.String("model","","local-only model candidate")
 output:=flag.String("out","","single owned test file")
 rawOutput:=flag.String("raw","","bounded JSON evidence")
 flag.Parse()
 r:=Receipt{Schema:"scp.r069.intent-receipt.v1",Suite:*suite,Mode:*mode,Model:*model,SourceSHA:os.Getenv("GITHUB_SHA"),
  Status:"UNKNOWN",Scope:"SOURCE_ONLY_TYPED_NONCODE_INTENT_NOT_PRODUCT_ADMITTED"}
 fail:=func(err error){r.Reason=err.Error();line,_:=json.Marshal(r);fmt.Println(string(line));os.Exit(12)}
 if *output==""||*rawOutput==""{fail(errors.New("MISSING_OUTPUT"))}
 var raw []byte;var err error
 if *mode=="fixture"{raw,err=fixture(*suite)}else if *mode=="model"{
  if *model==""{fail(errors.New("MISSING_MODEL"))}
  ctx,cancel:=context.WithTimeout(context.Background(),165*time.Second);defer cancel()
  raw,err=askModel(ctx,*model,*suite)
 }else{fail(errors.New("UNKNOWN_MODE"))}
 if err!=nil{fail(err)}
 h:=sha256.Sum256(raw);r.IntentSHA=hex.EncodeToString(h[:])
 if err:=os.MkdirAll(filepath.Dir(*rawOutput),0700);err!=nil{fail(err)}
 if err:=os.WriteFile(*rawOutput,raw,0600);err!=nil{fail(err)}
 intent,err:=parse(raw,*suite);if err!=nil{fail(err)}
 r.Cases=len(intent.Cases)
 if _,err:=os.Stat(*output);err==nil{fail(errors.New("REFUSE_OVERWRITE"))}else if !errors.Is(err,os.ErrNotExist){fail(err)}
 if err:=os.WriteFile(*output,[]byte(emit(intent)),0600);err!=nil{fail(err)}
 r.Status="INTENT_ADMITTED_EMITTED";b,_:=json.Marshal(r);fmt.Println(string(b))
}
