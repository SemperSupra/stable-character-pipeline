// Package control is a synthetic, nonproduction reference reducer for an
// audio-session control contract. It has NO audio device, network, microphone,
// DSP, filesystem or external side effects. Host adapters must authorize effects.
package control

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "strings"
)

type State string
const (
 New State = "new"
 Configured State = "configured"
 StartPending State = "start_pending"
 Active State = "active"
 StopPending State = "stop_pending"
 Stopped State = "stopped"
 Completed State = "completed"
 Failed State = "failed"
 Closed State = "closed"
)
type Action string
const (
 Configure Action = "configure"
 RequestStart Action = "request_start"
 Stop Action = "stop"
 Close Action = "close"
 // These are observations emitted by trusted local host integrations, NOT API commands.
 HostStarted Action = "host_started"
 HostStopped Action = "host_stopped"
 HostCompleted Action = "host_completed"
 HostFailed Action = "host_failed"
)
type Command struct {
 SchemaVersion string `json:"schema_version"`
 PrincipalID string `json:"principal_id"`
 SessionID string `json:"session_id"`
 TargetID string `json:"target_id"`
 OperationID string `json:"operation_id"`
 Action Action `json:"action"`
 ExpectedRevision uint64 `json:"expected_revision"`
 Epoch uint64 `json:"epoch,omitempty"`
 // ConfigDigest is a hex SHA-256 of an independently validated immutable plan.
 ConfigDigest string `json:"config_digest,omitempty"`
}
type Effect struct {
 Kind string `json:"kind"`
 Epoch uint64 `json:"epoch"`
}
type Receipt struct {
 SchemaVersion string `json:"schema_version"`
 Status string `json:"status"`
 State State `json:"state"`
 Revision uint64 `json:"revision"`
 Epoch uint64 `json:"epoch"`
 Effects []Effect `json:"effects,omitempty"`
}
type Outcome struct {
 Receipt Receipt
 Replayed bool
 // An actual adapter may consume Dispatch once; duplicates return no dispatch.
 // Production requires durable outbox and effect reconciliation before use.
 Dispatch []Effect
}
type entry struct {cmd Command; receipt Receipt}
type Machine struct {
 sessionID,targetID string
 state State
 revision,epoch uint64
 configDigest string
 seen map[string]entry
}
const (
 maxRemembered = 512
 ProtocolVersion = "audio_control.r0"
 ReceiptVersion = "audio_control.receipt.r0"
)

