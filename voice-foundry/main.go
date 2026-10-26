// Public Voice Foundry: a reproducible SYNTHETIC candidate speech workcell.
// Never pass real-person or final character identity material to public CI.
package main

import (
  "context"
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "errors"
  "flag"
  "fmt"
  "io"
  "os"
  "os/exec"
  "path/filepath"
  "strings"
  "time"
)

type Config struct {
  Engine string
  Out string
  Voice string
  Text string
  Rate int
  Pitch int
}

func (c Config) Validate() error {
  if strings.TrimSpace(c.Text)=="" || len(c.Text)>5000 { return errors.New("text must be 1..5000 bytes") }
  if c.Rate<80 || c.Rate>450 || c.Pitch<0 || c.Pitch>99 { return errors.New("speed or pitch out of range") }
  if strings.TrimSpace(c.Out)=="" { return errors.New("new output filename required") }
  if c.Voice=="" || len(c.Voice)>80 || strings.HasPrefix(c.Voice,"-") || strings.ContainsAny(c.Voice," \t\r\n") { return errors.New("invalid voice name") }
  if c.Engine!="auto" && c.Engine!="espeak" && c.Engine!="espeak-ng" { return errors.New("unsupported engine") }
  return nil
}
func findEngine(choice string)(string,error){
  if choice!="auto" { return exec.LookPath(choice) }
  for _, name:= range []string{"espeak-ng","espeak"}{
    if p,e:=exec.LookPath(name);e==nil{return p,nil}
  }
  return "",errors.New("install espeak-ng or espeak")
}
func makeVoice(ctx context.Context,c Config)(map[string]interface{},error){
  if err:=c.Validate();err!=nil{return nil,err}
  engine,err:=findEngine(c.Engine);if err!=nil{return nil,err}
  out,err:=filepath.Abs(c.Out);if err!=nil{return nil,err}
  if _,err:=os.Lstat(out);err==nil{return nil,errors.New("refusing to overwrite existing file")}else if !os.IsNotExist(err){return nil,err}
  if info,err:=os.Stat(filepath.Dir(out));err!=nil || !info.IsDir(){return nil,errors.New("output parent directory must exist")}
  tmp,err:=os.CreateTemp(filepath.Dir(out),".candidate-*.wav");if err!=nil{return nil,err}
  tmpPath:=tmp.Name();_ = tmp.Close();defer os.Remove(tmpPath)
  cmd:=exec.CommandContext(ctx,engine,"-v",c.Voice,"-s",fmt.Sprint(c.Rate),"-p",fmt.Sprint(c.Pitch),"-w",tmpPath)
  cmd.Stdin=strings.NewReader(c.Text)
  if result,err:=cmd.CombinedOutput();err!=nil{return nil,fmt.Errorf("synthesis failed: %w (%s)",err,strings.TrimSpace(string(result)))}
  src,err:=os.Open(tmpPath);if err!=nil{return nil,err}
  defer src.Close()
  header:=make([]byte,12)
  if _,err:=io.ReadFull(src,header);err!=nil{return nil,err}
  if string(header[:4])!="RIFF" || string(header[8:])!="WAVE"{return nil,errors.New("not WAV output")}
  stat,err:=src.Stat();if err!=nil{return nil,err}
  if stat.Size()<=44{return nil,errors.New("empty audio")}
  if _,err:=src.Seek(0,io.SeekStart);err!=nil{return nil,err}
  dst,err:=os.OpenFile(out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return nil,err}
  sha:=sha256.New()
  _,copyErr:=io.Copy(io.MultiWriter(dst,sha),src)
  closeErr:=dst.Close()
  if copyErr!=nil || closeErr!=nil{_ = os.Remove(out);return nil,errors.New("could not finalize WAV")}
  textHash:=sha256.Sum256([]byte(c.Text))
  return map[string]interface{}{
    "schema":"voice-candidate.v1",
    "classification":"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",
    "engine":filepath.Base(engine),"voice":c.Voice,
    "text_sha256":hex.EncodeToString(textHash[:]),
    "wav_sha256":hex.EncodeToString(sha.Sum(nil)),
    "bytes":stat.Size(),
  },nil
}
func main(){
  c:=Config{}
  flag.StringVar(&c.Engine,"engine","auto","auto, espeak-ng, or espeak")
  flag.StringVar(&c.Out,"out","","new output WAV path")
  flag.StringVar(&c.Voice,"voice","en-us","engine voice ID")
  flag.StringVar(&c.Text,"text","","speech text")
  flag.IntVar(&c.Rate,"rate",165,"speech rate, 80..450")
  flag.IntVar(&c.Pitch,"pitch",55,"pitch, 0..99")
  flag.Parse()
  ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
  result,err:=makeVoice(ctx,c)
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
  _=json.NewEncoder(os.Stdout).Encode(result)
}
