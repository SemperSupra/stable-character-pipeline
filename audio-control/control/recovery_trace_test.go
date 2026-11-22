package control

import "testing"

// These are NEGATIVE recovery probes. An R0 in-memory process restart cannot
// prove the previous device state, outbox or exactly-once effects. No real I/O.
func TestCrashAfterAcceptedBeforeHostAcknowledgment(t *testing.T) {
 original:=setup(t); configure(t,original); start(t,original)
 if original.Snapshot().State!=StartPending {t.Fatal("setup not pending")}
 recovered:=setup(t) // Simulate loss of all process-local state on restart.
 if recovered.Snapshot().State!=New || recovered.Snapshot().Epoch!=0 {
  t.Fatal("recovered process fabricated previous observed state")
 }
 late:=recovered.ObserveHost(cmd("late-host",HostStarted,0,1))
 if late.Receipt.Status!="stale_epoch"||recovered.Snapshot().State!=New{
  t.Fatalf("orphan host ACK resurrected audio: %+v",late)
 }
 // Retried old operation is not deduplicated across a crash. The pure
 // reducer cannot safely assert that the device is now silent or running.
 retry:=recovered.Submit(cmd("start",RequestStart,0,0))
 if retry.Receipt.Status=="accepted"||len(retry.Dispatch)!=0 {
  t.Fatalf("unreconciled in-flight START reissued: %+v",retry)
 }
}
func TestCrashAfterPhysicalStartRequiresHostReconciliation(t *testing.T) {
 previous:=setup(t);configure(t,previous);start(t,previous)
 started:=previous.ObserveHost(cmd("host-start",HostStarted,0,1))
 if started.Receipt.State!=Active{t.Fatalf("setup failed: %+v",started)}
 restarted:=setup(t)
 if restarted.Snapshot().State!=New{t.Fatal("crash state should be unknown to fresh process")}
 // Force STOP request must be allowed, but a brand-new in-memory model has
 // no epoch/device lease and DOES NOT issue a host-stop intent here.
 // This is a documented blocking defect for physical adoption, not a proof.
 stop:=restarted.Submit(cmd("emergency-stop",Stop,0,0))
 if stop.Receipt.State!=Stopped{t.Fatalf("emergency command rejected: %+v",stop)}
 if len(stop.Dispatch)!=0 {
  t.Fatal("unexpected host operation from unbound recovery model")
 }
 t.Log("LIMITATION: new process cannot prove physical silence; host re-discovery and outbox replay are mandatory before live adoption")
}
