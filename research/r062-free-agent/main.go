// Command r062-agent is a disposable, single-task OpenAI-free coding workcell.
// Its only output is one bounded Go test candidate. The enclosing CI owns the
// independent oracle, evidence and acceptance boundary.
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
 "go/parser"
 "go/token"
 "io"
 "net/http"
 "os"
 "path/filepath"
 "strings"
 "time"
)

type generateRequest struct {
 Model string `json:"model"`
 Prompt string `json:"prompt"`
 Stream bool `json:"stream"`
 Format string `json:"format"`
 Options map[string]any `json:"options"`
}
type generateReply struct {
 Response string `json:"response"`
 Error string `json:"error"`
}
type candidate struct {
 GoSource string `json:"go_source"`
}

func task(lane string) (string,string,error) {
 const shared = "Return ONLY a JSON object with exactly one key go_source containing a complete Go test file (use JSON string escaping). No markdown, prose or shell commands. Package name must be main. Add tests ONLY, no production code. No network or external dependencies. Existing functions are compiled from adjacent Go source."
 switch lane {
 case "path-boundaries":
  return "r062_paths_test.go",shared + `
Use import "testing" only. Existing functions: cleanPath(s string) error; overlap(a,b string) bool; syntheticBatch() Batch; Validate(b Batch) (Receipt,error).
Create function TestR062PathBoundaries(t *testing.T). Check invalid cleanPath values "/absolute", "../escape", "x\\\\y" return errors. Check "src/new/**" is valid. Test overlap("src/a/**","src/a/b/**") is true and overlap("src/a/**","src/ab/**") is false. Use ordinary Go testing assertions.
`,nil
 case "strict-json":
  return "r062_json_test.go",shared + `
Use imports "os" and "testing" only. Existing function: decodeLocalBounded(file string, out interface{}) error. Existing type: Batch. Create function TestR062JSONAdmission(t *testing.T).
Create t.TempDir() paths using directory + "/fixture.json" and os.WriteFile. Use three table cases with contents: duplicate nested key {"authority":{"x":1,"x":2}} (reject), trailing document "{} {}" (reject), and valid empty object "{}" (accept). For each, write the file, call decodeLocalBounded(path,&Batch{}), and assert whether an error is expected. Make a deterministic Go test; no external data.
`,nil
 default:
  return "","",fmt.Errorf("unsupported lane %q",lane)
 }
}

func acquire(ctx context.Context, endpoint, model, prompt string) (string,error) {
 input,err:=json.Marshal(generateRequest{
  Model:model,Prompt:prompt,Stream:false,Format:"json",
  Options:map[string]any{"num_ctx":3072,"num_predict":750,"temperature":0},
 })
 if err!=nil{return "",err}
 req,err:=http.NewRequestWithContext(ctx,http.MethodPost,endpoint,bytes.NewReader(input))
 if err!=nil{return "",err}
 req.Header.Set("Content-Type","application/json")
 client:=&http.Client{Timeout:170*time.Second}
 resp,err:=client.Do(req)
 if err!=nil{return "",err}
 defer resp.Body.Close()
 raw,err:=io.ReadAll(io.LimitReader(resp.Body,16000))
 if err!=nil{return "",err}
 if resp.StatusCode!=200{return "",fmt.Errorf("inference HTTP %d: %.150s",resp.StatusCode,string(raw))}
 var reply generateReply
 if err:=json.Unmarshal(raw,&reply);err!=nil{return "",fmt.Errorf("invalid engine reply: %w",err)}
 if reply.Error!=""{return "",errors.New(reply.Error)}
 var c candidate
 dec:=json.NewDecoder(strings.NewReader(reply.Response))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(&c);err!=nil{return "",fmt.Errorf("model did not satisfy structured response contract: %w",err)}
 if err:=dec.Decode(&struct{}{});err!=io.EOF{return "",errors.New("extra structured response data")}
 return c.GoSource,nil
}

func validateGenerated(src string) error {
 if len(src)<80 || len(src)>8000{return errors.New("candidate outside bounded code-size envelope")}
 if !strings.HasPrefix(strings.TrimSpace(src),"package main"){return errors.New("candidate must declare package main")}
 fs:=token.NewFileSet()
 parsed,err:=parser.ParseFile(fs,"candidate_test.go",src,parser.AllErrors)
 if err!=nil{return fmt.Errorf("invalid Go syntax: %w",err)}
 if parsed.Name.Name!="main"{return errors.New("wrong Go package")}
 if !strings.Contains(src,"func TestR062"){return errors.New("missing owned executable test")}
 for _,imp:=range parsed.Imports {
  if imp.Path.Value!=`"testing"` && imp.Path.Value!=`"os"` {
   return fmt.Errorf("unadmitted import %s",imp.Path.Value)
  }
 }
 return nil
}

func main() {
 lane:=flag.String("lane","","independent public synthetic test lane")
 model:=flag.String("model","qwen2.5-coder:1.5b","local Ollama model")
 endpoint:=flag.String("endpoint","http://127.0.0.1:11434/api/generate","loopback-only inference API")
 targetDir:=flag.String("target-dir","../r051-batch","existing public Go workcell")
 flag.Parse()
 name,prompt,err:=task(*lane)
 if err!=nil{fmt.Fprintln(os.Stderr,"R062_HOLD",err);os.Exit(12)}
 if *endpoint!="http://127.0.0.1:11434/api/generate"{
  fmt.Fprintln(os.Stderr,"R062_HOLD only loopback model inference admitted")
  os.Exit(12)
 }
 ctx,cancel:=context.WithTimeout(context.Background(),180*time.Second)
 defer cancel()
 start:=time.Now()
 src,err:=acquire(ctx,*endpoint,*model,prompt)
 if err!=nil{fmt.Fprintln(os.Stderr,"R062_HOLD MODEL_CONTRACT",err);os.Exit(12)}
 if err:=validateGenerated(src);err!=nil{
  fmt.Fprintln(os.Stderr,"R062_HOLD MODEL_SOURCE",err);os.Exit(12)
 }
 dest:=filepath.Join(*targetDir,name)
 f,err:=os.OpenFile(dest,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0644)
 if err!=nil{fmt.Fprintln(os.Stderr,"R062_HOLD OWNER_PATH",err);os.Exit(12)}
 _,err=f.WriteString(src)
 errClose:=f.Close()
 if err!=nil||errClose!=nil{
  fmt.Fprintln(os.Stderr,"R062_HOLD WRITE",err,errClose);os.Exit(12)
 }
 sum:=sha256.Sum256([]byte(src))
 fmt.Printf("R062_MODEL_CANDIDATE lane=%s model=%s sha256=%s bytes=%d elapsed_ms=%d status=GENERATED_NOT_TESTED acceptance=false\n",
  *lane,*model,hex.EncodeToString(sum[:]),len(src),time.Since(start).Milliseconds())
}
