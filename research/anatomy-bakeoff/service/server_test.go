package service

import (
 "bytes"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
 anatomy "example.org/scp/anatomy-bakeoff"
)
func request(t *testing.T,s *Server,method,path string,body any,contentType string)*httptest.ResponseRecorder{
 t.Helper()
 var data []byte
 if body!=nil{data,_=json.Marshal(body)}
 req:=httptest.NewRequest(method,path,bytes.NewReader(data))
 if contentType!=""{req.Header.Set("Content-Type",contentType)}
 rec:=httptest.NewRecorder();s.ServeHTTP(rec,req);return rec
}
func TestHumanDiscoveryAndAccessibleMarkup(t *testing.T){
 s:=New();r:=request(t,s,"GET","/",nil,"")
 if r.Code!=200{t.Fatal(r.Code)}
 for _,needle:=range []string{"<main>","<h1>","<fieldset>","<legend>","for=\"locale\"","for=\"search\"","role=\"status\"","aria-live=\"polite\"","box.type=\"checkbox\"","/api/scene","/api/describe"}{
  if !strings.Contains(r.Body.String(),needle){t.Errorf("not discoverable: %q",needle)}
 }
 // This checks source markup only, NOT actual browser/screen-reader behavior.
}
func TestAutomationAgentCapabilityDiscovery(t *testing.T){
 s:=New()
 a:=request(t,s,"GET","/api/describe",nil,"")
 if a.Code!=200||!strings.Contains(a.Body.String(),"mutation"){t.Fatal(a.Code,a.Body.String())}
 b:=request(t,s,"GET","/api/scene",nil,"")
 if b.Code!=200||!strings.Contains(b.Body.String(),"synthetic-1"){t.Fatal(b.Code,b.Body.String())}
}
func TestSharedStateAndPhysicsSeparation(t *testing.T){
 s:=New();before,_:=anatomy.PhysicsDigest(s.scene)
 b:=Change{Schema:anatomy.Schema,Revision:"synthetic-1",System:"circulatory",Visible:false}
 a:=request(t,s,"POST","/api/view",b,"application/json")
 if a.Code!=200{t.Fatal(a.Code,a.Body.String())}
 if s.scene.View.Visible["heart"]{t.Fatal("failed to hide heart")}
 after,_:=anatomy.PhysicsDigest(s.scene)
 if before!=after{t.Fatal("visibility modified physics")}
 b2:=request(t,s,"POST","/api/view",b,"application/json")
 if b2.Code!=200{t.Fatal("non-idempotent toggle")}
}
func TestInvalidRequestsFailClosed(t *testing.T){
 s:=New()
 valid:=Change{Schema:anatomy.Schema,Revision:"synthetic-1",System:"circulatory",Visible:false}
 checks:=[]struct{name,method,path,ctype string;body any;status int}{
  {"bad-method","GET","/api/view","",nil,405},
  {"bad-content","POST","/api/view","text/plain",valid,415},
  {"unknown-system","POST","/api/view","application/json",Change{Schema:anatomy.Schema,Revision:"synthetic-1",System:"unsupported",Visible:false},422},
  {"stale-revision","POST","/api/view","application/json",Change{Schema:anatomy.Schema,Revision:"old",System:"circulatory",Visible:false},409},
  {"wrong-schema","POST","/api/view","application/json",Change{Schema:"wrong",Revision:"synthetic-1",System:"circulatory",Visible:false},422},
 }
 for _,c:=range checks{t.Run(c.name,func(t *testing.T){
   before,_:=anatomy.PhysicsDigest(s.scene)
   result:=request(t,s,c.method,c.path,c.body,c.ctype)
   if result.Code!=c.status{t.Fatalf("status=%d expected=%d response=%q",result.Code,c.status,result.Body.String())}
   after,_:=anatomy.PhysicsDigest(s.scene)
   if before!=after{t.Fatal("invalid command modified physics")}
 })}
}
