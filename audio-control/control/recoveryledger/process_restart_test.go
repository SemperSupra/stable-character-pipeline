package recoveryledger

import (
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
)

// The child bypasses normal test cleanup after persisting an intent. This is a
// process-exit probe, not power-loss, disk-exhaustion or physical STOP evidence.
func TestLedgerProcessHelper(t *testing.T) {
 if os.Getenv("AUDIO_LEDGER_CHILD")!="1" { return }
 s,err:=NewStore(os.Getenv("AUDIO_LEDGER_ROOT"));if err!=nil { os.Exit(31) }
 admitted,err:=s.AdmitStart(example())
 if err!=nil {
  // Another process may still be writing the immutable record. Rejecting the
  // partial record is conservative and must never grant a second effect.
  if errors.Is(err,ErrCorrupt) { os.Exit(24) }
  os.Exit(32)
 }
 if admitted { os.Exit(23) }
 os.Exit(24)
}

func ledgerChild(root string)*exec.Cmd {
 c:=exec.Command(os.Args[0],"-test.run=^TestLedgerProcessHelper$")
 for _,e:=range os.Environ() {
  if !strings.HasPrefix(e,"AUDIO_LEDGER_CHILD=")&&!strings.HasPrefix(e,"AUDIO_LEDGER_ROOT=") {
   c.Env=append(c.Env,e)
  }
 }
 c.Env=append(c.Env,"AUDIO_LEDGER_CHILD=1","AUDIO_LEDGER_ROOT="+root)
 return c
}
func childExit(t *testing.T,c *exec.Cmd)int {
 t.Helper()
 err:=c.Wait()
 var exit *exec.ExitError
 if !errors.As(err,&exit) { t.Fatalf("expected deliberate child exit, got %v",err) }
 return exit.ExitCode()
}
func TestActualProcessExitRetainsPendingAndSuppressesRestartStart(t *testing.T) {
 root:=filepath.Join(t.TempDir(),"ledger")
 c:=ledgerChild(root)
 if err:=c.Start();err!=nil { t.Fatal(err) }
 if code:=childExit(t,c);code!=23 { t.Fatalf("initial intent was not admitted: %d",code) }
 s:=mustStore(t,root)
 state:=s.Recover(example())
 if state.Kind!="unknown_pending"||!state.RequiresHostReconcile||state.MayIssueStart {
  t.Fatalf("process death fabricated outcome: %+v",state)
 }
 replay:=ledgerChild(root)
 if err:=replay.Start();err!=nil { t.Fatal(err) }
 if code:=childExit(t,replay);code!=24 { t.Fatalf("restarted process redispatched or errored: %d",code) }
}
func TestCompetingProcessesGrantAtMostOneSyntheticStart(t *testing.T) {
 root:=filepath.Join(t.TempDir(),"ledger")
 // Precreate the owned root so the race targets record admission only.
 mustStore(t,root)
 a,b:=ledgerChild(root),ledgerChild(root)
 if err:=a.Start();err!=nil { t.Fatal(err) }
 if err:=b.Start();err!=nil { _=a.Wait();t.Fatal(err) }
 x,y:=childExit(t,a),childExit(t,b)
 if !((x==23&&y==24)||(x==24&&y==23)) {
  t.Fatalf("expected one eligibility token and one refusal: %d %d",x,y)
 }
 state:=mustStore(t,root).Recover(example())
 if state.Kind!="unknown_pending"||!state.RequiresHostReconcile||state.MayIssueStart {
  t.Fatalf("competing writers fabricated effect result: %+v",state)
 }
}
