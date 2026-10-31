// scoreclock provides original-synthetic, non-mutating music/dance time mapping.
// -capabilities is suitable for automation/agent discovery, not full UI acceptance.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"

 editable "example.invalid/audio-editable"
)
func execute(args []string,w io.Writer)error{
 fs:=flag.NewFlagSet("scoreclock",flag.ContinueOnError);fs.SetOutput(io.Discard)
 capability:=fs.Bool("capabilities",false,"print machine readable capabilities")
 fixture:=fs.Bool("fixture",false,"eight-bar original synthetic two-actor plan")
 projectPath:=fs.String("project","","editable_audio.v1 JSON project")
 requestPath:=fs.String("request","","original synthetic choreography request JSON")
 if err:=fs.Parse(args);err!=nil{return err}
 if fs.NArg()!=0{return errors.New("unexpected arguments")}
 enc:=json.NewEncoder(w);enc.SetIndent("","  ")
 if *capability{if *fixture||*projectPath!=""||*requestPath!=""{return errors.New("capability mode accepts no other input")};return enc.Encode(editable.Capability())}
 if *fixture {
  if *projectPath!=""||*requestPath!=""{return errors.New("fixture cannot override user inputs")}
  p:=editable.EightBarFixtureProject()
  tempo:=[]editable.TempoPoint{{AtTick:0,BPM:120},{AtTick:16*editable.PPQ,BPM:90}}
  events:=[]editable.ChoreographyEvent{
   {ID:"intro",ActorID:"actor-a",Role:"leader",Action:"step",Tick:0},
   {ID:"response",ActorID:"actor-b",Role:"follower",Action:"cross",Tick:editable.PPQ/2},
   {ID:"change",ActorID:"actor-a",Role:"leader",Action:"turn",Tick:16*editable.PPQ},
   {ID:"reply",ActorID:"actor-b",Role:"follower",Action:"clap",Tick:17*editable.PPQ},
  }
  r,err:=editable.FormatScoreRequest(p,tempo,events);if err!=nil{return err}
  plan,err:=editable.AlignOriginalSynthetic(p,r);if err!=nil{return err}
  return enc.Encode(plan)
 }
 if *projectPath==""||*requestPath==""{return errors.New("project and request required")}
 p,err:=editable.Read(*projectPath);if err!=nil{return err}
 f,err:=os.Open(*requestPath);if err!=nil{return err};defer f.Close()
 decoder:=json.NewDecoder(io.LimitReader(f,1<<20));decoder.DisallowUnknownFields()
 var req editable.ScoreRequest
 if err:=decoder.Decode(&req);err!=nil{return err}
 var more any;if err:=decoder.Decode(&more);err!=io.EOF{return errors.New("trailing request JSON")}
 plan,err:=editable.AlignOriginalSynthetic(p,req);if err!=nil{return err}
 return enc.Encode(plan)
}
func main(){if err:=execute(os.Args[1:],os.Stdout);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
