// Package recoveryledger is a deliberately narrow process-restart probe.
// It is NOT a power-loss-safe transactional outbox or an authorized device
// controller. It persists an operation intent BEFORE any effect may be issued,
// then returns conservative reconcile/stop decisions after a process restart.
package recoveryledger

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "strings"
)

var (
 ErrInvalid = errors.New("recoveryledger: invalid identity or plan")
 ErrConflict = errors.New("recoveryledger: operation ID already has different immutable intent")
 ErrCorrupt = errors.New("recoveryledger: untrusted or partial record; effect state unknown")
)
const version=1
const maxRecordBytes=4096

type Intent struct {
 Version int `json:"version"`
 PrincipalID string `json:"principal_id"`
 SessionID string `json:"session_id"`
 OperationID string `json:"operation_id"`
 TargetID string `json:"target_id"`
 Epoch uint64 `json:"epoch"`
 PlanSHA256 string `json:"plan_sha256"`
}
type Observation struct {
 Intent Intent `json:"intent"`
 Kind string `json:"kind"` // Only an authorized host should ever produce "stopped".
 HostEvidenceSHA256 string `json:"host_evidence_sha256"`
}
type State struct {
 Kind string `json:"kind"` // unknown_no_record, unknown_pending, observed_stopped, corrupt_unknown
 RequiresHostReconcile bool `json:"requires_host_reconcile"`
 MayIssueStart bool `json:"may_issue_start"` // ALWAYS false for recovery.
}
type Store struct{root string}

func allowedID(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s {
  if !((c>='0'&&c<='9')||(c>='A'&&c<='Z')||(c>='a'&&c<='z')||c=='-'||c=='_'||c=='.'){return false}
 }
 return true
}
func sha(s string)bool {
 if len(s)!=64{return false}
 if strings.ToLower(s)!=s{return false}
 _,e:=hex.DecodeString(s)
 return e==nil
}
func (i Intent)validate()error{
 if i.Version!=version||!allowedID(i.PrincipalID)||!allowedID(i.SessionID)||
 !allowedID(i.OperationID)||!allowedID(i.TargetID)||i.Epoch==0||!sha(i.PlanSHA256) {
  return ErrInvalid
 }
 return nil
}
func NewStore(root string)(*Store,error){
 if root==""||!filepath.IsAbs(root)||filepath.Clean(root)!=root{return nil,ErrInvalid}
 if e:=os.MkdirAll(root,0700);e!=nil{return nil,e}
 real,e:=filepath.EvalSymlinks(root);if e!=nil{return nil,e}
 if real!=root{return nil,ErrInvalid}
 s,e:=os.Stat(root);if e!=nil{return nil,e}
 if !s.IsDir(){return nil,ErrInvalid}
 return &Store{root:root},nil
}
func (s *Store)paths(i Intent)(string,string){
 h:=sha256.Sum256([]byte(i.PrincipalID+"\x00"+i.SessionID+"\x00"+i.OperationID))
 prefix:=hex.EncodeToString(h[:])
 return filepath.Join(s.root,prefix+".intent.json"),filepath.Join(s.root,prefix+".stopped.json")
}
func canonical(v any)([]byte,error){
 b,e:=json.Marshal(v);if e!=nil{return nil,e}
 return append(b,'\n'),nil
}
func readProtected(path string)([]byte,error){
 st,e:=os.Lstat(path);if e!=nil{return nil,e}
 if !st.Mode().IsRegular()||st.Size()>maxRecordBytes{return nil,ErrCorrupt}
 data,e:=os.ReadFile(path);if e!=nil{return nil,e}
 if len(data)>maxRecordBytes{return nil,ErrCorrupt}
 return data,nil
}
func writeOnce(path string,data []byte)(bool,error){
 if len(data)>maxRecordBytes{return false,ErrInvalid}
 f,e:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if errors.Is(e,os.ErrExist){
  prior,readErr:=readProtected(path);if readErr!=nil{return false,ErrCorrupt}
  if bytes.Equal(prior,data){return false,nil}
  return false,ErrConflict
 }
 if e!=nil{return false,e}
 _,writeErr:=f.Write(data)
 if writeErr==nil{writeErr=f.Sync()}
 closeErr:=f.Close()
 if writeErr!=nil{return false,writeErr}
 if closeErr!=nil{return false,closeErr}
 return true,nil
}
// AdmitStart persists a pending intent and only then grants the caller a
// *one-time synthetic* eligibility token. It does not play audio, authorize
// a device, guarantee directory fsync, or create an exactly-once transaction.
func (s *Store)AdmitStart(i Intent)(bool,error){
 if s==nil{return false,ErrInvalid}
 if e:=i.validate();e!=nil{return false,e}
 pending,stopped:=s.paths(i)
 // Diagnose existing untrusted/partial records before calling duplicate/conflict.
 // A forged stopped file is not evidence of a completed host stop.
 if _,e:=os.Lstat(stopped);e==nil{
  if state:=s.Recover(i);state.Kind=="observed_stopped"{return false,ErrConflict}
  return false,ErrCorrupt
 }else if !errors.Is(e,os.ErrNotExist){return false,e}
 if _,e:=os.Lstat(pending);e==nil{
  state:=s.Recover(i)
  if state.Kind=="unknown_pending"{return false,nil}
  return false,ErrCorrupt
 }else if !errors.Is(e,os.ErrNotExist){return false,e}
 b,e:=canonical(i);if e!=nil{return false,e}
 return writeOnce(pending,b)
}
func (s *Store)Recover(i Intent)State{
 state:=State{Kind:"corrupt_unknown",RequiresHostReconcile:true}
 if s==nil||i.validate()!=nil{return state}
 pending,stopped:=s.paths(i)
 bytesPending,e:=readProtected(pending)
 if errors.Is(e,os.ErrNotExist){return State{Kind:"unknown_no_record",RequiresHostReconcile:true}}
 if e!=nil{return state}
 expected,_:=canonical(i)
 if !bytes.Equal(bytesPending,expected){return state}
 stoppedBytes,stopErr:=readProtected(stopped)
 if errors.Is(stopErr,os.ErrNotExist){return State{Kind:"unknown_pending",RequiresHostReconcile:true}}
 if stopErr!=nil{return state}
 var obs Observation
 if json.Unmarshal(stoppedBytes,&obs)!=nil||obs.Kind!="stopped"||obs.Intent!=i||!sha(obs.HostEvidenceSHA256){
  return state
 }
 canonicalObs,_:=canonical(obs)
 if !bytes.Equal(stoppedBytes,canonicalObs){return state}
 return State{Kind:"observed_stopped",RequiresHostReconcile:false}
}
// RecordHostStopped is an intentionally UNTRUSTED API in this probe.
// A production adapter would require independently authenticated host events
// and matching device/lease/epoch, not caller-supplied host evidence strings.
func (s *Store)RecordHostStopped(i Intent,evidenceDigest string)(bool,error){
 if s==nil||i.validate()!=nil||!sha(evidenceDigest){return false,ErrInvalid}
 if got:=s.Recover(i);got.Kind!="unknown_pending"&&got.Kind!="observed_stopped"{
  return false,fmt.Errorf("%w: missing original pending intent",ErrCorrupt)
 }
 _,path:=s.paths(i)
 b,e:=canonical(Observation{Intent:i,Kind:"stopped",HostEvidenceSHA256:evidenceDigest})
 if e!=nil{return false,e}
 return writeOnce(path,b)
}
