// Command verify validates public synthetic soundtrack stems and mix outputs.
// FFmpeg and eSpeak produce audio; Go owns checks, hashes and machine receipts.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "strings"
)

var files = []string{"ambience_wind.wav", "music_pad.wav", "fauna_chirps.wav", "foley_texture.wav", "human_voice.wav", "robot_voice.wav", "full_mix.wav"}

type Probe struct {
 Streams []struct { SampleRate string `json:"sample_rate"`; Channels int `json:"channels"` } `json:"streams"`
 Format struct { Duration string `json:"duration"` } `json:"format"`
}
type Artifact struct {
 File string `json:"file"`
 SHA256 string `json:"sha256"`
 Bytes int64 `json:"bytes"`
 DurationSeconds float64 `json:"duration_seconds"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 VoiceType string `json:"voices"`
 TTSEngine string `json:"tts_engine"`
 SceneSeconds int `json:"scene_seconds"`
 SampleRate int `json:"sample_rate"`
 Channels int `json:"channels"`
 Stems []string `json:"stems"`
 Artifacts []Artifact `json:"artifacts"`
 Note string `json:"note"`
}
func validate(p Probe, size int64) (float64,error) {
 if len(p.Streams)!=1 || p.Streams[0].SampleRate!="48000" || p.Streams[0].Channels!=2 || size<=1024 {return 0,errors.New("wrong sample rate, channels, stream count or file size")}
 dur,err:=strconv.ParseFloat(p.Format.Duration,64)
 if err!=nil || dur<11.99 || dur>12.01 {return 0,errors.New("wrong/invalid duration")}
 return dur,nil
}
func inspect(path string)(Artifact,error){
 cmd:=exec.Command("ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=sample_rate,channels","-show_entries","format=duration","-of","json",path)
 output,err:=cmd.Output();if err!=nil{return Artifact{},fmt.Errorf("ffprobe %s: %w",filepath.Base(path),err)}
 var probe Probe; if err:=json.Unmarshal(output,&probe);err!=nil{return Artifact{},err}
 f,err:=os.Open(path);if err!=nil{return Artifact{},err};defer f.Close()
 st,err:=f.Stat();if err!=nil{return Artifact{},err}
 duration,err:=validate(probe,st.Size());if err!=nil{return Artifact{},fmt.Errorf("%s: %w",filepath.Base(path),err)}
 h:=sha256.New();if _,err:=io.Copy(h,f);err!=nil{return Artifact{},err}
 return Artifact{File:filepath.Base(path),SHA256:hex.EncodeToString(h.Sum(nil)),Bytes:st.Size(),DurationSeconds:duration},nil
}
func run(args []string) error {
 if len(args)!=2 || strings.TrimSpace(args[1])=="" {return errors.New("usage: verify OUTPUT_DIR TTS_ENGINE")}
 out:=args[0]
 if st,err:=os.Stat(filepath.Join(out,"receipt.json"));err==nil && st!=nil {return errors.New("refusing to replace existing receipt")}
 rec:=Receipt{Schema:"audio-foundry-fixture.v1",Classification:"PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",VoiceType:"generic-espeak",TTSEngine:args[1],SceneSeconds:12,SampleRate:48000,Channels:2,Stems:append([]string(nil),files[:6]...),Note:"Synthetic technical audio-mix fixture, not natural/simulation-accurate or neural output."}
 for _,name:=range files { a,err:=inspect(filepath.Join(out,name));if err!=nil{return err};rec.Artifacts=append(rec.Artifacts,a) }
 b,err:=json.MarshalIndent(rec,"","  ");if err!=nil{return err}
 if err:=os.WriteFile(filepath.Join(out,"receipt.json"),append(b,'\n'),0600);err!=nil{return err}
 fmt.Printf("audio_foundry_fixture_PASS stems=%d mix_sha256=%s\n",len(rec.Stems),rec.Artifacts[len(rec.Artifacts)-1].SHA256)
 return nil
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
