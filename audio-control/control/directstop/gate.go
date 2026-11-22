// Package directstop is a synthetic, CPU-only demonstration of a bounded,
// storage-independent render gate. No sound driver or physical device exists.
// It does not implement the OS host's mandatory stop/flush acknowledgment.
package directstop

import "sync/atomic"

type Phase uint32
const (
 Idle Phase = iota
 StartPending
 Active
 StopPending
 StopObserved
)

// Gate owns only a simulated per-session render permit. A real audio host
// must own device permissions, buffer cancellation, route and actual silence.
type Gate struct{phase atomic.Uint32}
func New()*Gate{return &Gate{}}
func(g *Gate)Phase()Phase{if g==nil{return StopPending};return Phase(g.phase.Load())}

// RequestStart is an admission *intent*, not permission to open sound output.
func(g *Gate)RequestStart()bool{
 return g!=nil&&g.phase.CompareAndSwap(uint32(Idle),uint32(StartPending))
}

// ObserveHostStarted is called only by a verified adapter; late START
// observations after STOP never re-enable the simulated render permit.
func(g *Gate)ObserveHostStarted()bool{
 return g!=nil&&g.phase.CompareAndSwap(uint32(StartPending),uint32(Active))
}

// StopDirect is deliberately independent of any journal, network, scheduler
// or DB. This in-memory intent cannot by itself stop physical device buffers.
// The immediate return is NOT a device acknowledgment.
func(g *Gate)StopDirect()bool{
 if g==nil{return false}
 for {
  old:=g.phase.Load()
  if Phase(old)==StopPending||Phase(old)==StopObserved{return false}
  if g.phase.CompareAndSwap(old,uint32(StopPending)){return true}
 }
}

// ObserveHostStopped requires an independently verified host callback.
// Unlike StopDirect, this records observed completion in the mock model.
func(g *Gate)ObserveHostStopped()bool{
 return g!=nil&&g.phase.CompareAndSwap(uint32(StopPending),uint32(StopObserved))
}

// RenderSimulatedSample returns zero unless the single atomic gate is active.
// It has no filesystem, lock, GC allocation, JSON or network operation.
// In-flight callback writes and device buffers need separate host silencing.
func(g *Gate)RenderSimulatedSample(sample float32)float32{
 if g==nil||Phase(g.phase.Load())!=Active{return 0}
 return sample
}
