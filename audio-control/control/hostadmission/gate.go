// Package hostadmission is a NO-DEVICE proof of host-side authorization and
// epoch-fenced observations. It is not an OS authentication implementation,
// network endpoint, real-time callback, or physical STOP guarantee.
package hostadmission

import (
 "errors"
 "fmt"
)
type Phase string
const (
 Idle Phase="idle"
 StartPending Phase="start_pending"
 Active Phase="active"
 StopPending Phase="stop_pending"
 Stopped Phase="stopped"
 Unknown Phase="unknown"
)
type Request struct {
 PrincipalID string
 SessionID string
 TargetID string
 OperationID string
}
type Binding struct {
 PrincipalID string
 SessionID string
 TargetID string
 HostDeviceID string
 LeaseID string
 Epoch uint64
}
type Observation struct {
 Kind string // started, stopped, failed
 SessionID string
 TargetID string
 HostDeviceID string
 LeaseID string
 Epoch uint64
}
type EffectIntent struct {
 Kind string // host_start, host_stop, discover_then_stop
 Binding Binding
}
var ErrUnverified=errors.New("hostadmission: host authorization/observation rejected")
var ErrConflict=errors.New("hostadmission: invalid lifecycle transition")
var ErrInvalid=errors.New("hostadmission: missing identity/epoch")
type Verifier interface{
 // A real adapter derives authority from a trusted OS user gesture/permission
 // and device registry, never from client JSON fields or agent speech.
 AuthorizeLocalHuman(Request)(Binding,error)
 // A real adapter must validate OS origin/lease/epoch, not mere string equality.
 VerifyHostObservation(Observation,Binding)bool
}
type Gate struct{
 verify Verifier
 phase Phase
 binding Binding
}
func New(v Verifier)(*Gate,error){
 if v==nil{return nil,ErrInvalid}
 return &Gate{verify:v,phase:Idle},nil
}
func (g *Gate)Phase()Phase {if g==nil{return Unknown};return g.phase}
func valid(b Binding)bool{
 return b.PrincipalID!=""&&b.SessionID!=""&&b.TargetID!=""&&
  b.HostDeviceID!=""&&b.LeaseID!=""&&b.Epoch>0
}
// RequestStart is called only after the R0 command reducer accepts the
// intent; this adapter independently checks local human/device authority.
func (g *Gate)RequestStart(r Request)(EffectIntent,error){
 if g==nil||g.verify==nil{return EffectIntent{},ErrInvalid}
 if g.phase!=Idle{return EffectIntent{},ErrConflict}
 b,e:=g.verify.AuthorizeLocalHuman(r)
 if e!=nil{return EffectIntent{},fmt.Errorf("%w: %v",ErrUnverified,e)}
 if !valid(b)||b.PrincipalID!=r.PrincipalID||b.SessionID!=r.SessionID||
  b.TargetID!=r.TargetID{return EffectIntent{},ErrUnverified}
 g.binding=b;g.phase=StartPending
 return EffectIntent{Kind:"host_start",Binding:b},nil
}
func matches(e Observation,b Binding)bool{
 return e.SessionID==b.SessionID&&e.TargetID==b.TargetID&&
  e.HostDeviceID==b.HostDeviceID&&e.LeaseID==b.LeaseID&&e.Epoch==b.Epoch
}
// Observe consumes a *verified* OS-side event. The verifier is injection-only;
// tests have no real host, so they cannot prove physical audio outcomes.
func (g *Gate)Observe(e Observation)([]EffectIntent,error){
 if g==nil||g.verify==nil||!valid(g.binding){return nil,ErrInvalid}
 if !matches(e,g.binding)||!g.verify.VerifyHostObservation(e,g.binding){return nil,ErrUnverified}
 switch e.Kind{
 case "started":
  switch g.phase{
  case StartPending:g.phase=Active;return nil,nil
  case StopPending,Unknown:
   return []EffectIntent{{Kind:"host_stop",Binding:g.binding}},nil
  default:return nil,ErrConflict
  }
 case "stopped","failed":
  if g.phase==StartPending||g.phase==Active||g.phase==StopPending||g.phase==Unknown{
   g.phase=Stopped;return nil,nil
  }
  return nil,ErrConflict
 default:return nil,ErrUnverified
 }
}
// Stop never fabricates a verified stopped state: it only requests a host
// effect. With no authenticated binding, it reports discovery as the next
// required action instead of silently treating STOP as physical success.
func (g *Gate)Stop()EffectIntent{
 if g==nil||!valid(g.binding){
  return EffectIntent{Kind:"discover_then_stop"}
 }
 if g.phase!=Stopped{g.phase=StopPending}
 return EffectIntent{Kind:"host_stop",Binding:g.binding}
}
// RecoverUnknown is called only after a separately verified durable binding
// is restored by the host. A JSON claim from an agent must not invoke this.
func (g *Gate)RecoverUnknown(b Binding)error{
 if g==nil||!valid(b)||g.phase!=Idle{return ErrInvalid}
 g.binding=b;g.phase=Unknown
 return nil
}
