//go:build linux

// Package ledger provides a single-host durable transaction gate for bounded provider research.
// Flock is not a cross-host/runner distributed lock; do not deploy across independent GHA runners.
package ledger

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "net/url"
 "os"
 "path/filepath"
 "strings"
 "syscall"

 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)

type Entry struct {
 State sweeps.RequestState `json:"state"`
 PendingTicket string `json:"pending_ticket,omitempty"`
 LastOutcome string `json:"last_outcome,omitempty"`
}
type State struct {
 Schema string `json:"schema"`
 Entries map[string]Entry `json:"entries"`
}
type Ledger struct { Path string }
type Ticket struct {
 ID string `json:"id"`
 Origin string `json:"origin"`
 ProviderID string `json:"provider_id"`
 ReservedAtMS int64 `json:"reserved_at_ms"`
}
func validOrigin(origin string)bool {
 u,err:=url.Parse(origin)
 return err==nil&&u.Scheme=="https"&&u.Hostname()!=""&&u.User==nil&&u.Path==""&&u.RawQuery==""&&u.Fragment==""&&u.Host==strings.ToLower(u.Host)
}
func (l Ledger) transact(fn func(*State)error)error {
 if l.Path=="" {return errors.New("missing ledger path")}
 dir:=filepath.Dir(l.Path)
 if err:=os.MkdirAll(dir,0700);err!=nil{return err}
 lockpath:=l.Path+".lock"
 if x,err:=os.Lstat(lockpath);err==nil && x.Mode()&os.ModeSymlink!=0{return errors.New("symlink lock forbidden")}
 lock,err:=os.OpenFile(lockpath,os.O_CREATE|os.O_RDWR,0600)
 if err!=nil{return err}
 defer lock.Close()
 if err:=syscall.Flock(int(lock.Fd()),syscall.LOCK_EX);err!=nil{return err}
 defer syscall.Flock(int(lock.Fd()),syscall.LOCK_UN)
 state:=State{Schema:"scp.origin_quota_ledger.v1",Entries:map[string]Entry{}}
 if info,err:=os.Lstat(l.Path);err==nil {
  if !info.Mode().IsRegular()||info.Mode().Perm()&0077!=0{return errors.New("unsafe ledger file permissions/type")}
  data,err:=os.ReadFile(l.Path);if err!=nil{return err}
  if err:=json.Unmarshal(data,&state);err!=nil{return fmt.Errorf("unreadable ledger: %w",err)}
  if state.Schema!="scp.origin_quota_ledger.v1"||state.Entries==nil{return errors.New("wrong ledger schema")}
 } else if !os.IsNotExist(err){return err}
 if err:=fn(&state);err!=nil{return err}
 data,err:=json.MarshalIndent(state,"","  ");if err!=nil{return err}
 temp,err:=os.CreateTemp(dir,".quota-*.tmp");if err!=nil{return err}
 defer os.Remove(temp.Name())
 if err:=temp.Chmod(0600);err!=nil{temp.Close();return err}
 if _,err:=temp.Write(data);err!=nil{temp.Close();return err}
 if err:=temp.Sync();err!=nil{temp.Close();return err}
 if err:=temp.Close();err!=nil{return err}
 if err:=os.Rename(temp.Name(),l.Path);err!=nil{return err}
 d,err:=os.Open(dir);if err!=nil{return err};defer d.Close()
 return d.Sync()
}
func key(origin, providerID string)string{return providerID+"@"+origin}
func (l Ledger) Reserve(p sweeps.AccessPolicy,origin string,nowMS int64)(Ticket,sweeps.Permit,error){
 deny:=sweeps.Permit{Status:"LEDGER_HOLD",Explanation:"ledger transaction not qualified"}
 if !validOrigin(origin)||p.ProviderID==""{return Ticket{},deny,errors.New("invalid exact https origin")}
 var ticket Ticket
 permit:=deny
 err:=l.transact(func(st *State)error{
  k:=key(origin,p.ProviderID)
  entry:=st.Entries[k]
  permit=sweeps.CheckPermit(p,entry.State,nowMS)
  if permit.Status!="PLAN_PERMITTED"{return nil}
  id:=sha256.Sum256([]byte(fmt.Sprintf("%s|%d|%d",k,nowMS,len(entry.State.AttemptTimesMS))))
  ticket=Ticket{ID:hex.EncodeToString(id[:16]),Origin:origin,ProviderID:p.ProviderID,ReservedAtMS:nowMS}
  if entry.PendingTicket!="" {permit=sweeps.Permit{Status:"PENDING_HOLD",Explanation:"unresolved prior reservation"};return nil}
  entry.PendingTicket=ticket.ID
  entry.State.Active=1
  entry.State.HasAttempt=true
  entry.State.LastAttemptMS=nowMS
  entry.State.AttemptTimesMS=append(entry.State.AttemptTimesMS,nowMS)
  entry.State.Pages++
  st.Entries[k]=entry
  return nil
 })
 if err!=nil{return Ticket{},deny,err}
 return ticket,permit,nil
}
func (l Ledger) Complete(ticket Ticket,status,retryAfterSeconds int,nowMS int64)error{
 if ticket.ID==""||!validOrigin(ticket.Origin)||ticket.ProviderID==""||status<0||status>599||
  retryAfterSeconds<0||retryAfterSeconds>86400||nowMS<ticket.ReservedAtMS{return errors.New("invalid completion")}
 return l.transact(func(st *State)error{
  k:=key(ticket.Origin,ticket.ProviderID)
  e,ok:=st.Entries[k]
  if !ok||e.PendingTicket!=ticket.ID||e.State.Active!=1{return errors.New("stale or replayed ticket")}
  e.PendingTicket=""
  e.State.Active=0
  if status==0 {status=503} // transport unknown -> fail closed
  e.State.RecentStatus=status
  if status==429||status>=500 {
   if retryAfterSeconds>0 {
    next:=nowMS+int64(retryAfterSeconds)*1000
    if next<nowMS{return errors.New("cooldown clock overflow")}
    e.State.CooldownUntilMS=next
   } else {e.State.CooldownUntilMS=0}
  }
  e.LastOutcome=fmt.Sprintf("HTTP_%d",status)
  st.Entries[k]=e
  return nil
 })
}
