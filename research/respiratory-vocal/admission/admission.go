// Package admission implements fail-closed source-neutral JSON ingress for
// PUBLIC synthetic respiratory performance events. Exact source SHA, license,
// privacy and rights review are separate, mandatory public custody gates.
package admission
import ("bytes";"encoding/json";"errors";"fmt";"io";"unicode/utf8"
"github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior")
const MaxPayloadBytes=1<<20
const MaxDepth=32
const MaxItemsPerContainer=4096
// CheckJSON prevents ambiguous state when runtimes otherwise silently accept
// duplicate nested JSON members or replace invalid UTF-8.
func CheckJSON(data []byte)error{
 if len(data)==0||len(data)>MaxPayloadBytes{return errors.New("empty or oversized JSON")}
 if !utf8.Valid(data){return errors.New("invalid UTF-8")}
 d:=json.NewDecoder(bytes.NewReader(data))
 var visit func(int)error
 visit=func(depth int)error{
  if depth>MaxDepth{return errors.New("JSON nested beyond bound")}
  token,err:=d.Token();if err!=nil{return err}
  if delim,ok:=token.(json.Delim);ok{
   switch delim{
   case '{':
    seen:=map[string]bool{}
    for d.More(){
     if len(seen)>=MaxItemsPerContainer{return errors.New("object too large")}
     keyToken,err:=d.Token();if err!=nil{return err}
     key,ok:=keyToken.(string);if !ok{return errors.New("invalid key")}
     if seen[key]{return fmt.Errorf("duplicate member %q",key)}
     seen[key]=true
     if err:=visit(depth+1);err!=nil{return err}
    }
    closing,err:=d.Token();if err!=nil||closing!=json.Delim('}'){return errors.New("bad object closure")}
   case '[':
    n:=0
    for d.More(){
     if n>=MaxItemsPerContainer{return errors.New("array too large")}
     if err:=visit(depth+1);err!=nil{return err};n++
    }
    closing,err:=d.Token();if err!=nil||closing!=json.Delim(']'){return errors.New("bad array closure")}
   default:return errors.New("unmatched JSON close delimiter")
   }
  }
  return nil
 }
 if err:=visit(0);err!=nil{return err}
 if _,err:=d.Token();err!=io.EOF{
  if err!=nil{return fmt.Errorf("bad trailing JSON: %w",err)}
  return errors.New("multiple JSON values")
 }
 return nil
}
func Decode(data []byte)(behavior.Performance,error){
 var p behavior.Performance
 if e:=CheckJSON(data);e!=nil{return p,e}
 d:=json.NewDecoder(bytes.NewReader(data));d.DisallowUnknownFields()
 if e:=d.Decode(&p);e!=nil{return behavior.Performance{},fmt.Errorf("typed JSON: %w",e)}
 if e:=p.Validate();e!=nil{return behavior.Performance{},fmt.Errorf("source event: %w",e)}
 return p,nil
}
