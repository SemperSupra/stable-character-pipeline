package control

import "testing"

// Caller-owned outcomes must never expose the stored original receipt slices.
func TestReceiptEffectsAndDispatchHaveIndependentOwnership(t *testing.T) {
 for _, mutate := range []string{"initial_dispatch", "initial_receipt", "replayed_receipt"} {
  t.Run(mutate, func(t *testing.T) {
   m := setup(t)
   configure(t, m)
   c := cmd("ownership-start", RequestStart, 1, 0)
   first := m.Submit(c)
   if len(first.Dispatch) != 1 || len(first.Receipt.Effects) != 1 { t.Fatal("missing initial effect") }
   if mutate == "initial_dispatch" {
    first.Dispatch[0] = Effect{Kind:"caller-corruption", Epoch:999}
    if first.Receipt.Effects[0].Kind != "host_authorize_then_start" || first.Receipt.Effects[0].Epoch != 1 {
     t.Error("dispatch mutation changed the separately returned receipt")
    }
   }
   if mutate == "initial_receipt" { first.Receipt.Effects[0] = Effect{Kind:"caller-corruption", Epoch:999} }
   replay := m.Submit(c)
   if !replay.Replayed || len(replay.Dispatch) != 0 { t.Fatal("replay redispatched") }
   if len(replay.Receipt.Effects) != 1 || replay.Receipt.Effects[0] != (Effect{Kind:"host_authorize_then_start", Epoch:1}) {
    t.Fatal("caller mutation corrupted stored original receipt")
   }
   if mutate == "replayed_receipt" { replay.Receipt.Effects[0] = Effect{Kind:"caller-corruption", Epoch:999} }
   again := m.Submit(c)
   if !again.Replayed || len(again.Dispatch) != 0 || len(again.Receipt.Effects) != 1 ||
    again.Receipt.Effects[0] != (Effect{Kind:"host_authorize_then_start", Epoch:1}) {
    t.Fatal("replayed receipt mutation corrupted ledger or redispatched")
   }
   if m.Snapshot().State != StartPending || m.Snapshot().Epoch != 1 || m.Snapshot().Revision != 2 {
    t.Fatal("outcome mutation changed machine state")
   }
  })
 }
}
