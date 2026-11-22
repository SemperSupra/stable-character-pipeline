package offlinecontrol

import (
 "errors"
 "os"
 "os/exec"
 "testing"
)

// A missing durable success receipt is not equivalent to a fresh operation.
// This negative test explicitly holds the boundary against false 'exactly once'.
func TestCrashAfterWAVBeforeReceiptDoesNotOverwrite(t *testing.T){
 if _,e:=exec.LookPath("ffmpeg");e!=nil{t.Skip("ffmpeg absent")}
 if _,e:=exec.LookPath("ffprobe");e!=nil{t.Skip("ffprobe absent")}
 m,assets,output:=fixture(t)
 planned,e:=Prepare(m,assets,output);if e!=nil{t.Fatal(e)}
 first,e:=planned.Execute();if e!=nil{t.Fatal(e)}
 if first.OutputSHA256==""{t.Fatal("no exact output SHA")}
 // Simulate process crash: original in-memory Prepared and receipt are gone,
 // but an output file remains. There is no persisted exactly-once journal.
 again,e:=Prepare(m,assets,output)
 if !errors.Is(e,ErrOutputExists)||again!=nil{t.Fatalf("incomplete recovery falsely accepted: %v",e)}
 okay,e:=VerifyOutput(output,first.OutputSHA256)
 if e!=nil||!okay{t.Fatalf("failed to verify existing output: %v",e)}
}
func TestTamperedOrTruncatedOutputNeverSilentlyReplayed(t *testing.T){
 if _,e:=exec.LookPath("ffmpeg");e!=nil{t.Skip("ffmpeg absent")}
 if _,e:=exec.LookPath("ffprobe");e!=nil{t.Skip("ffprobe absent")}
 m,assets,output:=fixture(t)
 p,e:=Prepare(m,assets,output);if e!=nil{t.Fatal(e)}
 receipt,e:=p.Execute();if e!=nil{t.Fatal(e)}
 if e:=os.Truncate(output,64);e!=nil{t.Fatal(e)}
 if ok,e:=VerifyOutput(output,receipt.OutputSHA256);ok||e==nil{
  t.Fatal("truncated audio incorrectly verified as original output")
 }
 if _,e:=Prepare(m,assets,output);!errors.Is(e,ErrOutputExists){
  t.Fatalf("corrupted output overwritten instead of quarantined: %v",e)
 }
}
func TestOrphanOutputWithoutAnyTrustedReceiptCannotBeAdmitted(t *testing.T){
 m,root,out:=fixture(t)
 if e:=os.WriteFile(out,[]byte("orphan incomplete WAV"),0600);e!=nil{t.Fatal(e)}
 if _,e:=Prepare(m,root,out);!errors.Is(e,ErrOutputExists){
  t.Fatalf("untrusted orphan WAV silently admitted: %v",e)
 }
}
