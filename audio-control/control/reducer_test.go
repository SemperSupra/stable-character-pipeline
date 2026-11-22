package control

import (
 "math/rand"
 "reflect"
 "testing"
)
func setup(t *testing.T)*Machine{
 t.Helper()
 m,e:=NewMachine("session.synthetic","target.synthetic")
 if e!=nil{t.Fatal(e)}
 return m
}
func cmd(id string,a Action,rev,epoch uint64)Command{
 return Command{SessionID:"session.synthetic",TargetID:"target.synthetic",
 OperationID:id,Action:a,ExpectedRevision:rev,Epoch:epoch}
}
func configure(t *testing.T,m *Machine) {
 t.Helper()
 c:=cmd("cfg",Configure,0,0)
 c.ConfigDigest=Digest([]byte("synthetic-no-audio"))
 o:=m.Apply(c)
 if o.Receipt.State!=Configured||o.Receipt.Revision!=1||len(o.Dispatch)!=0{
  t.Fatalf("configure: %+v",o)
 }
}
func start(t *testing.T,m *Machine)Outcome{
 t.Helper()
 r:=m.Apply(cmd("start",RequestStart,1,0))
 if r.Receipt.State!=StartPending||r.Receipt.Epoch!=1||
 len(r.Dispatch)!=1||r.Dispatch[0].Kind!="host_authorize_then_start"{t.Fatalf("start: %+v",r)}
 return r
}
func TestStopDominatesLateHostStart(t *testing.T){
 m:=setup(t);configure(t,m);first:=start(t,m)
 stop:=m.Apply(cmd("stop",Stop,0,0)) // Must bypass stale revision.
 if stop.Receipt.State!=StopPending||stop.Receipt.Revision!=3||
 len(stop.Dispatch)!=1||stop.Dispatch[0].Kind!="host_stop_now"{t.Fatalf("stop: %+v",stop)}
 replay:=m.Apply(cmd("stop",Stop,0,0))
 if !replay.Replayed||len(replay.Dispatch)!=0||!reflect.DeepEqual(stop.Receipt,replay.Receipt){
  t.Fatalf("duplicate stop redispatched or changed receipt: %+v",replay)
 }
 late:=m.Apply(cmd("host-start",HostStarted,0,1))
 if late.Receipt.State!=StopPending||late.Receipt.Status!="ignored_late_start"||
 len(late.Dispatch)!=1||late.Dispatch[0].Kind!="host_stop_now"{
  t.Fatalf("late host start revived output: %+v",late)
 }
 ended:=m.Apply(cmd("host-stop",HostStopped,0,1))
 if ended.Receipt.State!=Stopped||ended.Receipt.Revision!=4{t.Fatalf("host stopped: %+v",ended)}
 if got:=m.Apply(cmd("second-start",RequestStart,4,0));got.Receipt.Status=="accepted"{
  t.Fatal("terminal STOP allowed restart without new session")
 }
 if got:=m.Apply(cmd("close",Close,4,0));got.Receipt.State!=Closed{t.Fatal("close terminal failed")}
 if first.Receipt.Epoch!=1{t.Fatal("start epoch lost")}
}
func TestStartObservationAndCompletion(t *testing.T){
 m:=setup(t);configure(t,m);start(t,m)
 started:=m.Apply(cmd("host-start",HostStarted,0,1))
 if started.Receipt.State!=Active||started.Receipt.Revision!=3{t.Fatalf("host start: %+v",started)}
 completed:=m.Apply(cmd("host-completed",HostCompleted,0,1))
 if completed.Receipt.State!=Completed||completed.Receipt.Revision!=4{t.Fatalf("host EOS: %+v",completed)}
 if r:=m.Apply(cmd("stop",Stop,0,0));r.Receipt.State!=Completed||len(r.Dispatch)!=0{t.Fatalf("stop post EOS: %+v",r)}
}
func TestIdempotencyConflictStaleAndScope(t *testing.T){
 m:=setup(t);configure(t,m)
 original:=m.Apply(cmd("start",RequestStart,1,0))
 if x:=m.Apply(cmd("start",RequestStart,1,0));!x.Replayed||len(x.Dispatch)!=0||
  !reflect.DeepEqual(x.Receipt,original.Receipt){t.Fatalf("replay: %+v",x)}
 collision:=cmd("start",RequestStart,1,0);collision.TargetID="other"
 // Scope rejection takes precedence and does not reveal another session's receipt.
 if x:=m.Apply(collision);x.Receipt.Status!="rejected"{t.Fatal("cross-target not rejected")}
 collision=cmd("start",RequestStart,999,0)
 if x:=m.Apply(collision);x.Receipt.Status!="operation_id_reused_with_different_payload"{t.Fatal("same ID altered payload accepted")}
 if x:=m.Apply(cmd("stale",Close,1,0));x.Receipt.Status!="stale_revision"{t.Fatal("stale revision accepted")}
 if x:=m.Apply(cmd("stale-host",HostStarted,0,99));x.Receipt.Status!="stale_epoch"{t.Fatal("stale host epoch accepted")}
 if x:=m.Apply(cmd("same-host-start",HostStarted,0,1));x.Receipt.State!=Active{t.Fatal("valid host observation rejected")}
 if x:=m.Apply(cmd("stop",Stop,0,0));x.Receipt.State!=StopPending{t.Fatal("STOP could not override stale revision")}
}
func TestBoundedHistoryAndAdversarialTrace(t *testing.T){
 m:=setup(t);configure(t,m);start(t,m)
 r:=rand.New(rand.NewSource(20261122))
 actions:=[]Action{RequestStart,Stop,HostStarted,HostStopped,HostCompleted,HostFailed,Close,Configure}
 wasStopped:=false
 prevRev:=m.Snapshot().Revision
 for i:=0;i<300;i++ {
  a:=actions[r.Intn(len(actions))]
  id:="rnd"+toID(i)
  c:=cmd(id,a,m.Snapshot().Revision,m.Snapshot().Epoch)
  if a==Configure{c.ConfigDigest=Digest([]byte("new"))}
  v:=m.Apply(c)
  if v.Receipt.Revision<prevRev{t.Fatalf("non-monotonic revision at %d",i)}
  prevRev=v.Receipt.Revision
  if v.Receipt.State==StopPending||v.Receipt.State==Stopped{wasStopped=true}
  if wasStopped&&v.Receipt.State==Active{t.Fatalf("STOP resurrection at %d",i)}
 }
 if _,err:=NewMachine("a/b","target");err==nil{t.Fatal("unvalidated ID")}
}
func toID(n int)string{
 if n==0{return "0"}
 var b [20]byte;i:=len(b)
 for n>0{i--;b[i]=byte('0'+n%10);n/=10}
 return string(b[i:])
}
func TestLedgerFullFailsClosed(t *testing.T){
 m:=setup(t)
 for i:=0;i<maxRemembered;i++ {
  m.Apply(cmd("unique"+toID(i),Close,0,0))
 }
 r:=m.Apply(cmd("overflow",Stop,0,0))
 if r.Receipt.Status!="bounded_history_full"||r.Receipt.State!=New{
  t.Fatalf("silent dedupe eviction or effect: %+v",r)
 }
}
