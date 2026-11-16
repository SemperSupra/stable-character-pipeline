// R063 treats the model as a bounded adversarial-fixture proposer, never as
// trusted Go code or an accepted test oracle. All emitted source is deterministic.
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
 "go/format"
 "io"
 "net/http"
 "os"
 "path/filepath"
 "strings"
 "time"
)

type proposedCase struct {
 Input string `json:"input"`
 Reject bool `json:"reject"`
}
type proposedCases struct {
 Cases []proposedCase `json:"cases"`
}
type localRequest struct {
 Model string `json:"model"`
 Prompt string `json:"prompt"`
 Stream bool `json:"stream"`
 Format string `json:"format"`
 Options map[string]any `json:"options"`
}
type localResponse struct {
 Response string `json:"response"`
 Error string `json:"error"`
}
const endpoint = "http://127.0.0.1:11434/api/generate"

func taskPrompt(lane string) (string,error) {
 head:=`You are proposing small adversarial test INPUTS, not code. Return ONLY one JSON object with exactly key "cases". It is an array of 4 objects, each with exactly keys "input" (a string) and "reject" (true/false). Provide at least 2 rejected and at least 1 accepted. Make all 4 inputs different. NEVER return markdown or Go source. Example structure: {"cases":[{"input":"example","reject":false},{"input":"bad","reject":true},{"input":"other","reject":true},{"input":"third","reject":false}]}. Choose inputs based on the following precise behavior:\n`
 switch lane {
 case "path":
  return head+`Go cleanPath accepts relative normalized forward-slash paths such as "src/good" and "src/good/**". It rejects absolute paths beginning with "/", backslashes, paths with ".." segments, "." components, embedded ":" and empty paths. Provide two rejected path strings and two valid paths, each unique. Do not use newline in paths.`,nil
 case "json":
  return head+`Go decodeLocalBounded loads a file as a Batch struct, rejects duplicated JSON object keys at any depth, trailing multiple JSON documents, unknown top-level fields, malformed JSON, and inputs >1MiB. It accepts "{}" and "{\"schema\":\"scp.r051.batch-rep.v1\"}". Each input string must be the CONTENTS of a JSON document (escape embedded quotes for outer response JSON). Supply two rejected inputs (like "{\"schema\":1,\"schema\":2}" and "{} {}") and two accepted inputs ("{}" and a valid JSON object with a known field). Use no private data.`,nil
 default:return "",fmt.Errorf("unknown lane %q",lane)
 }
}
func modelTag(model string) (string,error) {
 switch model {
 case "qwen2.5-coder:1.5b":return "m15",nil
 case "qwen2.5-coder:3b":return "m3",nil
 default:return "",errors.New("unadmitted model")
 }
}
func validateCases(b proposedCases) error {
 if len(b.Cases)<3||len(b.Cases)>5{return fmt.Errorf("invalid case count %d",len(b.Cases))}
 seen:=map[string]bool{}
 yes,no:=0,0
 for _,c:=range b.Cases {
  if len(c.Input)==0||len(c.Input)>320{return errors.New("blank or oversized case input")}
  if strings.ContainsRune(c.Input,0){return errors.New("NUL input not admitted")}
  if seen[c.Input]{return errors.New("duplicate proposed case input")}
  seen[c.Input]=true
  if c.Reject{yes++}else{no++}
 }
 if yes<2||no<1{return errors.New("need two rejects and one accept")}
 return nil
}
func generate(ctx context.Context, model,prompt string) (proposedCases,error) {
 var result proposedCases
 payload,err:=json.Marshal(localRequest{Model:model,Prompt:prompt,Stream:false,Format:"json",
  Options:map[string]any{"temperature":0.1,"num_ctx":2048,"num_predict":320}})
 if err!=nil{return result,err}
 req,err:=http.NewRequestWithContext(ctx,http.MethodPost,endpoint,bytes.NewReader(payload))
 if err!=nil{return result,err}
 req.Header.Set("Content-Type","application/json")
 client:=&http.Client{Timeout:165*time.Second}
 resp,err:=client.Do(req)
 if err!=nil{return result,err}
 defer resp.Body.Close()
 data,err:=io.ReadAll(io.LimitReader(resp.Body,16*1024))
 if err!=nil{return result,err}
 if resp.StatusCode!=http.StatusOK{return result,fmt.Errorf("model server HTTP %d",resp.StatusCode)}
 var decoded localResponse
 if err:=json.Unmarshal(data,&decoded);err!=nil{return result,fmt.Errorf("bad model envelope: %w",err)}
 if decoded.Error!=""{return result,errors.New(decoded.Error)}
 d:=json.NewDecoder(strings.NewReader(decoded.Response))
 d.DisallowUnknownFields()
 if err:=d.Decode(&result);err!=nil{return result,fmt.Errorf("bad model fixture JSON: %w",err)}
 if err:=d.Decode(&struct{}{});err!=io.EOF{return result,errors.New("trailing model fixture data")}
 return result,validateCases(result)
}
func renderTest(lane,tag string, b proposedCases) ([]byte,error) {
 if err:=validateCases(b);err!=nil{return nil,err}
 var out bytes.Buffer
 out.WriteString("// Model-proposed public synthetic fixture cases; deterministic source renderer.\npackage main\n\n")
 if lane=="json" {out.WriteString("import (\"fmt\"; \"os\"; \"testing\")\n\n")} else {out.WriteString("import (\"fmt\"; \"testing\")\n\n")}
 name:="TestR063"+strings.ToUpper(tag[:1])+tag[1:]+strings.ToUpper(lane[:1])+lane[1:]
 fmt.Fprintf(&out,"func %s(t *testing.T) {\n",name)
 out.WriteString("cases := []struct{Input string; Reject bool}{\n")
 for _,v:=range b.Cases {fmt.Fprintf(&out,"{%q, %v},\n",v.Input,v.Reject)}
 out.WriteString("}\nfor i, tc := range cases {\n")
 out.WriteString("t.Run(fmt.Sprintf(\"case-%d\",i),func(t *testing.T){\n")
 if lane=="path"{
  out.WriteString("err := cleanPath(tc.Input)\n")
 }else if lane=="json"{
  out.WriteString("p:=t.TempDir()+\"/fixture.json\"\n")
  out.WriteString("if err:=os.WriteFile(p,[]byte(tc.Input),0600); err!=nil{t.Fatal(err)}\n")
  out.WriteString("var parsed Batch\nerr:=decodeLocalBounded(p,&parsed)\n")
 }else{return nil,errors.New("bad lane")}
 out.WriteString("if tc.Reject && err==nil {t.Errorf(\"input %q must be rejected\",tc.Input)}\n")
 out.WriteString("if !tc.Reject && err!=nil {t.Errorf(\"input %q unexpectedly rejected: %v\",tc.Input,err)}\n")
 out.WriteString("})\n}\n}\n")
 formatted,err:=format.Source(out.Bytes())
 if err!=nil{return nil,fmt.Errorf("deterministic source format failure: %w",err)}
 return formatted,nil
}
func main() {
 lane:=flag.String("lane","","path or json")
 model:=flag.String("model","","local model name")
 flag.Parse()
 tag,err:=modelTag(*model)
 if err!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD",err);os.Exit(12)}
 prompt,err:=taskPrompt(*lane)
 if err!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD",err);os.Exit(12)}
 ctx,cancel:=context.WithTimeout(context.Background(),180*time.Second)
 defer cancel()
 start:=time.Now()
 b,err:=generate(ctx,*model,prompt)
 if err!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD MODEL_FIXTURES",err);os.Exit(12)}
 src,err:=renderTest(*lane,tag,b)
 if err!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD RENDER",err);os.Exit(12)}
 name:="r063_"+tag+"_"+*lane+"_test.go"
 file:=filepath.Join("../r051-batch",name)
 f,err:=os.OpenFile(file,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0644)
 if err!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD OWNED_FILE",err);os.Exit(12)}
 _,writeErr:=f.Write(src)
 closeErr:=f.Close()
 if writeErr!=nil||closeErr!=nil{fmt.Fprintln(os.Stderr,"R063_HOLD WRITE",writeErr,closeErr);os.Exit(12)}
 h:=sha256.Sum256(src)
 raw,_:=json.Marshal(b)
 fixtureSum:=sha256.Sum256(raw)
 fmt.Printf("R063_SOURCE_ONLY_GENERATED_UNTESTED lane=%s model=%s cases=%d fixture_sha256=%s candidate_sha256=%s bytes=%d wall_ms=%d\n",
  *lane,*model,len(b.Cases),hex.EncodeToString(fixtureSum[:]),hex.EncodeToString(h[:]),len(src),time.Since(start).Milliseconds())
}
