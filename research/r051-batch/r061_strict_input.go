// R061 strict bounded offline JSON admission for source-safe actor receipt CLI.
// Duplicate keys are rejected at every nesting level, not silently last-wins.
package main

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "os"
)

const maxLocalReceiptBytes = 1 << 20

func jsonValue(dec *json.Decoder, depth int) error {
    if depth>64{return errors.New("nested JSON too deep")}
    t,err:=dec.Token()
    if err!=nil{return err}
    delim,ok:=t.(json.Delim)
    if !ok{return nil}
    switch delim {
    case '{':
        seen:=map[string]struct{}{}
        for dec.More(){
            key,err:=dec.Token()
            if err!=nil{return err}
            name,ok:=key.(string)
            if !ok{return errors.New("object key is not a string")}
            if _,present:=seen[name];present{return fmt.Errorf("duplicate JSON key %q",name)}
            seen[name]=struct{}{}
            if err:=jsonValue(dec,depth+1);err!=nil{return err}
        }
        end,err:=dec.Token()
        if err!=nil{return err}
        if end!=json.Delim('}') {return errors.New("unclosed object")}
    case '[':
        for dec.More(){
            if err:=jsonValue(dec,depth+1);err!=nil{return err}
        }
        end,err:=dec.Token()
        if err!=nil{return err}
        if end!=json.Delim(']'){return errors.New("unclosed array")}
    default:return errors.New("unexpected JSON delimiter")
    }
    return nil
}
func decodeLocalBounded(file string, out interface{}) error {
    f,err:=os.Open(file)
    if err!=nil{return err}
    defer f.Close()
    raw,err:=io.ReadAll(io.LimitReader(f,maxLocalReceiptBytes+1))
    if err!=nil{return err}
    if len(raw)==0||len(raw)>maxLocalReceiptBytes{
        return errors.New("invalid bounded input byte count")
    }
    guard:=json.NewDecoder(bytes.NewReader(raw))
    guard.UseNumber()
    if err:=jsonValue(guard,0);err!=nil{return err}
    if _,err:=guard.Token();err!=io.EOF{
        return errors.New("extra data after JSON document")
    }
    decoder:=json.NewDecoder(bytes.NewReader(raw))
    decoder.DisallowUnknownFields()
    if err:=decoder.Decode(out);err!=nil{return err}
    if _,err:=decoder.Token();err!=io.EOF{
        return errors.New("JSON has trailing content")
    }
    return nil
}
