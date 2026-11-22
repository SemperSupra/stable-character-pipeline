package hostadmission

import (
 "errors"
 "testing"
)

// A late START after a confirmed STOP creates a new STOP generation. The old
// STOP acknowledgement is stale and cannot restore the observed-stopped phase.
func TestLateStartRequiresFreshStopGeneration(t *testing.T) {
 v:=&fakeVerifier{grant:true,observed:true,epoch:31}
 g,_:=New(v)
 start,err:=g.RequestStart(request());if err!=nil { t.Fatal(err) }
 if _,err=g.Observe(obs("started",start.Binding));err!=nil { t.Fatal(err) }
 firstStop:=g.Stop()
 if firstStop.Kind!="host_stop"||firstStop.StopGeneration==0 { t.Fatalf("missing initial stop generation: %+v",firstStop) }
 if _,err=g.Observe(Observation{Kind:"stopped",SessionID:start.Binding.SessionID,TargetID:start.Binding.TargetID,HostDeviceID:start.Binding.HostDeviceID,LeaseID:start.Binding.LeaseID,Epoch:start.Binding.Epoch,StopGeneration:firstStop.StopGeneration});err!=nil||g.Phase()!=Stopped { t.Fatalf("initial stop ack: phase=%s err=%v",g.Phase(),err) }

 corrective,err:=g.Observe(obs("started",start.Binding))
 if err!=nil||g.Phase()!=StopPending||len(corrective)!=1||corrective[0].StopGeneration<=firstStop.StopGeneration { t.Fatalf("late START did not require a new stop: phase=%s effects=%+v err=%v",g.Phase(),corrective,err) }
 stale:=Observation{Kind:"stopped",SessionID:start.Binding.SessionID,TargetID:start.Binding.TargetID,HostDeviceID:start.Binding.HostDeviceID,LeaseID:start.Binding.LeaseID,Epoch:start.Binding.Epoch,StopGeneration:firstStop.StopGeneration}
 if _,err=g.Observe(stale);!errors.Is(err,ErrUnverified)||g.Phase()!=StopPending { t.Fatalf("stale pre-correction stop ack accepted: phase=%s err=%v",g.Phase(),err) }
 fresh:=stale;fresh.StopGeneration=corrective[0].StopGeneration
 if _,err=g.Observe(fresh);err!=nil||g.Phase()!=Stopped { t.Fatalf("fresh correction ack rejected: phase=%s err=%v",g.Phase(),err) }
}
