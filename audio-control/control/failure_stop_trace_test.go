package control

import (
 "reflect"
 "testing"
)

// A failure requests STOP but does not prove the output has stopped. The
// machine must retain a state from which STOP can be reasserted and a verified
// HostStopped can be consumed before Close is allowed.
func TestFailureRequiresObservedStopBeforeClose(t *testing.T) {
 m:=setup(t);configure(t,m);start(t,m)
 if got:=apply(m,cmd("host-start-failed-test",HostStarted,0,1));got.Receipt.State!=Active {
  t.Fatalf("start observation: %+v",got)
 }
 failed:=apply(m,cmd("host-failed",HostFailed,0,1))
 if failed.Receipt.State!=Failed||len(failed.Dispatch)!=1||failed.Dispatch[0].Kind!="host_stop_now" {
  t.Fatalf("host failure should retain its reason and request STOP: %+v",failed)
 }
 stop:=apply(m,cmd("stop-after-failure",Stop,0,0))
 if stop.Receipt.State==Closed||stop.Receipt.State==Failed||len(stop.Dispatch)!=1||stop.Dispatch[0].Kind!="host_stop_now" {
  t.Fatalf("STOP after failure must reassert physical stop while unconfirmed: %+v",stop)
 }
 earlyClose:=apply(m,cmd("close-before-stop-observed",Close,m.Snapshot().Revision,0))
 if earlyClose.Receipt.State==Closed {
  t.Fatalf("closed without host stop observation: %+v",earlyClose)
 }
 // Matching STOP observation remains admissible after host failure.
 ended:=apply(m,cmd("host-stopped-after-failure",HostStopped,0,1))
 if ended.Receipt.State!=Stopped {
  t.Fatalf("verified STOP did not reconcile host failure: %+v",ended)
 }
 closed:=apply(m,cmd("close-after-stop-observed",Close,m.Snapshot().Revision,0))
 if closed.Receipt.State!=Closed { t.Fatalf("close after observed STOP: %+v",closed) }
 // Saturation must still permit a fresh emergency stop effect and its host
 // acknowledgment; the same operation ID remains replay-suppressed.
}

// A fault receipt must remain immutable through replay while an independently
// issued STOP is allowed to converge the physical output state.
func TestFailureReplayDoesNotSuppressLaterEmergencyStop(t *testing.T) {
 m:=setup(t);configure(t,m);start(t,m)
 apply(m,cmd("host-start-failure-replay",HostStarted,0,1))
 failedCmd:=cmd("host-failure-replayed",HostFailed,0,1)
 first:=apply(m,failedCmd)
 replay:=apply(m,failedCmd)
 if !replay.Replayed||!reflect.DeepEqual(first.Receipt,replay.Receipt)||len(replay.Dispatch)!=0 {
  t.Fatalf("failure replay changed receipt or redispatched: first=%+v replay=%+v",first,replay)
 }
 stop:=apply(m,cmd("emergency-stop-after-failure",Stop,0,0))
 if len(stop.Dispatch)!=1||stop.Dispatch[0].Kind!="host_stop_now" {
  t.Fatalf("fresh STOP was suppressed by failure state: %+v",stop)
 }
}
