package envelope

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "strconv"
)

// RejectDuplicateJSONKeys scans EVERY nested JSON object before evidence is
// interpreted. The standard JSON decoder otherwise accepts last-write-wins
// duplicate keys: a different human/agent reader may silently choose the
// first value and disagree about verdict, source rights or measured data.
// This is a syntax hardening check, not an independent source-hash proof.
func RejectDuplicateJSONKeys(data []byte) error {
    d:=json.NewDecoder(bytes.NewReader(data))
    if err:=rejectValue(d,"$");err!=nil{return err}
    if _,err:=d.Token(); !errors.Is(err,io.EOF) {
        if err!=nil{return fmt.Errorf("invalid trailing JSON: %w",err)}
        return errors.New("additional trailing JSON token")
    }
    return nil
}

func rejectValue(d *json.Decoder,where string) error {
    token,err:=d.Token()
    if err!=nil{return fmt.Errorf("invalid JSON value at %s: %w",where,err)}
    sep,ok:=token.(json.Delim)
    if !ok{return nil}
    switch sep {
    case '{':
        seen:=map[string]bool{}
        for d.More() {
            keyToken,err:=d.Token()
            if err!=nil{return fmt.Errorf("JSON key at %s: %w",where,err)}
            key,ok:=keyToken.(string)
            if !ok{return fmt.Errorf("non-string JSON object key at %s",where)}
            if seen[key] {return fmt.Errorf("duplicate JSON key %q at %s",key,where)}
            seen[key]=true
            if err:=rejectValue(d,where+"."+strconv.Quote(key));err!=nil{return err}
        }
        close,err:=d.Token()
        if err!=nil || close!=json.Delim('}') {return fmt.Errorf("unclosed JSON object at %s",where)}
    case '[':
        index:=0
        for d.More() {
            if err:=rejectValue(d,fmt.Sprintf("%s[%d]",where,index));err!=nil{return err}
            index++
        }
        close,err:=d.Token()
        if err!=nil || close!=json.Delim(']') {return fmt.Errorf("unclosed JSON array at %s",where)}
    default:
        return fmt.Errorf("unexpected JSON delimiter at %s",where)
    }
    return nil
}
