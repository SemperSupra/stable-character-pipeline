package scenejob
import(
 "bytes"
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "sync/atomic"
 "testing"
 "time"
)
const testRevision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
type fakeEngine struct{calls atomic.Int32; fail bool; pause bool}
func put(path string,b []byte)(string,error){
 if err:=os.MkdirAll(filepath.Dir(path),0700);err!=nil{return "",err}
 if err:=os.WriteFile(path,b,0600);err!=nil{return "",err}
 d:=sha256.Sum256(b)
 return hex.EncodeToString(d[:]),nil
}
func(e *fakeEngine)Run(ctx context.Context,dir,rev string)error{
 e.calls.Add(1)
 if e.pause{time.Sleep(50*time.Millisecond)}
 if e.fail{
  _,_=put(filepath.Join(dir,"first-failure-observation.txt"),[]byte("original failure retained"))
  return errors.New("first failure")
 }
 source,_:=put(filepath.Join(dir,"forward/source.json"),[]byte("source-only original fixture"))
 glb,_:=put(filepath.Join(dir,"forward/original_synthetic_24frame_skinned.glb"),[]byte("fake original glb"))
 blend,_:=put(filepath.Join(dir,"forward/original_source_grounded_24frame_native.blend"),[]byte("fake original blend"))
 videos:=map[string]string{}
 for _,c:=range cameras{
  digest,_:=put(filepath.Join(dir,"forward/rendered",c+".mp4"),[]byte("fake original "+c))
  videos[c]=digest
 }
 r:=Result{Schema:ResultSchema,JobID:JobID,Revision:rev,
  SourceClass:"public-synthetic",Rights:"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  SourceSHA:source,GLBSHA:glb,BlendSHA:blend,Videos:videos,
  FPS:12,Frames:24,ActorIDs:[]string{"CobaltOriginal","MarigoldOriginal"},
  Cameras:[]string{"OriginalFront","OriginalOblique"},
  ObservedVideo:"PASS_ALL_REQUIRED_VIEWS_L1_ONLY",
  HumanBehavior:"FAIL_ABSTRACT_LIMBS_ONLY",HumanAnatomy:"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
  Release:"HELD_R009_NOT_RUN_NOT_ADMITTED"}
 raw,_:=json.Marshal(r)
 _,err:=put(filepath.Join(dir,"result.json"),raw)
 return err
}
func testManager(t *testing.T,e Engine)*Manager{
 t.Helper()
 m,err:=NewManager(testRevision,t.TempDir(),e)
 if err!=nil{t.Fatal(err)}
 return m
}
func reqBody()(Request,[]byte){
 r:=Expected(testRevision);b,_:=json.Marshal(r);return r,b
}
func TestActualCoreAPICLIAndHumanMediaOneManager(t *testing.T){
 engine:=&fakeEngine{}
 m:=testManager(t,engine)
 request,body:=reqBody()
 got,err:=m.Run(context.Background(),request)
 if err!=nil||got.Release!="HELD_R009_NOT_RUN_NOT_ADMITTED"{t.Fatalf("%+v %v",got,err)}
 if _,err:=m.Run(context.Background(),request);err!=nil{t.Fatal(err)}
 if engine.calls.Load()!=1{t.Fatal("repeated CLI did not reuse trusted result")}
 srv:=m.Handler()
 for i:=0;i<2;i++{
  h:=httptest.NewRequest("POST","http://127.0.0.1:8766/v1/jobs",bytes.NewReader(body))
  h.Header.Set("Content-Type","application/json")
  w:=httptest.NewRecorder();srv.ServeHTTP(w,h)
  var report Result
  if err:=json.Unmarshal(w.Body.Bytes(),&report);err!=nil{t.Fatal(err)}
  if w.Code!=200||report!=got && report.Release!=got.Release{
   t.Fatalf("HTTP job != same core: %d %+v",w.Code,report)
  }
 }
 if engine.calls.Load()!=1{t.Fatal("HTTP reused job but re-executed engine")}
 for _,camera:=range cameras{
  path:="/v1/jobs/"+JobID+"/media/"+camera
  rec:=httptest.NewRecorder();srv.ServeHTTP(rec,httptest.NewRequest("GET",path,nil))
  if rec.Code!=200||rec.Header().Get("Content-Type")!="video/mp4"||!strings.Contains(rec.Body.String(),camera){
   t.Fatalf("clean video endpoint %s got %d",camera,rec.Code)
  }
 }
 for _,tc:=range []struct{path,needle string}{
  {"/","aria-live"},{"/ui.js","/v1/jobs"},
  {"/v1/capabilities","agent_execute"},{"/v1/jobs/"+JobID,"FAIL_ABSTRACT_LIMBS_ONLY"},
 }{
  w:=httptest.NewRecorder()
  srv.ServeHTTP(w,httptest.NewRequest("GET",tc.path,nil))
  if w.Code!=200||!strings.Contains(w.Body.String(),tc.needle){
   t.Fatalf("%s status %d body %s",tc.path,w.Code,w.Body.String())
  }
 }
}
func TestUntrustedOriginAndProtectedJobFailClosed(t *testing.T){
 engine:=&fakeEngine{}
 m:=testManager(t,engine);server:=m.Handler()
 base,body:=reqBody()
 cases:=[]struct{name string;payload []byte;origin string;contentType string;code int}{
  {"cross-origin",body,"http://evil.example","application/json",403},
  {"missing-content-type",body,"","text/plain",415},
  {"duplicate-key",[]byte(`{"schema":"scp.native-job-request.v1","schema":"changed"}`),"","application/json",400},
  {"trailing",append(body,[]byte("{}")...),"","application/json",400},
  {"extra-key",[]byte(`{"schema":"scp.native-job-request.v1","job_id":"w7a-forward-24","revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","source_class":"public-synthetic","shell":"command"}`),"","application/json",400},
  {"private-scope",func()[]byte{q:=base;q.SourceClass="protected-product";b,_:=json.Marshal(q);return b}(),"","application/json",422},
  {"rev-swap",func()[]byte{q:=base;q.Revision=strings.Repeat("b",40);b,_:=json.Marshal(q);return b}(),"","application/json",422},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  req:=httptest.NewRequest("POST","http://127.0.0.1:8766/v1/jobs",bytes.NewReader(tc.payload))
  req.Header.Set("Content-Type",tc.contentType)
  if tc.origin!=""{req.Header.Set("Origin",tc.origin)}
  w:=httptest.NewRecorder();server.ServeHTTP(w,req)
  if w.Code!=tc.code{t.Fatalf("got %d want %d: %s",w.Code,tc.code,w.Body.String())}
 })}
 if engine.calls.Load()!=0{t.Fatal("untrusted job executed")}
}
func TestConcurrentCallsHaveOneWriter(t *testing.T){
 e:=&fakeEngine{pause:true};m:=testManager(t,e)
 var wg sync.WaitGroup
 for i:=0;i<12;i++{
  wg.Add(1);go func(){defer wg.Done()
   if _,err:=m.Run(context.Background(),Expected(testRevision));err!=nil{t.Error(err)}
  }()
 }
 wg.Wait()
 if e.calls.Load()!=1{t.Fatalf("duplicate concurrent execution count %d",e.calls.Load())}
}
func TestFirstFailurePreservedAndCannotMasquer(t *testing.T){
 e:=&fakeEngine{fail:true}
 m:=testManager(t,e)
 if _,err:=m.Run(context.Background(),Expected(testRevision));err==nil{t.Fatal("expected first failure")}
 if _,err:=os.Stat(filepath.Join(m.root,"attempt-0001","first-failure-observation.txt"));err!=nil{
  t.Fatal("historical failure erased",err)
 }
 if _,ready,_:=m.Result();ready{t.Fatal("failed attempt promoted")}
 e.fail=false
 if _,err:=m.Run(context.Background(),Expected(testRevision));err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Join(m.root,"attempt-0001","first-failure-observation.txt"));err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Join(m.root,"attempt-0002","result.json"));err!=nil{t.Fatal(err)}
}
func TestTamperedCleanMediaCannotBeServed(t *testing.T){
 m:=testManager(t,&fakeEngine{})
 if _,err:=m.Run(context.Background(),Expected(testRevision));err!=nil{t.Fatal(err)}
 bad:=filepath.Join(m.completeDir,"forward/rendered/OriginalFront.mp4")
 if err:=os.WriteFile(bad,[]byte("tampered"),0600);err!=nil{t.Fatal(err)}
 if _,err:=m.MediaPath("OriginalFront");err==nil{t.Fatal("tampered media was served")}
 if _,ok,err:=m.Result();!ok||err==nil{t.Fatal("tampered original receipt still accepted")}
}
func TestNoUnboundedPathOrSourceInjection(t *testing.T){
 e:=&fakeEngine{};m:=testManager(t,e)
 for _,name:=range []string{"../../evil","w7a-forward-24;rm","R009"}{
  r:=Expected(testRevision);r.JobID=name
  if _,err:=m.Run(context.Background(),r);err==nil{t.Fatal("accepted job",name)}
 }
 if e.calls.Load()!=0{t.Fatal("untrusted job executed")}
 if err:=Admit(Expected(strings.Repeat("b",40)),testRevision);err==nil{t.Fatal("revision not bound")}
 if _,err:=NewManager("bad",t.TempDir(),e);err==nil{t.Fatal("bad source revision accepted")}
 if (DockerEngine{Image:"private:latest"}).Run(context.Background(),".",testRevision)==nil{
  t.Fatal("unapproved runtime admitted")
 }
}
func TestSourceOrScientificStatusForgeryDenied(t *testing.T){
 for _,mode:=range []string{"rights","behavior","release","source"}{
  t.Run(mode,func(t *testing.T){
   m:=testManager(t,&fakeEngine{});_,err:=m.Run(context.Background(),Expected(testRevision));if err!=nil{t.Fatal(err)}
   path:=filepath.Join(m.completeDir,"result.json")
   raw,_:=os.ReadFile(path);var data map[string]any;_ = json.Unmarshal(raw,&data)
   switch mode{
   case "rights":data["rights"]="PRIVATE_UNVERIFIED"
   case "behavior":data["human_behavior"]="PASS"
   case "release":data["release"]="READY_FOR_RELEASE"
   case "source":data["source_sha256"]=strings.Repeat("c",64)
   }
   changed,_:=json.Marshal(data)
   if err:=os.WriteFile(path,changed,0600);err!=nil{t.Fatal(err)}
   if _,_,err:=m.Result();err==nil{t.Fatal("forged result accepted",mode)}
  })
 }
}
func ExampleRequest(){
 r:=Expected(testRevision);fmt.Println(r.Schema,r.JobID,r.SourceClass)
 // Output: scp.native-job-request.v1 w7a-forward-24 public-synthetic
}
