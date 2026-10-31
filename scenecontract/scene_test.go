package scenecontract
import(
 "bytes"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
)
func scene()Scene{return Scene{Schema:Schema,Revision:strings.Repeat("a",40),Action:"walk_approach",FPS:12,Frames:72,Cameras:[]string{"front","oblique"},Actors:[]Actor{
  {ID:"left",AssetDigest:"sha256:"+strings.Repeat("b",64),SourceClass:"public-synthetic"},
  {ID:"right",AssetDigest:"sha256:"+strings.Repeat("c",64),SourceClass:"public-synthetic"},
 }}}
func TestValidStructuralScene(t *testing.T){v:=Validate(scene());if v.Status!="PASS"{t.Fatal(v)}}
func TestFailClosedCases(t *testing.T){
 cases:=[]struct{name,code string;edit func(*Scene)}{
 {"wrong schema","SCHEMA_MISMATCH",func(s *Scene){s.Schema="scenes.v0"}},
 {"revision drift","INVALID_REVISION",func(s *Scene){s.Revision=strings.Repeat("d",39)}},
 {"wrong action","INVALID_ACTION",func(s *Scene){s.Action="teleport"}},
 {"bad fps","INVALID_CLOCK",func(s *Scene){s.FPS=0}},
 {"one actor","EXACTLY_TWO_ACTORS_REQUIRED",func(s *Scene){s.Actors=s.Actors[:1]}},
 {"duplicate actor","DUPLICATE_ACTOR",func(s *Scene){s.Actors[1].ID=s.Actors[0].ID}},
 {"asset digest","INVALID_ASSET_DIGEST",func(s *Scene){s.Actors[0].AssetDigest="lookslikeahash"}},
 {"source class","INVALID_SOURCE_CLASS",func(s *Scene){s.Actors[0].SourceClass="private-url"}},
 {"duplicate camera","DUPLICATE_CAMERA",func(s *Scene){s.Cameras[1]=s.Cameras[0]}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){s:=scene();tc.edit(&s);d:=Validate(s);if d.Code!=tc.code{t.Fatalf("%+v != %s",d,tc.code)}})}
}
func TestHTTPAndCLIParity(t *testing.T){
 b,_:=json.Marshal(scene())
 want,err:=Evaluate(bytes.NewReader(b));if err!=nil{t.Fatal(err)}
 req:=httptest.NewRequest("POST","http://127.0.0.1:8765/v1/scenes/validate",bytes.NewReader(b))
 req.Header.Set("Content-Type","application/json")
 w:=httptest.NewRecorder()
 Handler().ServeHTTP(w,req)
 var got Decision
 if err:=json.Unmarshal(w.Body.Bytes(),&got);err!=nil{t.Fatal(err)}
 if got!=want||w.Code!=200{t.Fatalf("CLI=%+v API=%+v HTTP %d",want,got,w.Code)}
}
func TestOriginAndHostileEnvelope(t *testing.T){
 b,_:=json.Marshal(scene())
 for _,tc:=range []struct{name,body,origin,contentType string;status int}{
  {"cross origin",string(b),"http://evil.example","application/json",403},
  {"wrong content-type",string(b),"","text/plain",415},
  {"duplicate key",`{"fps":12,"fps":100}`,"","application/json",400},
  {"trailing",string(b)+`{"schema":"second"}`,"","application/json",400},
  {"oversize",strings.Repeat(" ",1<<20+1),"","application/json",400},
 }{
  t.Run(tc.name,func(t *testing.T){
   req:=httptest.NewRequest("POST","http://127.0.0.1:8765/v1/scenes/validate",strings.NewReader(tc.body))
   req.Header.Set("Content-Type",tc.contentType)
   if tc.origin!=""{req.Header.Set("Origin",tc.origin)}
   w:=httptest.NewRecorder();Handler().ServeHTTP(w,req)
   if w.Code!=tc.status{t.Fatalf("got %d want %d: %s",w.Code,tc.status,w.Body.String())}
  })
 }
}
func TestHumanAndAgentDiscovery(t *testing.T){
 for _,tc:=range []struct{path string;needle string}{
  {"/","aria-live"},{"/ui.js","/v1/scenes/validate"},{"/v1/capabilities","agent_discovery"},
 }{
  w:=httptest.NewRecorder();Handler().ServeHTTP(w,httptest.NewRequest(http.MethodGet,tc.path,nil))
  if w.Code!=200||!strings.Contains(w.Body.String(),tc.needle){t.Fatalf("%s %d %s",tc.path,w.Code,w.Body.String())}
 }
}

func TestSourceNativeActorLabelsAndCasefoldCollision(t *testing.T){
 s:=scene()
 s.Actors[0].ID="CobaltOriginal"
 s.Actors[1].ID="MarigoldOriginal"
 if v:=Validate(s);v.Status!="PASS"{t.Fatalf("native source ID rejected: %+v",v)}
 s.Actors[1].ID="cobaltoriginal"
 if v:=Validate(s);v.Code!="DUPLICATE_ACTOR"{t.Fatalf("casefold collision accepted: %+v",v)}
}
