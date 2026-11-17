package main
// R071 source-original blind polarity interview. The prompt contains test inputs
// and semantic rules but NOT oracle labels or generated Go code.
import(
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
 "strings"
 "time"
)
type Case struct{ ID,Input,Truth string }
type Answer struct{ ID,Decision string }
type Packet struct{ Schema,Suite string; Cases []Answer }
type Request struct{Model,Prompt string;Stream bool;Format string;Options map[string]any}
type Reply struct{Response,Error string}
type Comparison struct{ID,Truth,Decision string;Correct bool}
type Receipt struct{
 Schema,SourceSHA,Suite,Language,Mode,Model,CandidateSHA,Status,Reason,Scope string
 Score,Total int
 Checks []Comparison
}
func cases(suite string)([]Case,error){
 switch suite{
 case "path":return []Case{
  {"c01","cleanPath(\"/private/root\")","NO"},
  {"c02","cleanPath(\"src/native/**\")","YES"},
  {"c03","cleanPath(\"../escape\")","NO"},
  {"c04","overlap(\"src/a/**\",\"src/ab/**\")","NO"},
  {"c05","overlap(\"src/a/**\",\"src/a/b/**\")","YES"},
  {"c06","overlap(\"src/A/**\",\"src/a/**\")","NO"},
 },nil
 case "json":return []Case{
  {"c01","{\"authority\":{\"x\":1,\"x\":2}}","NO"},
  {"c02","{\"scope\":\"ok\"}","YES"},
  {"c03","{\"unknown_field\":1}","NO"},
  {"c04","{} {}","NO"},
  {"c05","{\"scope\":\"ok\",\"scope\":\"later\"}","NO"},
  {"c06","{\"authority\":{\"x\":\"a\"}}","YES"},
 },nil
 default:return nil,errors.New("SUITE_UNSUPPORTED")
 }
}
func instruction(lang string)string{
 switch lang{
 case "en":return "Predict for each case whether it is accepted according to the specification. Output YES if accepted and NO otherwise."
 case "de":return "Beurteile für jeden Fall, ob er gemäß der Spezifikation akzeptiert wird. Gib YES bei Annahme und NO bei Ablehnung aus."
 case "th":return "พิจารณาว่าแต่ละกรณีเป็นไปตามข้อกำหนดหรือไม่ ตอบ YES ถ้ายอมรับ และ NO ถ้าปฏิเสธ"
 default:return ""
 }
}
func spec(suite string)string{
 if suite=="path"{
  return "Functions: cleanPath(s) accepts normalized relative paths including terminal /**; rejects empty, absolute (/), backslash, colon, dot, parent traversal, and empty path components. overlap(a,b) strips terminal /** and returns true if the two paths are identical or one is a slash-delimited parent of the other; it is case-sensitive. For cleanPath YES means nil error; for overlap YES means true."
 }
 return "Function decodeLocalBounded: accepts a single JSON object mapping to Batch. Reject duplicate object keys at any nesting depth, a second JSON document, unknown top-level keys, and non-string authority map values. Allowed top-level keys: schema, authority, scope, max_concurrent, min_eligible, admission, packets, rep_receipt_required, stop_rule, reconciliation. An empty object is legal. YES means accepted, NO rejected."
}
func prompt(suite,lang string)string{
 cs,_:=cases(suite)
 var b strings.Builder
 b.WriteString(instruction(lang)+"\n"+spec(suite)+"\nEvaluate these inputs:\n")
 for _,c:=range cs{b.WriteString(c.ID+": "+c.Input+"\n")}
 b.WriteString("Return one JSON object containing exactly the fields Schema, Suite and Cases. Schema must be scp.r071.blind.v1; Suite must be "+suite+". Cases must be an array with six objects, ID c01 through c06 and Decision YES or NO. The literal strings YES and NO describe the allowed answer vocabulary, NOT the correct answers. Do not output Go source or prose.")
 return b.String()
}
func scan(d *json.Decoder,depth int)error{
 if depth>16{return errors.New("DEPTH")}
 tok,err:=d.Token();if err!=nil{return err}
 x,ok:=tok.(json.Delim);if !ok{return nil}
 switch x{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   k,err:=d.Token();if err!=nil{return err}
   name,ok:=k.(string);if !ok{return errors.New("KEY_TYPE")}
   if seen[name]{return errors.New("DUPLICATE_KEY")}
   seen[name]=true
   if err:=scan(d,depth+1);err!=nil{return err}
  }
  z,err:=d.Token();if err!=nil{return err};if z!=json.Delim('}'){return errors.New("OBJECT_CLOSE")}
 case '[':
  for d.More(){if err:=scan(d,depth+1);err!=nil{return err}}
  z,err:=d.Token();if err!=nil{return err};if z!=json.Delim(']'){return errors.New("ARRAY_CLOSE")}
 default:return errors.New("DELIMITER")
 }
 return nil
}
func parse(raw []byte,suite string)(Packet,error){
 if len(raw)<40||len(raw)>4096{return Packet{},errors.New("SIZE_BOUND")}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if err:=scan(d,0);err!=nil{return Packet{},err}
 if _,err:=d.Token();err!=io.EOF{return Packet{},errors.New("TRAILING")}
 x:=json.NewDecoder(bytes.NewReader(raw));x.DisallowUnknownFields()
 var p Packet
 if err:=x.Decode(&p);err!=nil{return Packet{},err}
 cs,err:=cases(suite);if err!=nil{return Packet{},err}
 if p.Schema!="scp.r071.blind.v1"||p.Suite!=suite||len(p.Cases)!=len(cs){return Packet{},errors.New("SCHEMA_SUITE_COVERAGE")}
 known:=map[string]bool{};for _,c:=range cs{known[c.ID]=true}
 seen:=map[string]bool{}
 for _,c:=range p.Cases{
  if !known[c.ID]||seen[c.ID]||(c.Decision!="YES"&&c.Decision!="NO"){return Packet{},errors.New("BAD_ID_LABEL_OR_DUPLICATE")}
  seen[c.ID]=true
 }
 return p,nil
}
func fixed(suite string)([]byte,error){
 cs,err:=cases(suite);if err!=nil{return nil,err}
 p:=Packet{Schema:"scp.r071.blind.v1",Suite:suite}
 for _,c:=range cs{p.Cases=append(p.Cases,Answer{c.ID,c.Truth})}
 return json.Marshal(p)
}
func infer(ctx context.Context,suite,lang,model string)([]byte,error){
 reqRaw,err:=json.Marshal(Request{Model:model,Prompt:prompt(suite,lang),Stream:false,Format:"json",Options:map[string]any{"temperature":0,"seed":29,"num_ctx":2048,"num_predict":400}})
 if err!=nil{return nil,err}
 req,err:=http.NewRequestWithContext(ctx,"POST","http://127.0.0.1:11434/api/generate",bytes.NewReader(reqRaw))
 if err!=nil{return nil,err};req.Header.Set("Content-Type","application/json")
 resp,err:=(&http.Client{Timeout:175*time.Second}).Do(req);if err!=nil{return nil,err};defer resp.Body.Close()
 b,err:=io.ReadAll(io.LimitReader(resp.Body,8192));if err!=nil{return nil,err}
 if resp.StatusCode!=200{return nil,fmt.Errorf("MODEL_HTTP_%d",resp.StatusCode)}
 var answer Reply
 if err:=json.Unmarshal(b,&answer);err!=nil{return nil,err}
 if answer.Error!=""{return nil,errors.New("MODEL_ENGINE_ERROR")}
 return []byte(strings.TrimSpace(answer.Response)),nil
}
func evaluate(suite string,p Packet)([]Comparison,int,error){
 cs,err:=cases(suite);if err!=nil{return nil,0,err}
 predictions:=map[string]string{}
 for _,c:=range p.Cases{predictions[c.ID]=c.Decision}
 var out []Comparison;score:=0
 for _,c:=range cs{
  actual:=predictions[c.ID];correct:=actual==c.Truth
  if correct{score++}
  out=append(out,Comparison{c.ID,c.Truth,actual,correct})
 }
 return out,score,nil
}
func main(){
 suite:=flag.String("suite","path","path/json")
 lang:=flag.String("lang","en","en/de/th")
 mode:=flag.String("mode","fixed","fixed/model")
 model:=flag.String("model","","loopback Ollama")
 rawOut:=flag.String("raw","","raw response path")
 flag.Parse()
 r:=Receipt{Schema:"scp.r071.blind-interview-receipt.v1",SourceSHA:os.Getenv("GITHUB_SHA"),
  Suite:*suite,Language:*lang,Mode:*mode,Model:*model,
  Status:"UNKNOWN",Scope:"SYNTHETIC_SMALL_SPECS_BLIND_POLARITY_ONLY"}
 finish:=func(exit int){b,_:=json.Marshal(r);fmt.Println(string(b));if exit!=0{os.Exit(exit)}}
 if *rawOut==""||instruction(*lang)==""{r.Reason="BAD_INPUT";finish(12)}
 var b []byte;var err error
 if *mode=="fixed"{b,err=fixed(*suite)}else if *mode=="model"&&*model!=""{
  ctx,cancel:=context.WithTimeout(context.Background(),180*time.Second);defer cancel()
  b,err=infer(ctx,*suite,*lang,*model)
 }else{err=errors.New("MODE_UNSUPPORTED")}
 if err!=nil{r.Reason=err.Error();finish(12)}
 hash:=sha256.Sum256(b);r.CandidateSHA=hex.EncodeToString(hash[:])
 if err:=os.WriteFile(*rawOut,b,0600);err!=nil{r.Reason="WRITE_FAILED";finish(12)}
 p,err:=parse(b,*suite);if err!=nil{r.Reason=err.Error();finish(12)}
 r.Checks,r.Score,err=evaluate(*suite,p);if err!=nil{r.Reason=err.Error();finish(12)}
 r.Total=len(r.Checks)
 if r.Score==r.Total{r.Status="PASS_EXACT_SYNTHETIC_ONLY";finish(0);return}
 r.Status="FAIL_BLIND_CONTROLS";r.Reason="POLARITY_MISMATCH";finish(12)
}
