package scenejob

// R11: source-original synthetic only. Exercise OS-process boundaries rather
// than claiming that two Manager values in one Go process prove process safety.
import (
 "context"
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
 "time"
)

const r11ModeEnv = "SCP_R11_HELPER_MODE"
const r11RootEnv = "SCP_R11_HELPER_ROOT"

type r11HoldingEngine struct{ root string }
func (e *r11HoldingEngine) Run(ctx context.Context, dir, revision string) error {
 if err := os.WriteFile(filepath.Join(e.root, "r11-started"), []byte("entered native engine"), 0600); err != nil { return err }
 until := time.Now().Add(15*time.Second)
 for time.Now().Before(until) {
  if _, err := os.Stat(filepath.Join(e.root,"r11-release")); err == nil {
   return (&fakeEngine{}).Run(ctx,dir,revision)
  }
  if err := ctx.Err(); err != nil { return err }
  time.Sleep(20*time.Millisecond)
 }
 return errors.New("R11_HELPER_TIMEOUT")
}

// Test helper is invoked only in child processes with a narrowly scoped
// environment. The parent also invokes this test without env: that is a no-op.
func TestR11OSHelper(t *testing.T) {
 mode := os.Getenv(r11ModeEnv)
 if mode == "" { return }
 root := os.Getenv(r11RootEnv)
 if root == "" { t.Fatal("missing helper root") }
 m, err := NewManager(testRevision,root,&r11HoldingEngine{root:root})
 if err != nil { t.Fatal(err) }
 _, err = m.Run(context.Background(),Expected(testRevision))
 switch mode {
 case "hold":
  if err != nil { t.Fatal(err) }
 case "contend":
  if err == nil || !strings.Contains(err.Error(),"ROOT_WRITER_BUSY_OR_RECOVERY_REQUIRED") {
   t.Fatalf("competing OS process was not denied: %v",err)
  }
 default: t.Fatalf("unsupported helper mode %q",mode)
 }
}

func r11Child(root,mode string) *exec.Cmd {
 c := exec.Command(os.Args[0],"-test.run=^TestR11OSHelper$","-test.timeout=25s")
 c.Env=append(os.Environ(),r11ModeEnv+"="+mode,r11RootEnv+"="+root)
 return c
}

func r11WaitStarted(t *testing.T, root string) {
 t.Helper()
 until:=time.Now().Add(8*time.Second)
 for time.Now().Before(until) {
  if _,err:=os.Stat(filepath.Join(root,"r11-started"));err==nil{return}
  time.Sleep(20*time.Millisecond)
 }
 t.Fatal("child never entered native engine")
}

func TestR11ActualSeparateOSProcessContentionAndReplay(t *testing.T) {
 root:=t.TempDir()
 owner:=r11Child(root,"hold")
 if err:=owner.Start();err!=nil{t.Fatal(err)}
 defer func(){if owner.ProcessState==nil{_ = owner.Process.Kill();_ = owner.Wait()}}()
 r11WaitStarted(t,root)
 rival:=r11Child(root,"contend")
 if output,err:=rival.CombinedOutput();err!=nil{t.Fatalf("competing process failed to verify denial: %v %s",err,output)}
 if err:=os.WriteFile(filepath.Join(root,"r11-release"),[]byte("released"),0600);err!=nil{t.Fatal(err)}
 if err:=owner.Wait();err!=nil{t.Fatal("owner process failed",err)}
 restored,err:=NewManager(testRevision,root,&fakeEngine{})
 if err!=nil{t.Fatal(err)}
 r,ok,err:=restored.Result()
 if err!=nil||!ok||r.Release!="HELD_R009_NOT_RUN_NOT_ADMITTED"{t.Fatalf("original source replay not safe: %+v %v %v",r,ok,err)}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0002"));!os.IsNotExist(err){t.Fatalf("duplicate attempt from rival process: %v",err)}
}

func TestR11SIGKILLLeavesOrphanLockAndFirstAttempt(t *testing.T) {
 if os.Getenv("GOOS")=="windows"{t.Skip("SIGKILL and POSIX directory-lock contract")}
 root:=t.TempDir()
 owner:=r11Child(root,"hold")
 if err:=owner.Start();err!=nil{t.Fatal(err)}
 defer func(){if owner.ProcessState==nil{_ = owner.Process.Kill();_ = owner.Wait()}}()
 r11WaitStarted(t,root)
 if err:=owner.Process.Kill();err!=nil{t.Fatal(err)}
 _=owner.Wait() // expected forced stop
 if _,err:=os.Stat(filepath.Join(root,writerLockName));err!=nil{t.Fatal("orphan lock missing",err)}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0001"));err!=nil{t.Fatal("first attempt evidence lost",err)}
 m,err:=NewManager(testRevision,root,&fakeEngine{})
 if err!=nil{t.Fatal(err)}
 if _,err=m.Run(context.Background(),Expected(testRevision));err==nil||!strings.Contains(err.Error(),"RECOVERY_REQUIRED"){
  t.Fatalf("orphan lock incorrectly ignored: %v",err)
 }
 if _,err:=os.Stat(filepath.Join(root,writerLockName));err!=nil{t.Fatal("orphan lock erased",err)}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0001"));err!=nil{t.Fatal("first attempt erased",err)}
}
