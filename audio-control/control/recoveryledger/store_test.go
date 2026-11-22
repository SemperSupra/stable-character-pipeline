package recoveryledger

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func digest(s string)string{v:=sha256.Sum256([]byte(s));return hex.EncodeToString(v[:])}
func example()Intent{
 return Intent{Version:1,PrincipalID:"local_human",SessionID:"synthetic_s1",OperationID:"request_01",
 TargetID:"host_audio_1",Epoch:7,PlanSHA256:digest("original synthetic plan")}
}
func mustStore(t *testing.T,root string)*Store{
 t.Helper();s,e:=NewStore(root);if e!=nil{t.Fatal(e)};return s
}
func TestRestartDisablesDuplicateStartAndRequestsHostReconciliation(t *testing.T){
 root:=filepath.Join(t.TempDir(),"ledger")
 s:=mustStore(t,root)
 plan:=example()
 admitted,e:=s.AdmitStart(plan);if e!=nil||!admitted{t.Fatalf("initial durable intent %v %v",admitted,e)}
 resumed:=mustStore(t,root)
 state:=resumed.Recover(plan)
 if state.Kind!="unknown_pending"||!state.RequiresHostReconcile||state.MayIssueStart{
  t.Fatalf("restart falsely proves audio output: %+v",state)
 }
 again,e:=resumed.AdmitStart(plan)
 if e!=nil||again{t.Fatalf("duplicate replayed physical start: %v %v",again,e)}
 conflict:=plan;conflict.PlanSHA256=digest("conflicting plan")
 if _,e:=resumed.AdmitStart(conflict);!errors.Is(e,ErrConflict){
  t.Fatalf("operation ID collision admitted: %v",e)
 }
}
func TestObservedStopRequiresOriginalIntentAndKeepsOriginalReceipt(t *testing.T){
 root:=filepath.Join(t.TempDir(),"ledger")
 s:=mustStore(t,root);i:=example()
 if _,e:=s.RecordHostStopped(i,digest("host stop"));e==nil{
  t.Fatal("stopped receipt without original intent accepted")
 }
 if _,e:=s.AdmitStart(i);e!=nil{t.Fatal(e)}
 first,e:=s.RecordHostStopped(i,digest("host stop"))
 if e!=nil||!first{t.Fatalf("first stop receipt: %v %v",first,e)}
 restarted:=mustStore(t,root)
 state:=restarted.Recover(i)
 if state.Kind!="observed_stopped"||state.RequiresHostReconcile||state.MayIssueStart{
  t.Fatalf("confirmed stop lost: %+v",state)
 }
 again,e:=restarted.RecordHostStopped(i,digest("host stop"))
 if e!=nil||again{t.Fatalf("same stop not deduplicated: %v %v",again,e)}
 if _,e:=restarted.RecordHostStopped(i,digest("other host record"));!errors.Is(e,ErrConflict){
  t.Fatalf("host stop evidence substitution accepted: %v",e)
 }
 if _,e:=restarted.AdmitStart(i);!errors.Is(e,ErrConflict){
  t.Fatalf("restarted after confirmed STOP: %v",e)
 }
}
func TestTruncatedPendingAndSpoofedHostObservationFailClosed(t *testing.T){
 s:=mustStore(t,filepath.Join(t.TempDir(),"ledger"));i:=example()
 if _,e:=s.AdmitStart(i);e!=nil{t.Fatal(e)}
 pending,stopped:=s.paths(i)
 if e:=os.WriteFile(stopped,[]byte("not a trustworthy host stop"),0600);e!=nil{t.Fatal(e)}
 if got:=s.Recover(i);got.Kind!="corrupt_unknown"||!got.RequiresHostReconcile{
  t.Fatalf("spoofed host observation trusted: %+v",got)
 }
 if e:=os.Truncate(pending,9);e!=nil{t.Fatal(e)}
 if got:=s.Recover(i);got.Kind!="corrupt_unknown"||!got.RequiresHostReconcile{
  t.Fatalf("partial record treated as complete: %+v",got)
 }
 if _,e:=s.AdmitStart(i);!errors.Is(e,ErrCorrupt){t.Fatalf("partial record bypassed: %v",e)}
}
func TestUnknownAfterCrashAndInputBounds(t *testing.T){
 s:=mustStore(t,filepath.Join(t.TempDir(),"ledger"));i:=example()
 if got:=s.Recover(i);got.Kind!="unknown_no_record"||got.MayIssueStart||!got.RequiresHostReconcile{
  t.Fatalf("unknown session wrongly declared safe: %+v",got)
 }
 bad:=i;bad.SessionID="../escape"
 if _,e:=s.AdmitStart(bad);!errors.Is(e,ErrInvalid){t.Fatalf("unsafe ID admitted %v",e)}
 bad=i;bad.PlanSHA256=strings.Repeat("Z",64)
 if _,e:=s.AdmitStart(bad);!errors.Is(e,ErrInvalid){t.Fatalf("invalid hash admitted %v",e)}
 if _,e:=NewStore("relative");!errors.Is(e,ErrInvalid){t.Fatalf("relative journal accepted: %v",e)}
}
func TestSymlinkSubstitutionCannotImpersonateJournal(t *testing.T){
 s:=mustStore(t,filepath.Join(t.TempDir(),"ledger"));i:=example()
 if _,e:=s.AdmitStart(i);e!=nil{t.Fatal(e)}
 pending,_:=s.paths(i)
 real:=filepath.Join(t.TempDir(),"impostor.json")
 if e:=os.WriteFile(real,[]byte("spoof"),0600);e!=nil{t.Fatal(e)}
 if e:=os.Remove(pending);e!=nil{t.Fatal(e)}
 if e:=os.Symlink(real,pending);e!=nil{t.Skip("symlink unavailable: "+e.Error())}
 if got:=s.Recover(i);got.Kind!="corrupt_unknown"||!got.RequiresHostReconcile{
  t.Fatalf("symlink journal trusted: %+v",got)
 }
}
