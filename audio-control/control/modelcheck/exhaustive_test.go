// Package modelcheck is a bounded, executable exhaustive transition witness
// against the actual R0 Go reducer. It never touches a media device, network,
// disk journal or user recording. 8^5 sequences cover five logical events.
package modelcheck

import (
 "fmt"
 "reflect"
 "testing"

 control "github.com/SemperSupra/stable-character-pipeline/audio-control/control"
)

var actions = []control.Action{
 control.Configure, control.RequestStart, control.Stop, control.Close,
 control.HostStarted, control.HostStopped, control.HostCompleted, control.HostFailed,
}

func isHost(a control.Action) bool {
 return a == control.HostStarted || a == control.HostStopped ||
  a == control.HostCompleted || a == control.HostFailed
}

func trial(t *testing.T, index int) (string, bool, bool) {
 t.Helper()
 m, err := control.NewMachine("synthetic_session", "synthetic_target")
 if err != nil { t.Fatal(err) }
 var stoppedByCommand, visitedPending bool
 seq := index
 for step:=0;step<5;step++ {
  a:=actions[seq%len(actions)]
  seq/=len(actions)
  before:=m.Snapshot()
  command:=control.Command{
   SchemaVersion:control.ProtocolVersion,
   PrincipalID:"bounded_model",
   SessionID:"synthetic_session",
   TargetID:"synthetic_target",
   OperationID:fmt.Sprintf("seq_%d_step_%d",index,step),
   Action:a,ExpectedRevision:before.Revision,Epoch:before.Epoch,
  }
  if a==control.Configure {command.ConfigDigest=control.Digest([]byte("original synthetic plan"))}
  var outcome control.Outcome
  if isHost(a) {
   rejected:=m.Submit(command)
   if rejected.Receipt.Status!="host_observation_requires_trusted_adapter" ||
    rejected.Receipt.State!=before.State || rejected.Receipt.Revision!=before.Revision {
    t.Fatalf("seq %d step %d forged host event crossed client ingress: %+v",index,step,rejected)
   }
   outcome=m.ObserveHost(command)
  }else{
   outcome=m.Submit(command)
  }
  after:=m.Snapshot()
  if after.Revision<before.Revision || after.Epoch<before.Epoch {
   t.Fatalf("seq %d step %d revision or epoch regressed: %+v -> %+v",index,step,before,after)
  }
  if stoppedByCommand && after.State==control.Active {
   t.Fatalf("seq %d step %d STOP resurrection: %+v",index,step,after)
  }
  if a==control.Stop && outcome.Receipt.Status=="accepted" {stoppedByCommand=true}
  if after.State==control.StopPending{visitedPending=true}
  if a==control.RequestStart && outcome.Receipt.Status=="accepted" {
   if len(outcome.Dispatch)!=1||outcome.Dispatch[0].Kind!="host_authorize_then_start"{
    t.Fatalf("seq %d step %d accepted START missing guarded intent",index,step)
   }
   if after.State!=control.StartPending{t.Fatalf("seq %d START claimed active prematurely",index)}
  }
  if a==control.HostStarted && before.State==control.StopPending {
   if after.State!=control.StopPending || len(outcome.Dispatch)!=1 ||
    outcome.Dispatch[0].Kind!="host_stop_now" {
    t.Fatalf("seq %d late START bypassed prior STOP",index)
   }
  }
  // Exact caller replay cannot dispatch another effect, must return a
  // value-equivalent original receipt on this bounded in-memory trace.
  var repeat control.Outcome
  if isHost(a){repeat=m.ObserveHost(command)}else{repeat=m.Submit(command)}
  if !repeat.Replayed || len(repeat.Dispatch)!=0 ||
   !reflect.DeepEqual(repeat.Receipt,outcome.Receipt) {
   t.Fatalf("seq %d step %d replay mutated original receipt/effect: %+v",index,step,repeat)
  }
 }
 return string(m.Snapshot().State),stoppedByCommand,visitedPending
}

func TestBoundedExhaustiveFiveEventTraces(t *testing.T){
 const depth=5
 total:=1
 for k:=0;k<depth;k++{total*=len(actions)}
 reached:=map[string]int{}
 stoppedCount,pendingCount:=0,0
 for i:=0;i<total;i++ {
  state,stopped,pending:=trial(t,i)
  reached[state]++
  if stopped{stoppedCount++}
  if pending{pendingCount++}
 }
 if total!=32768||stoppedCount==0||pendingCount==0 ||
  reached[string(control.Active)]==0||reached[string(control.StopPending)]==0||
  reached[string(control.Stopped)]==0||reached[string(control.Completed)]==0 {
  t.Fatalf("insufficient state exploration: total=%d stopped=%d pending=%d reached=%v",
   total,stoppedCount,pendingCount,reached)
 }
 t.Logf("PASS actual R0 reducer %d complete five-event sequences; STOP traces=%d; pending=%d; states=%v",
  total,stoppedCount,pendingCount,reached)
}
