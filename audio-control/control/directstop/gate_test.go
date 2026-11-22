package directstop

import (
 "sync"
 "testing"
 "time"
)

func TestStopBeforeStartRejectsLateStart(t *testing.T){
 g:=New()
 if !g.StopDirect()||g.RequestStart()||g.ObserveHostStarted(){t.Fatal("late start bypassed stop")}
 if g.Phase()!=StopPending||g.RenderSimulatedSample(.7)!=0{
  t.Fatal("stop did not fence render permit")
 }
 if !g.ObserveHostStopped()||g.Phase()!=StopObserved{t.Fatal("mock observation failed")}
 if g.RequestStart()||g.RenderSimulatedSample(.5)!=0{t.Fatal("observed STOP resurrected")}
}
func TestStartThenStopMutesFurtherSyntheticRenders(t *testing.T){
 g:=New()
 if !g.RequestStart()||g.RenderSimulatedSample(.5)!=0{t.Fatal("start intent sounded before host")}
 if !g.ObserveHostStarted()||g.RenderSimulatedSample(.5)!=.5{t.Fatal("mock host activation failed")}
 if !g.StopDirect()||g.Phase()!=StopPending{t.Fatal("direct stop failed")}
 for i:=0;i<5000;i++{if g.RenderSimulatedSample(.5)!=0{t.Fatal("render after STOP was not zero")}}
 if g.ObserveHostStarted(){t.Fatal("late START re-enabled render after stop")}
 if !g.ObserveHostStopped()||g.Phase()!=StopObserved{t.Fatal("no observed stop")}
}
func TestBlockedPersistenceCannotBlockDirectStop(t *testing.T){
 g:=New()
 if !g.RequestStart()||!g.ObserveHostStarted(){t.Fatal("setup")}
 writerLocked:=make(chan struct{})
 releaseWriter:=make(chan struct{})
 var writer sync.WaitGroup
 writer.Add(1)
 go func(){defer writer.Done();close(writerLocked);<-releaseWriter}()
 <-writerLocked // Synthetic DB/durable outbox is unavailable.
 stopped:=make(chan struct{})
 go func(){g.StopDirect();close(stopped)}()
 select{
 case <-stopped:
 case <-time.After(2*time.Second):
  close(releaseWriter);writer.Wait()
  t.Fatal("direct STOP blocked on persistence worker")
 }
 if g.RenderSimulatedSample(.6)!=0||g.Phase()!=StopPending{
  t.Fatal("storage-independent STOP did not fence synthetic output")
 }
 close(releaseWriter);writer.Wait()
}
func TestConcurrentStartObservationCannotResurrectAfterStop(t *testing.T){
 for rep:=0;rep<300;rep++{
  g:=New()
  if !g.RequestStart(){t.Fatal("setup")}
  var wg sync.WaitGroup
  wg.Add(2)
  go func(){defer wg.Done();g.ObserveHostStarted()}()
  go func(){defer wg.Done();g.StopDirect()}()
  wg.Wait()
  if g.Phase()!=StopPending||g.RenderSimulatedSample(.5)!=0{
   t.Fatalf("rep=%d concurrent start resurrected render",rep)
  }
 }
}
func TestNoJournalOrHostStopProofIsImplied(t *testing.T){
 g:=New()
 g.StopDirect()
 if g.Phase()==StopObserved{t.Fatal("STOP request fabricated verified device silence")}
 if !g.ObserveHostStopped(){t.Fatal("synthetic callback missing")}
}
