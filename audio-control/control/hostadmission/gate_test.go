package hostadmission

import (
 "errors"
 "testing"
)
type fakeVerifier struct {
 grant bool
 observed bool
 epoch uint64
}
func (f *fakeVerifier)AuthorizeLocalHuman(r Request)(Binding,error){
 if !f.grant{return Binding{},errors.New("no local human consent")}
 return Binding{PrincipalID:r.PrincipalID,SessionID:r.SessionID,TargetID:r.TargetID,
  HostDeviceID:"mock_os_device",LeaseID:"mock_lease",Epoch:f.epoch},nil
}
func (f *fakeVerifier)VerifyHostObservation(e Observation,b Binding)bool {
 return f.observed
}
func request()Request {
 return Request{PrincipalID:"authorized_human",SessionID:"session_1",
  TargetID:"selected_headphones",OperationID:"gesture_1"}
}
func obs(kind string,b Binding)Observation{
 return Observation{Kind:kind,SessionID:b.SessionID,TargetID:b.TargetID,
 HostDeviceID:b.HostDeviceID,LeaseID:b.LeaseID,Epoch:b.Epoch}
}
func TestHumanGrantIsRequired(t *testing.T){
 f:=&fakeVerifier{grant:false,observed:true,epoch:1}
 g,_:=New(f)
 if _,e:=g.RequestStart(request());!errors.Is(e,ErrUnverified){t.Fatalf("unauthorized start: %v",e)}
 if g.Phase()!=Idle{t.Fatal("reject changed lifecycle")}
 if stop:=g.Stop();stop.Kind!="discover_then_stop"{t.Fatalf("unknown host STOP fabricated success: %+v",stop)}
}
func TestStopPreemptsDelayedStartAndRequiresHostStop(t *testing.T){
 f:=&fakeVerifier{grant:true,observed:true,epoch:42}
 g,_:=New(f)
 start,e:=g.RequestStart(request());if e!=nil||start.Kind!="host_start"||g.Phase()!=StartPending{t.Fatalf("start intent: %v %+v",e,start)}
 if _,e:=g.RequestStart(request());!errors.Is(e,ErrConflict){t.Fatal("duplicate start was admitted")}
 stop:=g.Stop()
 if stop.Kind!="host_stop"||g.Phase()!=StopPending{t.Fatalf("stop did not preempt: %+v",stop)}
 late,e:=g.Observe(obs("started",start.Binding))
 if e!=nil||g.Phase()!=StopPending||len(late)!=1||late[0].Kind!="host_stop"{
  t.Fatalf("late START revived audio or lacked corrective STOP: %+v %v",late,e)
 }
 ack:=obs("stopped",start.Binding);ack.StopGeneration=late[0].StopGeneration
 if _,e:=g.Observe(ack);e!=nil||g.Phase()!=Stopped{
  t.Fatalf("physical STOP acknowledgment not observed: %v",e)
 }
 if again:=g.Stop();again.Kind!="host_stop"||g.Phase()!=Stopped{
  t.Fatal("repeated STOP lost convergent intent")
 }
}
func TestForgedHostAndMismatchedLeaseRejected(t *testing.T){
 f:=&fakeVerifier{grant:true,observed:false,epoch:77}
 g,_:=New(f)
 start,e:=g.RequestStart(request());if e!=nil{t.Fatal(e)}
 if _,e:=g.Observe(obs("started",start.Binding));!errors.Is(e,ErrUnverified)||g.Phase()!=StartPending{
  t.Fatalf("caller-provided host event admitted: %v",e)
 }
 f.observed=true
 wrong:=obs("started",start.Binding);wrong.Epoch=76
 if _,e:=g.Observe(wrong);!errors.Is(e,ErrUnverified){t.Fatalf("stale epoch admitted: %v",e)}
 wrong=obs("started",start.Binding);wrong.TargetID="other_headphones"
 if _,e:=g.Observe(wrong);!errors.Is(e,ErrUnverified){t.Fatalf("other device admitted: %v",e)}
 wrong=obs("started",start.Binding);wrong.LeaseID="expired_other_lease"
 if _,e:=g.Observe(wrong);!errors.Is(e,ErrUnverified){t.Fatalf("other lease admitted: %v",e)}
 if _,e:=g.Observe(obs("started",start.Binding));e!=nil||g.Phase()!=Active{
  t.Fatalf("genuine host ACK failed: %v",e)
 }
}
func TestCrashRecoverUnknownRequestsActualHostStop(t *testing.T){
 v:=&fakeVerifier{grant:true,observed:true,epoch:13}
 original,_:=New(v);start,e:=original.RequestStart(request());if e!=nil{t.Fatal(e)}
 recovered,_:=New(v)
 if recovered.Stop().Kind!="discover_then_stop"{t.Fatal("unbound crash recovery falsely claimed device stop")}
 // The example binding comes from a fake test verifier, NOT a real OS proof.
 if e:=recovered.RecoverUnknown(start.Binding);e!=nil{t.Fatal(e)}
 if recovered.Phase()!=Unknown{t.Fatal("unknown physical state fabricated active/stopped")}
 effect:=recovered.Stop()
 if effect.Kind!="host_stop"||effect.Binding.Epoch!=13||recovered.Phase()!=StopPending{
  t.Fatalf("recovery STOP not emitted: %+v",effect)
 }
 ack:=obs("stopped",start.Binding);ack.StopGeneration=effect.StopGeneration
 if _,e:=recovered.Observe(ack);e!=nil||recovered.Phase()!=Stopped{
  t.Fatalf("recovery physical observation failed: %v",e)
 }
}
func TestRecoveredUnknownRequiresExactNonzeroStopGeneration(t *testing.T){
 v:=&fakeVerifier{grant:true,observed:true,epoch:13}
 g,_:=New(v)
 b:=Binding{PrincipalID:"authorized_human",SessionID:"session_1",TargetID:"selected_headphones",HostDeviceID:"mock_os_device",LeaseID:"lease_1",Epoch:13,StopGeneration:7}
 if e:=g.RecoverUnknown(b);e!=nil{t.Fatal(e)}
 for _,generation:=range []uint64{0,6,8}{
  ack:=obs("stopped",b);ack.StopGeneration=generation
  if _,e:=g.Observe(ack);!errors.Is(e,ErrUnverified)||g.Phase()!=Unknown{t.Fatalf("recovered gate accepted generation %d: %v phase=%s",generation,e,g.Phase())}
 }
 ack:=obs("stopped",b);ack.StopGeneration=7
 if _,e:=g.Observe(ack);e!=nil||g.Phase()!=Stopped{t.Fatalf("matching recovered generation rejected: %v phase=%s",e,g.Phase())}
}
func TestStopGenerationOverflowFailsClosedUntilNewLease(t *testing.T){
 v:=&fakeVerifier{grant:true,observed:true,epoch:13}
 g,_:=New(v)
 b:=Binding{PrincipalID:"authorized_human",SessionID:"session_1",TargetID:"selected_headphones",HostDeviceID:"mock_os_device",LeaseID:"lease_1",Epoch:13,StopGeneration:^uint64(0)}
 if e:=g.RecoverUnknown(b);e!=nil{t.Fatal(e)}
 effect:=g.Stop()
 if effect.Kind!="discover_then_stop"||g.Phase()!=Unknown{t.Fatalf("overflow did not fail closed: %+v phase=%s",effect,g.Phase())}
 ack:=obs("stopped",b);ack.StopGeneration:^uint64(0)
 if _,e:=g.Observe(ack);!errors.Is(e,ErrUnverified)||g.Phase()!=Unknown{t.Fatalf("exhausted generation accepted stale ACK: %v phase=%s",e,g.Phase())}
 recovered:=b;recovered.LeaseID="lease_2";recovered.StopGeneration=0
 recoveredGate,_:=New(v)
 if e:=recoveredGate.RecoverUnknown(recovered);e!=nil{t.Fatalf("new lease could not restore reconciliation: %v",e)}
 stale:=obs("stopped",recovered)
 if _,e:=recoveredGate.Observe(stale);!errors.Is(e,ErrUnverified){t.Fatalf("zero generation accepted after new lease: %v",e)}
 next:=recoveredGate.Stop()
 if next.Kind!="host_stop"||next.StopGeneration!=1{t.Fatalf("new lease did not start fresh generation: %+v",next)}
}
func TestHostGrantBindingCannotOverrideSelectedTarget(t *testing.T){
 f:=&fakeVerifier{grant:true,observed:true,epoch:1}
 g,_:=New(f)
 bad:=request();bad.TargetID="selection_mismatch"
 b,e:=g.RequestStart(bad);if e!=nil||b.Binding.TargetID!="selection_mismatch"{t.Fatalf("wrong synthetic baseline: %v",e)}
 // In actual OS, a verifier must derive the permitted target independent of
 // caller fields. This mock does not, and cannot be deployed as security.
 t.Log("LIMITATION: mock verifier mirrors caller target, no OS permission proof")
}
