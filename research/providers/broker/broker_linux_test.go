//go:build linux
package broker

import (
 "bytes"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "path/filepath"
 "strings"
 "sync"
 "sync/atomic"
 "testing"
 "time"

 "github.com/SemperSupra/stable-character-pipeline/research/providers/ledger"
 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)
const token="fixture-only-credential-000000000000000000000"
func fixture(t *testing.T)(*httptest.Server,*atomic.Int64){
 t.Helper()
 var clock atomic.Int64;clock.Store(1000)
 p:=sweeps.AccessPolicy{ProviderID:"fixture",PolicyRef:"synthetic-reviewed",Verified:true,TermsPermit:true,Operation:"search_only",
  Method:"documented_api",UserAgent:"StableCharacterPipeline/Research (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)",
  MaxPerMinute:3,MaxPerDay:10,MinGapMS:1500,MaxConcurrency:1,MaxPages:3,MaxResponseBytes:32768,CacheTTLSeconds:3600}
 b,err:=New(Config{Ledger:ledger.Ledger{Path:filepath.Join(t.TempDir(),"ledger.json")},
  Policies:map[string]sweeps.AccessPolicy{"fixture":p},Origins:map[string]string{"fixture":"https://example.org"},
  TestCredential:token,Clock:func()time.Time{return time.UnixMilli(clock.Load())}})
 if err!=nil{t.Fatal(err)}
 return httptest.NewServer(b),&clock
}
func call(t *testing.T,client *http.Client,url,path string,payload any,credential string)(int,Response){
 t.Helper()
 data,_:=json.Marshal(payload);req,err:=http.NewRequest("POST",url+path,bytes.NewReader(data));if err!=nil{t.Fatal(err)}
 req.Header.Set("Content-Type","application/json")
 if credential!="" {req.Header.Set("Authorization","Bearer "+credential)}
 resp,err:=client.Do(req);if err!=nil{t.Fatal(err)}
 defer resp.Body.Close()
 var row Response;if err:=json.NewDecoder(resp.Body).Decode(&row);err!=nil{t.Fatal(err)}
 return resp.StatusCode,row
}
func TestTwoWorkerClientsShareSingleReservation(t *testing.T){
 srv,_:=fixture(t);defer srv.Close()
 clients:=[]*http.Client{{Timeout:time.Second*4},{Timeout:time.Second*4}}
 var wg sync.WaitGroup
 codes:=make(chan int,2)
 for _,c:=range clients{wg.Add(1);go func(c *http.Client){defer wg.Done();code,_:=call(t,c,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://example.org"},token);codes<-code}(c)}
 wg.Wait();close(codes);ok,denied:=0,0;for c:=range codes{if c==200 {ok++};if c==409{denied++}}
 if ok!=1||denied!=1 {t.Fatalf("expected exact one shared lock, got success=%d denied=%d",ok,denied)}
}
func TestTokenOriginRetryAfterAndReplay(t *testing.T){
 srv,clock:=fixture(t);defer srv.Close()
 cl:=srv.Client()
 for _,cred:=range []string{"", "wrong"}{
  status,_:=call(t,cl,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://example.org"},cred)
  if status!=401{t.Fatalf("invalid token status=%d",status)}
 }
 status,_:=call(t,cl,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://other.org"},token)
 if status!=403{t.Fatalf("unallowlisted origin status=%d",status)}
 status,r:=call(t,cl,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://example.org"},token)
 if status!=200||r.Ticket==nil{t.Fatalf("valid reserve: %d %+v",status,r)}
 clock.Store(1100)
 completed:=CompleteRequest{Ticket:*r.Ticket,HTTPStatus:429,RetryAfterSeconds:10}
 status,_=call(t,cl,srv.URL,"/v1/complete",completed,token)
 if status!=200{t.Fatalf("complete: %d",status)}
 status,_=call(t,cl,srv.URL,"/v1/complete",completed,token)
 if status!=409{t.Fatalf("replayed ticket: %d",status)}
 clock.Store(4000)
 status,r=call(t,cl,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://example.org"},token)
 if status!=409||!strings.Contains(r.Reason,"RETRY_AFTER"){t.Fatalf("429 gate bypass: %d %+v",status,r)}
 clock.Store(11200)
 status,r=call(t,cl,srv.URL,"/v1/reserve",ReserveRequest{Provider:"fixture",Origin:"https://example.org"},token)
 if status!=200||r.Ticket==nil{t.Fatalf("cooldown expiry: %d %+v",status,r)}
}
func TestStrictSchemaUnknownFields(t *testing.T){
 srv,_:=fixture(t);defer srv.Close()
 status,_:=call(t,srv.Client(),srv.URL,"/v1/reserve",map[string]any{"provider":"fixture","origin":"https://example.org","extra":"must reject"},token)
 if status!=400{t.Fatalf("unexpected field allowed: %d",status)}
}
