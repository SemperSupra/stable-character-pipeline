package control

import (
 "fmt"
 "math/rand"
 "reflect"
 "testing"
)

// Seeded reproducible interleavings are deliberately independent of the
// existing hand-authored state tests. They do not touch an audio host.
func runAdversarialTrace(t *testing.T, seed int64, steps int) {
 t.Helper()
 m,e:=NewMachine("synthetic.session","synthetic.target")
 if e!=nil{t.Fatal(e)}
 rng:=rand.New(rand.NewSource(seed))
 actions:=[]Action{Configure,RequestStart,Stop,Close,HostStarted,HostStopped,HostCompleted,HostFailed}
 stoppedOrStopping:=false
 var prior uint64
 for i:=0;i<steps;i++ {
  a:=actions[rng.Intn(len(actions))]
  snapshot:=m.Snapshot()
  cmd:=Command{SchemaVersion:ProtocolVersion,PrincipalID:"test.agent",SessionID:"synthetic.session",TargetID:"synthetic.target",OperationID:fmt.Sprintf("op_%d",i),Action:a,ExpectedRevision:snapshot.Revision,Epoch:snapshot.Epoch}
  if a==Configure{cmd.ConfigDigest=Digest([]byte("fixed-public-synthetic-plan"))}
  var actual Outcome
  if isHostEvent(a){
   // A hostile caller must never cross the host-event boundary.
   denied:=m.Submit(cmd)
   if denied.Receipt.Status!="host_observation_requires_trusted_adapter"||
    denied.Receipt.Revision!=snapshot.Revision {t.Fatalf("seed=%d step=%d forged host observation",seed,i)}
   actual=m.ObserveHost(cmd)
  }else{actual=m.Submit(cmd)}
  got:=m.Snapshot()
  if got.Revision<prior {t.Fatalf("seed=%d step=%d revision regressed",seed,i)}
  prior=got.Revision
  if got.State==StopPending||got.State==Stopped{stoppedOrStopping=true}
  if stoppedOrStopping&&got.State==Active {t.Fatalf("seed=%d step=%d sound resurrected after STOP",seed,i)}
  if got.State==Active&&snapshot.State!=StartPending&&snapshot.State!=Active{
   t.Fatalf("seed=%d step=%d unacknowledged active transition",seed,i)
  }
  if actual.Receipt.Status=="accepted"&&a==RequestStart {
   if len(actual.Dispatch)!=1||actual.Dispatch[0].Kind!="host_authorize_then_start"{
    t.Fatalf("seed=%d step=%d missing start authorization effect",seed,i)
   }
  }
  if i%19==0 {
   replay:=m.Submit(cmd)
   if isHostEvent(a){
    if replay.Receipt.Status!="host_observation_requires_trusted_adapter"{t.Fatal("host ingress replay bypass")}
   }else if actual.Receipt.Status!="bounded_history_full"&&actual.Receipt.Status!="emergency_untracked"{
    if !replay.Replayed||len(replay.Dispatch)!=0||!reflect.DeepEqual(replay.Receipt,actual.Receipt){
     t.Fatalf("seed=%d step=%d duplicate id redispatched",seed,i)
    }
   }
  }
 }
}
func TestParallelAdversarialSeeds(t *testing.T){
 for _,seed:=range []int64{1,7,17,42,20261122,0x5eed} {
  seed:=seed
  t.Run(fmt.Sprintf("trace_%d",seed),func(t *testing.T){t.Parallel();runAdversarialTrace(t,seed,256)})
 }
}
func FuzzAudioControlTrace(f *testing.F){
 for _,raw:=range [][]byte{{0},{1,2,3,4,5,6,7},{2,2,2,3,4,4,1},{255,0,127,1,3,8,11}}{f.Add(raw)}
 f.Fuzz(func(t *testing.T, raw []byte){
  if len(raw)>256{raw=raw[:256]}
  m,_:=NewMachine("fuzz.session","fuzz.target")
  stopObserved:=false
  actions:=[]Action{Configure,RequestStart,Stop,Close,HostStarted,HostStopped,HostCompleted,HostFailed}
  for i,b:=range raw{
   a:=actions[int(b)%len(actions)]
   s:=m.Snapshot()
   cmd:=Command{SchemaVersion:ProtocolVersion,PrincipalID:"fuzzer",SessionID:"fuzz.session",TargetID:"fuzz.target",OperationID:fmt.Sprintf("item_%d",i),Action:a,ExpectedRevision:s.Revision,Epoch:s.Epoch}
   if a==Configure{cmd.ConfigDigest=Digest([]byte("synthetic"))}
   if isHostEvent(a){m.ObserveHost(cmd)}else{m.Submit(cmd)}
   state:=m.Snapshot().State
   if state==StopPending||state==Stopped{stopObserved=true}
   if stopObserved&&state==Active{t.Fatalf("resurrection after STOP at byte %d",i)}
  }
 })
}