func NewMachine(sessionID,targetID string)(*Machine,error){
 if !validID(sessionID)||!validID(targetID){return nil,errors.New("invalid session/target ID")}
 return &Machine{sessionID:sessionID,targetID:targetID,state:New,seen:make(map[string]entry)},nil
}
func validID(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'||c=='.'){return false}}
 return true
}
func validDigest(s string)bool {
 if len(s)!=64||strings.ToLower(s)!=s{return false}
 _,err:=hex.DecodeString(s);return err==nil
}
func Digest(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func (m *Machine) Snapshot()Receipt{
 return Receipt{SchemaVersion:ReceiptVersion,Status:"observed",State:m.state,Revision:m.revision,Epoch:m.epoch}
}
// Submit is the untrusted human/automation/agent command ingress. It cannot
// claim that audio began, ended or failed; only a verified host adapter may
// call ObserveHost, and that authorization MUST be enforced at the process
// boundary (the Go type system is not an authentication authority).
func (m *Machine) Submit(c Command)Outcome{
 if isHostEvent(c.Action){return m.routeRejected("host_observation_requires_trusted_adapter")}
 return m.apply(c)
}
// ObserveHost is for authenticated local adapter observations, never published
// as a user, network, CLI or agent invocation without host verification.
func (m *Machine) ObserveHost(c Command)Outcome{
 if !isHostEvent(c.Action){return m.routeRejected("user_command_requires_submit")}
 return m.apply(c)
}
func isHostEvent(a Action)bool{
 return a==HostStarted||a==HostStopped||a==HostCompleted||a==HostFailed
}
func (m *Machine) routeRejected(status string)Outcome{
 return Outcome{Receipt:Receipt{SchemaVersion:ReceiptVersion,Status:status,State:m.state,Revision:m.revision,Epoch:m.epoch}}
}
func (m *Machine) apply(c Command)Outcome{
 status:="rejected"
 reply:=func() Outcome {
  return Outcome{Receipt:Receipt{Status:status,State:m.state,Revision:m.revision,Epoch:m.epoch}}
 }
 if c.SchemaVersion!=ProtocolVersion||!validID(c.PrincipalID)||!validID(c.OperationID)||c.SessionID!=m.sessionID||c.TargetID!=m.targetID{return reply()}
 scopedOpKey:=c.PrincipalID+"|"+c.OperationID
 if old,ok:=m.seen[scopedOpKey];ok{
  if old.cmd!=c {status="operation_id_reused_with_different_payload";return reply()}
  return Outcome{Receipt:old.receipt,Replayed:true}
 }
 if len(m.seen)>=maxRemembered{status="bounded_history_full";return reply()}
 effects:=[]Effect{}
 record:=func()Outcome{
  receipt:=Receipt{SchemaVersion:ReceiptVersion,Status:status,State:m.state,Revision:m.revision,Epoch:m.epoch,Effects:effects}
  m.seen[scopedOpKey]=entry{cmd:c,receipt:receipt}
  return Outcome{Receipt:receipt,Dispatch:effects}
 }
 hostEvent:=isHostEvent(c.Action)
 // STOP preempts stale expectedRevision. Host observations are epoch fenced, with
 // authorization and role verification required outside this pure function.
 if c.Action!=Stop&&!hostEvent&&c.ExpectedRevision!=m.revision{
  status="stale_revision";return record()
 }
 if hostEvent && (c.Epoch==0||c.Epoch!=m.epoch){
  status="stale_epoch";return record()
 }
 switch c.Action{
 case Configure:
  if m.state!=New || !validDigest(c.ConfigDigest){return record()}
  m.configDigest=c.ConfigDigest
  m.state=Configured
  m.revision++
  status="accepted"
 case RequestStart:
  if m.state!=Configured||m.configDigest==""{return record()}
  m.epoch++
  m.state=StartPending
  m.revision++
  // A request is never permission to play. The host checks physical/output
  // authorization and may report host_started only after actual effect.
  effects=append(effects,Effect{Kind:"host_authorize_then_start",Epoch:m.epoch})
  status="accepted"
 case Stop:
  switch m.state {
  case New,Configured:
   m.state=Stopped;m.revision++;status="accepted"
  case StartPending,Active:
   m.state=StopPending;m.revision++
   effects=append(effects,Effect{Kind:"host_stop_now",Epoch:m.epoch})
   status="accepted"
  case StopPending:
   // New STOP id can safely restate the same stop intent. Same op ID is
   // suppressed by the replay ledger above.
   effects=append(effects,Effect{Kind:"host_stop_now",Epoch:m.epoch})
   status="accepted"
  default:status="noop"
  }
 case HostStarted:
  switch m.state{
  case StartPending:
   m.state=Active;m.revision++;status="accepted"
  case StopPending,Stopped,Completed,Failed,Closed:
   // STOP dominates a late acknowledgment. Reassert stop, never revive output.
   effects=append(effects,Effect{Kind:"host_stop_now",Epoch:m.epoch})
   status="ignored_late_start"
  default:status="rejected"
  }
 case HostStopped:
  switch m.state{
  case StartPending,Active,StopPending:
   m.state=Stopped;m.revision++;status="accepted"
  case Stopped:status="noop"
  default:status="rejected"
  }
 case HostCompleted:
  if m.state==Active {m.state=Completed;m.revision++;status="accepted"}else{status="rejected"}
 case HostFailed:
  if m.state==StartPending||m.state==Active||m.state==StopPending{
   m.state=Failed;m.revision++;status="accepted"
   effects=append(effects,Effect{Kind:"host_stop_now",Epoch:m.epoch})
  }else{status="rejected"}
 case Close:
  if m.state==Stopped||m.state==Completed||m.state==Failed{
   m.state=Closed;m.revision++;status="accepted"
  }else{status="rejected"}
 default:status="unsupported_action"
 }
 return record()
}
