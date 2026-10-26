package main
import (
 "context"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
 "time"
)
func TestProfileTaxonomy(t *testing.T){
 if len(presentations)!=3 || len(profiles)!=3 {t.Fatalf("expected 3x3 profiles")}
 names:=map[string]bool{}
 for _,p:=range profiles{
  if p.Filter=="" || strings.Contains(p.Filter,"[") || names[p.Name] {t.Fatalf("invalid or duplicate preset: %s",p.Name)}
  names[p.Name]=true
 }
 if !names["classic-robot"] || !names["computer"] || !names["social-robot"]{t.Fatalf("required robot profiles missing")}
}
func TestSafetyGates(t *testing.T){
 d:=t.TempDir();out:=filepath.Join(t.TempDir(),"render")
 if e:=validateArgs(d,out,"PRIVATE_FINAL_CHARACTER_VOICE");e==nil{t.Fatal("private asset admission should fail")}
 if e:=validateArgs(d,out,classification);e==nil{t.Fatal("missing sources should fail")}
 for _,v:=range presentations{if e:=os.WriteFile(filepath.Join(d,v+".wav"),[]byte("stub"),0600);e!=nil{t.Fatal(e)}}
 if e:=validateArgs(d,out,classification);e!=nil{t.Fatal(e)}
 if e:=os.Mkdir(out,0700);e!=nil{t.Fatal(e)}
 if e:=validateArgs(d,out,classification);e==nil{t.Fatal("must refuse overwrite")}
}
func TestGenerateNineSyntheticAudioIfFFmpegPresent(t *testing.T){
 if _,e:=exec.LookPath("ffmpeg");e!=nil{t.Skip("FFmpeg not installed")}
 if _,e:=exec.LookPath("ffprobe");e!=nil{t.Skip("FFprobe not installed")}
 d:=t.TempDir()
 for _,v:=range presentations{
  cmd:=exec.Command("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-n","-f","lavfi","-i","sine=frequency=440:sample_rate=24000:duration=0.9","-ar","24000","-ac","1","-c:a","pcm_s16le",filepath.Join(d,v+".wav"))
  if b,e:=cmd.CombinedOutput();e!=nil{t.Fatalf("%s %v %s",v,e,string(b))}
 }
 output:=filepath.Join(t.TempDir(),"render")
 r,e:=render(d,output,"test-tone")
 if e!=nil{t.Fatal(e)}
 if len(r.Clips)!=9{t.Fatalf("wrong number of rendered combinations: %d",len(r.Clips))}
 if _,e:=os.Stat(filepath.Join(output,"receipt.json"));e!=nil{t.Fatal(e)}
 for _,x:=range r.Clips{
  if x.PCMBytes<=4000 || x.AACBytes<=1000 || x.OutputSHA256==x.InputSHA256{t.Fatal("output signal/custody invalid")}
  if x.DurationSeconds<0.8 || x.DurationSeconds>1.0{t.Fatal("duration drift")}
 }
}
func TestInspectDuration(t *testing.T){
 ctx,cancel:=context.WithTimeout(context.Background(),time.Second);defer cancel()
 if _,e:=probeAudio(ctx,filepath.Join(t.TempDir(),"missing.wav"),"pcm_s16le",24000,1);e==nil{t.Fatal("missing input accepted")}
}
