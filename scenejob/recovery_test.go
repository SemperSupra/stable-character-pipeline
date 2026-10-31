package scenejob

import (
 "context"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "sync/atomic"
 "testing"
)

func TestR10SourceBoundDurableRestartAndMedia(t *testing.T) {
 root:=t.TempDir()
 engine:=&fakeEngine{}
 first,err:=NewManager(testRevision,root,engine)
 if err!=nil{t.Fatal(err)}
 want,err:=first.Run(context.Background(),Expected(testRevision))
 if err!=nil{t.Fatal(err)}
 second,err:=NewManager(testRevision,root,engine)
 if err!=nil{t.Fatal(err)}
 got,ok,err:=second.Result()
 if err!=nil||!ok||got.SourceSHA!=want.SourceSHA{t.Fatalf("lost verified persisted result: %+v %v",got,err)}
 for _,camera:=range cameras {
  if _,err:=second.MediaPath(camera);err!=nil{t.Fatal(err)}
 }
 repeated,err:=second.Run(context.Background(),Expected(testRevision))
 if err!=nil||repeated.Release!="HELD_R009_NOT_RUN_NOT_ADMITTED"{t.Fatalf("%+v %v",repeated,err)}
 if engine.calls.Load()!=1{t.Fatal("duplicate native render after restart",engine.calls.Load())}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0002"));!os.IsNotExist(err){t.Fatal("created duplicate attempt",err)}
}

type r10BlockingEngine struct {
 started chan struct{}
 proceed chan struct{}
 calls atomic.Int32
}
func(e *r10BlockingEngine)Run(ctx context.Context,dir,rev string)error{
 e.calls.Add(1)
 close(e.started)
 select{case <-e.proceed:case <-ctx.Done():return ctx.Err()}
 return (&fakeEngine{}).Run(ctx,dir,rev)
}
func TestR10TwoIndependentManagersOneCrossProcessWriter(t *testing.T){
 root:=t.TempDir()
 engine:=&r10BlockingEngine{started:make(chan struct{}),proceed:make(chan struct{})}
 first,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 second,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 done:=make(chan error,1)
 go func(){_,err:=first.Run(context.Background(),Expected(testRevision));done<-err}()
 <-engine.started
 if _,err:=second.Run(context.Background(),Expected(testRevision));err==nil||!strings.Contains(err.Error(),"ROOT_WRITER_BUSY"){
  close(engine.proceed);t.Fatalf("second writer admitted during active first writer: %v",err)
 }
 close(engine.proceed)
 if err:=<-done;err!=nil{t.Fatal(err)}
 got,err:=second.Run(context.Background(),Expected(testRevision))
 if err!=nil||got.Release!="HELD_R009_NOT_RUN_NOT_ADMITTED"{t.Fatalf("failed source-bound replay: %+v %v",got,err)}
 if engine.calls.Load()!=1{t.Fatal("two engines executed",engine.calls.Load())}
}

func TestR10TamperedDurableBytesMustBlockReplay(t *testing.T){
 root:=t.TempDir()
 engine:=&fakeEngine{}
 first,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 if _,err:=first.Run(context.Background(),Expected(testRevision));err!=nil{t.Fatal(err)}
 media:=filepath.Join(root,"attempt-0001","forward","rendered","OriginalOblique.mp4")
 if err:=os.WriteFile(media,[]byte("tampered"),0600);err!=nil{t.Fatal(err)}
 if _,err:=NewManager(testRevision,root,engine);err==nil||!strings.Contains(err.Error(),"DURABLE_RESULT_FAIL_CLOSED"){
  t.Fatalf("promoted forged durable bytes: %v",err)
 }
 if _,err:=NewManager(strings.Repeat("b",40),root,engine);err==nil{
  t.Fatal("cross-source revision incorrectly reused persisted result")
 }
 if engine.calls.Load()!=1{t.Fatal("native engine attempted rerender on mutated receipt")}
}

func TestR10CrashOrphanLockFailClosed(t *testing.T){
 root:=t.TempDir()
 engine:=&fakeEngine{}
 m,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 if err:=os.Mkdir(filepath.Join(root,writerLockName),0700);err!=nil{t.Fatal(err)}
 if _,err:=m.Run(context.Background(),Expected(testRevision));err==nil||!strings.Contains(err.Error(),"RECOVERY_REQUIRED"){
  t.Fatalf("silently stole crash lock: %v",err)
 }
 if engine.calls.Load()!=0{t.Fatal("native engine ran behind stale lock")}
 if _,err:=os.Stat(filepath.Join(root,writerLockName));err!=nil{t.Fatal("crash evidence erased")}
}

func TestR10PreserveFirstFailureAcrossRestart(t *testing.T){
 root:=t.TempDir()
 engine:=&fakeEngine{fail:true}
 first,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 if _,err:=first.Run(context.Background(),Expected(testRevision));err==nil{t.Fatal("first intended failure lost")}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0001","first-failure-observation.txt"));err!=nil{t.Fatal(err)}
 engine.fail=false
 second,err:=NewManager(testRevision,root,engine);if err!=nil{t.Fatal(err)}
 if _,err:=second.Run(context.Background(),Expected(testRevision));err!=nil{t.Fatal(err)}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0001","first-failure-observation.txt"));err!=nil{t.Fatal("first failure overwritten",err)}
 if _,err:=os.Stat(filepath.Join(root,"attempt-0002","result.json"));err!=nil{t.Fatal(err)}
}

func TestR10RejectSymlinkedAttemptAndAmbiguousCompletes(t *testing.T){
 root:=t.TempDir()
 engine:=&fakeEngine{}
 external:=t.TempDir()
 if err:=os.Symlink(external,filepath.Join(root,"attempt-0001"));err!=nil{
  t.Skip("platform cannot create symlink:",err)
 }
 if _,err:=NewManager(testRevision,root,engine);err==nil||!strings.Contains(err.Error(),"UNSAFE_ATTEMPT_DIRECTORY"){
  t.Fatalf("accepted symlink attempt: %v",err)
 }
}

// This test fixes the absence of any implicit 'delete/repair/rollback' path:
// original false result / malformed historical attempt is a hard stop.
func TestR10ForgedResultOnColdCheckoutIsNotReset(t *testing.T){
 root:=t.TempDir()
 if err:=os.Mkdir(filepath.Join(root,"attempt-0001"),0700);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(root,"attempt-0001","result.json"),[]byte(`{"release":"PASS"}`),0600);err!=nil{t.Fatal(err)}
 _,err:=NewManager(testRevision,root,&fakeEngine{})
 if err==nil||!strings.Contains(err.Error(),"DURABLE_RESULT_FAIL_CLOSED"){
  t.Fatalf("forged result discarded or accepted: %v",err)
 }
 if _,err:=os.Stat(filepath.Join(root,"attempt-0001","result.json"));errors.Is(err,os.ErrNotExist){
  t.Fatal("mutated original first-failure evidence")
 }
}
