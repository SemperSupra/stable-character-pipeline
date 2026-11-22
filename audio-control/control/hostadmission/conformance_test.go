package hostadmission

import (
 "errors"
 "testing"
)

// These are fake-host lifecycle proofs only, never physical silence evidence.
func TestLateStartedAfterConfirmedStopReassertsStop(t *testing.T) {
 v := &fakeVerifier{grant:true, observed:true, epoch:5}
 g, _ := New(v)
 start, err := g.RequestStart(request())
 if err != nil { t.Fatal(err) }
 g.Stop()
 if _, err := g.Observe(obs("stopped", start.Binding)); err != nil { t.Fatal(err) }
 effects, err := g.Observe(obs("started", start.Binding))
 if err != nil || g.Phase() != Stopped || len(effects) != 1 ||
  effects[0].Kind != "host_stop" || effects[0].Binding != start.Binding {
  t.Fatalf("late verified START after STOP lacked corrective stop: phase=%s effects=%+v err=%v", g.Phase(), effects, err)
 }
}

func TestVerifiedFailureCannotClaimConfirmedSilence(t *testing.T) {
 v := &fakeVerifier{grant:true, observed:true, epoch:6}
 g, _ := New(v)
 start, err := g.RequestStart(request())
 if err != nil { t.Fatal(err) }
 if _, err := g.Observe(obs("started", start.Binding)); err != nil { t.Fatal(err) }
 effects, err := g.Observe(obs("failed", start.Binding))
 if err != nil || g.Phase() != StopPending || len(effects) != 1 ||
  effects[0].Kind != "host_stop" || effects[0].Binding != start.Binding {
  t.Fatalf("failure fabricated silence or lost stop: phase=%s effects=%+v err=%v", g.Phase(), effects, err)
 }
 if _, err := g.Observe(obs("stopped", start.Binding)); err != nil || g.Phase() != Stopped {
  t.Fatalf("verified stopped did not complete failure recovery: %v", err)
 }
}

func TestUnboundStopLatchesBeforeConsentAndAllowsTrustedRecovery(t *testing.T) {
 v := &fakeVerifier{grant:true, observed:true, epoch:7}
 g, _ := New(v)
 if effect := g.Stop(); effect.Kind != "discover_then_stop" || g.Phase() != Unknown {
  t.Fatalf("unbound stop did not latch unknown state: phase=%s effect=%+v", g.Phase(), effect)
 }
 if _, err := g.RequestStart(request()); !errors.Is(err, ErrConflict) {
  t.Fatalf("start admitted after latched unbound stop: %v", err)
 }
 // Binding restoration is a trusted-host-only precondition in this test double.
 binding, err := v.AuthorizeLocalHuman(request())
 if err != nil { t.Fatal(err) }
 if err := g.RecoverUnknown(binding); err != nil { t.Fatal(err) }
 if effect := g.Stop(); effect.Kind != "host_stop" || effect.Binding != binding || g.Phase() != StopPending {
  t.Fatalf("trusted recovery lost pending STOP: %+v", effect)
 }
 if _, err := g.Observe(obs("stopped", binding)); err != nil || g.Phase() != Stopped {
  t.Fatalf("verified recovery stop failed: %v", err)
 }
 if err := g.RecoverUnknown(binding); !errors.Is(err, ErrInvalid) {
  t.Fatalf("recovery replaced existing terminal binding: %v", err)
 }
}
