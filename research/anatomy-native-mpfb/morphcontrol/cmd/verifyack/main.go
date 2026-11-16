// verifyack checks a real Godot-process-written local morph-state receipt against
// canonical Go source plan bytes and an ephemeral shared HMAC-SHA256 key.
// It is a disposable RDTE observer; no remote identity or durable consensus.
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "crypto/subtle"
    "encoding/hex"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "math"
    "os"
    "path/filepath"

    ctl "github.com/SemperSupra/stable-character-pipeline/research/anatomy-native-mpfb/morphcontrol"
)

func fail(reason string) {
    fmt.Fprintln(os.Stderr,"R050_GO_ACK_HOLD "+reason)
    os.Exit(12)
}
func read(root,name string) []byte {
    b,e:=os.ReadFile(filepath.Join(root,name))
    if e!=nil||len(b)==0 {fail("missing signed source or Godot receipt "+name)}
    if len(b)>4000000 {fail("unbounded receipt "+name)}
    return b
}
func checkedMAC(payload,tag,key []byte) {
    rawSig,e:=hex.DecodeString(string(tag))
    if e!=nil||len(rawSig)!=32 {fail("bad HMAC encoding")}
    mac:=hmac.New(sha256.New,key)
    _,_=mac.Write(payload)
    if subtle.ConstantTimeCompare(mac.Sum(nil),rawSig)!=1 {
        fail("HMAC mismatch reject receipt")
    }
}
func obj(raw []byte) map[string]any {
    var result map[string]any
    if err:=json.Unmarshal(raw,&result);err!=nil||result==nil {
        fail("malformed JSON plan or engine acknowledgment")
    }
    return result
}
func number(x any) float64 {
    n,ok:=x.(float64)
    if !ok||math.IsNaN(n)||math.IsInf(n,0) {fail("missing or nonfinite numeric field")}
    return n
}
func exact(x any,expected string,label string){
    s,ok:=x.(string)
    if !ok||s!=expected {fail("wrong "+label)}
}
func main(){
    root:=flag.String("root","","disposable Godot project path")
    restart:=flag.Bool("restart",false,"require true Godot restart rehydration")
    flag.Parse()
    if *root==""{fail("missing project root")}
    keyHex:=os.Getenv("R050_HMAC_HEX_KEY")
    key,e:=hex.DecodeString(keyHex)
    if e!=nil||len(key)!=32{fail("invalid ephemeral 256-bit shared key")}
    source:=read(*root,"payload.json")
    sourceTag:=read(*root,"payload.hmac")
    checkedMAC(source,sourceTag,key)
    sourceHash:=sha256.Sum256(source)
    planHash:=hex.EncodeToString(sourceHash[:])
    if string(read(*root,"sha256.txt"))!=planHash+"\n" {
        fail("Go source plan SHA reference mismatch")
    }
    proposal:=obj(source)
    exact(proposal["schema"],ctl.Schema,"canonical plan schema")
    if number(proposal["expected_revision"])!=0{fail("unsupported initial revision")}
    commands,ok:=proposal["sequence"].([]any)
    if !ok||len(commands)!=24{fail("24 target commands required")}
    ackBytes:=read(*root,"engine-ack.json")
    checkedMAC(ackBytes,read(*root,"engine-ack.hmac"),key)
    receipt:=obj(ackBytes)
    exact(receipt["schema"],"r050.godot.engine-ack.v1","Godot receipt schema")
    exact(receipt["status"],"ENGINE_ACK_APPLIED_AND_READ_BACK","Godot receipt status")
    exact(receipt["plan_sha256"],planHash,"plan binding")
    if number(receipt["revision"])!=1||number(receipt["previous_revision"])!=0 ||
       number(receipt["commands"])!=24||number(receipt["targets"])!=3||
       number(receipt["channels_per_target"])!=8{
        fail("wrong committed revision or action count")
    }
    resumed,ok:=receipt["restart_rehydration"].(bool)
    if !ok||resumed!=*restart{fail("Godot process-restart policy mismatch")}
    vals,ok:=receipt["values"].([]any)
    if !ok||len(vals)!=24{fail("Godot did not report 24 observed target values")}
    for i,anyCmd:=range commands{
        cmd,ok:=anyCmd.(map[string]any)
        if !ok{fail("command not object")}
        target:=ctl.Targets[i/8]
        ch:=ctl.Channels[i%8]
        exact(cmd["target"],target,"ordered target")
        exact(cmd["channel"],ch,"source morph channel")
        if number(cmd["index"])!=float64(i%8){fail("source morph index mismatch")}
        desired:=number(cmd["value"])
        observed:=number(vals[i])
        if math.Abs(desired-observed)>0.00001{
            fail("Godot live observed value inconsistent with Go plan")
        }
    }
    digest:=sha256.Sum256(ackBytes)
    fmt.Printf("R050_GO_DURABLE_ACK_RECEIPT status=PASS_NARROW_ENGINE_HMAC_ACK_AND_PROCESS_REHYDRATION commands=24 godot_restart=%v plan_sha=%s ack_sha=%s auth_scope=EPHEMERAL_SHARED_KEY\n",
        resumed,planHash,hex.EncodeToString(digest[:]))
    if !errors.Is(nil,nil) {panic("unreachable")}
}
