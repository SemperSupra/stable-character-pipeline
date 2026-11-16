package morphcontrol

import (
	"encoding/json"
	"errors"
	"math"
	"slices"
	"sync"
	"testing"
)

func legal()map[string]float64{
	result:=make(map[string]float64,len(Channels))
	for i,key:=range Channels{result[key]=float64(i+1)/20}
	return result
}
func start(t *testing.T)(*Controller,Plan) {
	t.Helper()
	c:=New()
	p,err:=c.Prepare(0,legal())
	if err!=nil{t.Fatal(err)}
	return c,p
}
func TestPositiveExact24CommandsAndRevision(t *testing.T){
	c,p:=start(t)
	if len(p.Sequence)!=24{t.Fatalf("expected 24, got %d",len(p.Sequence))}
	if p.Sequence[0].Target!=Targets[0]||p.Sequence[23].Target!=Targets[2]{t.Fatal("target ordering wrong")}
	if len(p.SHA256)!=64 {t.Fatal("missing signed canonical digest")}
	r,e:=c.Commit(p)
	if e!=nil{t.Fatal(e)}
	if r.Revision!=1||r.Commands!=24||r.Status!="PASS_NARROW_PREPARED_COMMANDS_ONLY"{t.Fatal(r)}
	s:=c.Snapshot()
	if s.Digest!=r.CommittedSHA256 || s.Values[7]!=.4 {t.Fatal("unexpected canonical state",s)}
}
func TestNoInputMutationBeforeCommit(t *testing.T){
	c,p:=start(t)
	baseline:=c.Snapshot()
	p.Sequence[4].Value=0.99
	if c.Snapshot()!=baseline {t.Fatal("prepare or caller mutation affected state")}
}
func TestInvalidValueFailsClosed(t *testing.T){
	for name,fn:=range map[string]func(map[string]float64){
		"NaN":func(m map[string]float64){m[Channels[0]]=math.NaN()},
		"positive infinity":func(m map[string]float64){m[Channels[1]]=math.Inf(1)},
		"negative infinity":func(m map[string]float64){m[Channels[1]]=math.Inf(-1)},
		"out of range":func(m map[string]float64){m[Channels[2]]=1.1},
		"below negative one":func(m map[string]float64){m[Channels[2]]=-1.1},
		"missing one":func(m map[string]float64){delete(m,Channels[2])},
		"extra one":func(m map[string]float64){m["inject"]=.2},
	}{
		t.Run(name,func(t *testing.T){
			c:=New();m:=legal();fn(m)
			if _,err:=c.Prepare(0,m);!errors.Is(err,ErrInvalid){t.Fatalf("expected ErrInvalid, got %v",err)}
			if c.Snapshot().Revision!=0{t.Fatal("invalid input mutated state")}
		})
	}
}
func TestSamePlanJSONStable(t *testing.T) {
	a,ap:=start(t);_,bp:=start(t)
	if ap.SHA256!=bp.SHA256 {t.Fatal("same canonical plan digests not stable")}
	bytes,err:=json.Marshal(ap)
	if err!=nil{t.Fatal(err)}
	var p Plan
	if err=json.Unmarshal(bytes,&p);err!=nil{t.Fatal(err)}
	if _,err=a.Commit(p);err!=nil{t.Fatal(err)}
}
func TestStaleVersionCannotOverwrite(t *testing.T){
	c,p:=start(t)
	if _,err:=c.Commit(p);err!=nil{t.Fatal(err)}
	if _,err:=c.Commit(p);!errors.Is(err,ErrStale){t.Fatalf("expected ErrStale, got %v",err)}
	if _,err:=c.Prepare(0,legal());!errors.Is(err,ErrStale){t.Fatalf("expected ErrStale, got %v",err)}
	if c.Snapshot().Revision!=1{t.Fatal("stale replay mutated revision")}
}
func TestDigestTamperingFailsClosed(t *testing.T){
	c,p:=start(t)
	p.SHA256="baadf00d"
	if _,err:=c.Commit(p);!errors.Is(err,ErrTampered){t.Fatalf("expected digest rejection, got %v",err)}
	if c.Snapshot().Revision!=0{t.Fatal("tampering mutated state")}
}
func TestValueMutationFailsClosed(t *testing.T){
	c,p:=start(t)
	p.Sequence[2].Value=.789
	if _,err:=c.Commit(p);!errors.Is(err,ErrInvalid){t.Fatalf("expected divergence rejection, got %v",err)}
	if c.Snapshot().Revision!=0{t.Fatal("mutated plan affected state")}
}
func TestTargetSwapFailsClosed(t *testing.T) {
	c,p:=start(t)
	p.Sequence[0],p.Sequence[8]=p.Sequence[8],p.Sequence[0]
	if _,err:=c.Commit(p);!errors.Is(err,ErrInvalid){t.Fatalf("expected target index rejection, got %v",err)}
}
func TestMissingCommandFailsClosed(t *testing.T){
	c,p:=start(t)
	p.Sequence=p.Sequence[:23]
	if _,err:=c.Commit(p);!errors.Is(err,ErrInvalid){t.Fatalf("expected missing command rejection, got %v",err)}
}
func TestDuplicatedCommandFailsClosed(t *testing.T){
	c,p:=start(t)
	p.Sequence[23]=p.Sequence[22]
	if _,err:=c.Commit(p);!errors.Is(err,ErrInvalid){t.Fatalf("expected duplicate rejection, got %v",err)}
}
func TestBadSchemaFailsClosed(t *testing.T){
	c,p:=start(t)
	p.Schema="r048.inject"
	if _,err:=c.Commit(p);!errors.Is(err,ErrInvalid){t.Fatalf("expected schema rejection, got %v",err)}
}
func TestNegativeZeroCanonicalization(t *testing.T){
	c:=New();m:=legal();m[Channels[0]]=math.Copysign(0,-1)
	p,err:=c.Prepare(0,m)
	if err!=nil{t.Fatal(err)}
	if math.Signbit(p.Sequence[0].Value){t.Fatal("negative zero not canonicalized")}
}
func TestConcurrentPrepareOnlyOneCommit(t *testing.T){
	c,p:=start(t)
	var wg sync.WaitGroup
	wg.Add(12)
	successes:=make(chan bool,12)
	for range 12 {
		go func(){defer wg.Done();_,err:=c.Commit(p);successes<-err==nil}()
	}
	wg.Wait();close(successes)
	n:=0;for ok:=range successes{if ok{n++}}
	if n!=1||c.Snapshot().Revision!=1{t.Fatalf("nonserializable concurrent commits: %d",n)}
}
func TestChainDigestAndSnapshotCopy(t *testing.T){
	c,p:=start(t);first,err:=c.Commit(p)
	if err!=nil{t.Fatal(err)}
	m:=legal();m[Channels[4]]=-.5
	q,err:=c.Prepare(1,m);if err!=nil{t.Fatal(err)}
	if slices.EqualFunc(p.Sequence,q.Sequence,func(a,b Entry)bool{return a==b}){t.Fatal("unchanged planned commands")}
	second,err:=c.Commit(q);if err!=nil{t.Fatal(err)}
	if second.PreviousSHA256!=first.CommittedSHA256||second.Revision!=2||second.CommittedSHA256==first.CommittedSHA256{
		t.Fatal("bad append-only chain",second)
	}
	copy:=c.Snapshot();copy.Values[4]=5
	if c.Snapshot().Values[4]!=-.5{t.Fatal("state exposed to caller mutation")}
}
