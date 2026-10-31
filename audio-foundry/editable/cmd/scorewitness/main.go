// scorewitness produces a new immutable original-synthetic PCM/MIDI/MusicXML
// evidence directory. It does not replace Audio Foundry's source project.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 editable "example.invalid/audio-editable"
)
func run(args []string)error{
 fs:=flag.NewFlagSet("scorewitness",flag.ContinueOnError)
 out:=fs.String("out","","new evidence directory")
 if e:=fs.Parse(args);e!=nil{return e}
 if *out==""||fs.NArg()!=0{return errors.New("out required, no positional args")}
 if _,e:=os.Lstat(*out);e==nil{return errors.New("refuse existing output directory")}else if !os.IsNotExist(e){return e}
 p:=editable.EightBarFixtureProject()
 r,e:=editable.FormatScoreRequest(p,[]editable.TempoPoint{{AtTick:0,BPM:120},{AtTick:16*editable.PPQ,BPM:90}},
 []editable.ChoreographyEvent{{ID:"intro",ActorID:"actor-a",Role:"leader",Action:"step",Tick:0},
 {ID:"response",ActorID:"actor-b",Role:"follower",Action:"cross",Tick:editable.PPQ/2},
 {ID:"change",ActorID:"actor-a",Role:"leader",Action:"turn",Tick:16*editable.PPQ},
 {ID:"reply",ActorID:"actor-b",Role:"follower",Action:"clap",Tick:17*editable.PPQ}})
 if e!=nil{return e}
 wav,midi,xml,receipt,e:=editable.RenderOriginalSyntheticTempoWitness(p,r)
 if e!=nil{return e}
 csd,e:=editable.CsoundTempoDiagnostic(p,r);if e!=nil{return e}
 source,e:=p.Bytes();if e!=nil{return e}
 plan,e:=editable.AlignOriginalSynthetic(p,r);if e!=nil{return e}
 planJSON,e:=json.MarshalIndent(plan,"","  ");if e!=nil{return e}
 receiptJSON,e:=json.MarshalIndent(receipt,"","  ");if e!=nil{return e}
 if e:=os.Mkdir(*out,0700);e!=nil{return e}
 success:=false
 defer func(){if !success{os.RemoveAll(*out)}}()
 files:=[]struct{name string;content []byte}{
  {"source.json",source},{"original-synthetic-tempo.mid",midi},
  {"original-synthetic-tempo.musicxml",xml},{"original-synthetic-onsets.wav",wav},
  {"time-map.json",append(planJSON,'\n')},{"receipt.json",append(receiptJSON,'\n')},
  {"original-synthetic-csound-transport.csd",csd},
 }
 for _,f:=range files{if e:=editable.WriteNew(filepath.Join(*out,f.name),f.content);e!=nil{return e}}
 success=true
 return nil
}
func main(){if e:=run(os.Args[1:]);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
