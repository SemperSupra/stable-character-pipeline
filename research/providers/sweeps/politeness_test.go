package sweeps

import "testing"

func citizen()AccessPolicy{return AccessPolicy{
 ProviderID:"example",PolicyRef:"fixture:approved",Verified:true,TermsPermit:true,
 Operation:"search_only",Method:"documented_api",UserAgent:"StableCharacterPipeline-Research/1.0 (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)",
 MaxPerMinute:2,MaxPerDay:3,MinGapMS:3000,MaxConcurrency:1,
 MaxPages:3,MaxResponseBytes:65536,CacheTTLSeconds:3600,
}}
func TestCitizenPolicyAndBudgets(t *testing.T){
 p:=citizen()
 if err:=ValidatePolicy(p);err!=nil{t.Fatal(err)}
 zero:=RequestState{}
 if got:=CheckPermit(p,zero,1000);got.Status!="PLAN_PERMITTED"{t.Fatalf("%+v",got)}
 s,err:=AfterResponse(zero,200,0,1000)
 if err!=nil{t.Fatal(err)}
 if got:=CheckPermit(p,s,1100);got.Status!="PACE_HOLD"{t.Fatalf("too fast: %+v",got)}
 if got:=CheckPermit(p,s,4000);got.Status!="PLAN_PERMITTED"{t.Fatalf("at min gap: %+v",got)}
 s,err=AfterResponse(s,200,0,4000)
 if err!=nil{t.Fatal(err)}
 if got:=CheckPermit(p,s,7000);got.Status!="QUOTA_HOLD"{t.Fatalf("per minute must cap: %+v",got)}
 if got:=CheckPermit(p,s,62000);got.Status!="PLAN_PERMITTED"{t.Fatalf("minute window should release: %+v",got)}
 s,err=AfterResponse(s,200,0,62000)
 if err!=nil{t.Fatal(err)}
 if got:=CheckPermit(p,s,65000);got.Status!="PAGE_BUDGET_HOLD"{t.Fatalf("page cap: %+v",got)}
}
func TestCitizen429And403NoBypass(t *testing.T){
 p:=citizen()
 s,_:=AfterResponse(RequestState{},429,60,1000)
 if got:=CheckPermit(p,s,10000);got.Status!="RETRY_AFTER_HOLD"||got.NextEligibleMS!=61000{t.Fatalf("ignored 429: %+v",got)}
 if got:=CheckPermit(p,s,61000);got.Status!="PLAN_PERMITTED" {t.Fatalf("cooldown not released: %+v",got)}
 s,_=AfterResponse(RequestState{},429,0,1000)
 if got:=CheckPermit(p,s,90000);got.Status!="RATE_HOLD"{t.Fatalf("missing retry after not held: %+v",got)}
 for _,status:=range []int{401,403} {
  s,_:=AfterResponse(RequestState{},status,0,1000)
  got:=CheckPermit(p,s,90000)
  if got.Status!="AUTH_HOLD"&&got.Status!="ACCESS_HOLD"{t.Fatalf("must not bypass %d: %+v",status,got)}
 }
}
func TestCitizenFailClosedToSRobotsAndAttribution(t *testing.T){
 p:=citizen()
 p.Verified=false
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="POLICY_HOLD"{t.Fatal(got)}
 p=citizen();p.TermsPermit=false
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="POLICY_HOLD"{t.Fatal(got)}
 p=citizen();p.Method="crawler";p.RobotsChecked=false
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="POLICY_HOLD"{t.Fatal(got)}
 p.RobotsChecked=true;p.RobotsAllow=false
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="POLICY_HOLD"{t.Fatal(got)}
 p=citizen();p.ProviderID="polyhaven";p.VisibleAttribution=false
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="POLICY_HOLD"{t.Fatal(got)}
 p.VisibleAttribution=true
 if got:=CheckPermit(p,RequestState{},1000);got.Status!="PLAN_PERMITTED"{t.Fatal(got)}
}
func TestCitizenNoParallelOrExcess(t *testing.T){
 p:=citizen();s:=RequestState{Active:1}
 if got:=CheckPermit(p,s,1000);got.Status!="CONCURRENCY_HOLD"{t.Fatal(got)}
 p.MaxConcurrency=4
 if err:=ValidatePolicy(p);err==nil{t.Fatal("excess concurrency allowed")}
 p=citizen();p.MaxPerMinute=999
 if err:=ValidatePolicy(p);err==nil{t.Fatal("unbounded quota")}
 p=citizen();p.MaxResponseBytes=1024*1024
 if err:=ValidatePolicy(p);err==nil{t.Fatal("unbounded response")}
}
func TestCitizen500NoBlindRetry(t *testing.T){
 p:=citizen();s,_:=AfterResponse(RequestState{},503,0,1000)
 if got:=CheckPermit(p,s,60000);got.Status!="SERVER_HOLD"{t.Fatal(got)}
}
