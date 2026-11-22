// control-probe is a synthetic, no-device client for the R0 reducer.
// It never exposes host observations or real audio effects over a public API.
package main

import (
 "bufio"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"

 control "github.com/SemperSupra/stable-character-pipeline/audio-control/control"
)
func run(args []string,in io.Reader,out io.Writer)error{
 if len(args)!=1{return errors.New("usage: control-probe capabilities | simulate")}
 enc:=json.NewEncoder(out)
 enc.SetEscapeHTML(false)
 switch args[0] {
 case "capabilities":
  return enc.Encode(control.Describe())
 case "simulate":
  // Strict parse of each bounded JSON line; no arbitrary event/policy plugins.
  scanner:=bufio.NewScanner(io.LimitReader(in,1<<20))
  scanner.Buffer(make([]byte,4096),1<<16)
  var machine *control.Machine
  count:=0
  for scanner.Scan(){
   b:=scanner.Bytes()
   d:=json.NewDecoder(&boundedReader{data:b})
   d.DisallowUnknownFields()
   var c control.Command
   if err:=d.Decode(&c);err!=nil{return fmt.Errorf("invalid command %d: %w",count+1,err)}
   var extra any
   if err:=d.Decode(&extra);err!=io.EOF{return fmt.Errorf("unexpected trailing JSON on line %d",count+1)}
   if machine==nil{
    m,err:=control.NewMachine(c.SessionID,c.TargetID)
    if err!=nil{return err}
    machine=m
   }
   // Untrusted input CANNOT invoke ObserveHost. Host events are rejected by Submit.
   receipt:=machine.Submit(c)
   if err:=enc.Encode(struct{
    Receipt control.Receipt `json:"receipt"`
    Replayed bool `json:"replayed"`
    Effects []control.Effect `json:"effect_intents,omitempty"`
   }{receipt.Receipt,receipt.Replayed,receipt.Dispatch});err!=nil{return err}
   count++
  }
  if err:=scanner.Err();err!=nil{return err}
  if count==0{return errors.New("no command envelopes supplied")}
  return nil
 default:return errors.New("unknown command; use capabilities or simulate")
 }
}
type boundedReader struct{data []byte}
func(r *boundedReader)Read(p []byte)(int,error){
 if len(r.data)==0{return 0,io.EOF}
 n:=copy(p,r.data)
 r.data=r.data[n:]
 return n,nil
}
func main(){
 if err:=run(os.Args[1:],os.Stdin,os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"control-probe:",err)
  os.Exit(2)
 }
}
