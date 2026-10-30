//go:build linux
package ledger

import (
 "encoding/json"
 "os"
 "path/filepath"
 "sync"
 "testing"
 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)
func policy()sweeps.AccessPolicy{return sweeps.AccessPolicy{
 ProviderID:"fixture",PolicyRef:"synthetic:policy",Verified:true,TermsPermit:true,Operation:"search_only",Method:"documented_api",
 UserAgent:"StableCharacterPipeline/Research (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)",
 MaxPerMinute:2,MaxPerDay:4,MinGapMS:2500,MaxConcurrency:1,MaxPages:3,MaxResponseBytes:65536,CacheTTLSeconds:3600}}
func TestAtomicConcurrentReservations(t *testing.T){
 p:=policy();l:=Ledger{Path:filepath.Join(t.TempDir(),"state.json")}
 const n=24; var wg sync.WaitGroup;results:=make(chan string,n)
 for i:=0;i<n;i++ {wg.Add(1);go func(){defer wg.Done();_,result,err:=l.Reserve(p,"https://assets.example.org",1000);if err!=nil{results<-"ERROR:"+err.Error()}else{results<-result.Status}}()}
 wg.Wait();close(results)
 allowed:=0;for result:=range results {if result=="PLAN_PERMITTED"{allowed++}else if result!="CONCURRENCY_HOLD"&&result!="PACE_HOLD" {t.Fatalf("unexpected concurrent result %s",result)}}
 if allowed!=1{t.Fatalf("concurrent allowed=%d; want 1",allowed)}
 b,err:=os.ReadFile(l.Path);if err!=nil{t.Fatal(err)}
 var saved State; if err:=json.Unmarshal(b,&saved);err!=nil{t.Fatal(err)}
 if len(saved.Entries)!=1||saved.Schema!="scp.origin_quota_ledger.v1"{t.Fatalf("bad durable state: %+v",saved)}
}
func TestCooldownPacingAndReplay(t *testing.T){
 p:=policy();l:=Ledger{Path:filepath.Join(t.TempDir(),"state.json")}
 ticket,g,err:=l.Reserve(p,"https://assets.example.org",1000)
 if err!=nil||g.Status!="PLAN_PERMITTED"{t.Fatalf("%+v %v",g,err)}
 if e:=l.Complete(ticket,429,10,1100);e!=nil{t.Fatal(e)}
 if e:=l.Complete(ticket,200,0,1200);e==nil{t.Fatal("replay completion admitted")}
 _,g,_=l.Reserve(p,"https://assets.example.org",4000)
 if g.Status!="RETRY_AFTER_HOLD"{t.Fatalf("failed retry-after: %+v",g)}
 ticket2,g,err:=l.Reserve(p,"https://assets.example.org",11200)
 if err!=nil||g.Status!="PLAN_PERMITTED"{t.Fatalf("cooldown not expired: %+v %v",g,err)}
 if err:=l.Complete(ticket2,403,0,11300);err!=nil{t.Fatal(err)}
 _,g,_=l.Reserve(p,"https://assets.example.org",100000)
 if g.Status!="ACCESS_HOLD"{t.Fatalf("403 bypass: %+v",g)}
}
func TestFailClosedFilesystemAndScope(t *testing.T){
 dir:=t.TempDir();p:=policy()
 l:=Ledger{Path:filepath.Join(dir,"state.json")}
 if _,_,err:=l.Reserve(p,"http://assets.example.org",1000);err==nil{t.Fatal("not https")}
 if err:=os.WriteFile(l.Path,[]byte("{corrupted"),0600);err!=nil{t.Fatal(err)}
 if _,_,err:=l.Reserve(p,"https://assets.example.org",1000);err==nil{t.Fatal("corrupt ledger should fail")}
 if err:=os.Remove(l.Path);err!=nil{t.Fatal(err)}
 p.Verified=false
 _,got,err:=l.Reserve(p,"https://assets.example.org",1000)
 if err!=nil||got.Status!="POLICY_HOLD"{t.Fatalf("unverified policy bypassed %+v %v",got,err)}
 p.Verified=true
 if err:=os.Symlink(filepath.Join(dir,"not-real"),l.Path);err!=nil{t.Fatal(err)}
 if _,_,err:=l.Reserve(p,"https://assets.example.org",1000);err==nil{t.Fatal("ledger symlink not refused")}
}
func TestUnresolvedReservationBlocks(t *testing.T){
 p:=policy();l:=Ledger{Path:filepath.Join(t.TempDir(),"state.json")}
 first,_,err:=l.Reserve(p,"https://assets.example.org",1000)
 if err!=nil{t.Fatal(err)}
 _,g,_:=l.Reserve(p,"https://assets.example.org",100000)
 if g.Status!="CONCURRENCY_HOLD"{t.Fatalf("unresolved ticket bypassed: %+v",g)}
 if err:=l.Complete(first,0,0,100200);err!=nil{t.Fatal(err)}
 _,g,_=l.Reserve(p,"https://assets.example.org",104000)
 if g.Status!="SERVER_HOLD"{t.Fatalf("transport error not held: %+v",g)}
}
