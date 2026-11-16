package admission

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "regexp"
    "strings"
)

// Reject ambiguous JSON representations before typed parsing. In particular,
// encoding/json normally takes the last value on duplicate nested object keys.
func rejectNestedDuplicates(buf []byte) error {
    d:=json.NewDecoder(bytes.NewReader(buf))
    var visit func(int) error
    visit = func(depth int) error {
        if depth>32{return errors.New("JSON nesting exceeds depth limit")}
        tok,err:=d.Token();if err!=nil{return err}
        switch tok {
        case json.Delim('{'):
            seen:=map[string]bool{}
            for d.More(){
                t,err:=d.Token();if err!=nil{return err}
                k,ok:=t.(string);if !ok{return errors.New("invalid JSON member name")}
                if seen[k]{return fmt.Errorf("duplicate nested JSON member: %s",k)}
                seen[k]=true
                if err:=visit(depth+1);err!=nil{return err}
            }
            t,err:=d.Token();if err!=nil||t!=json.Delim('}'){return errors.New("bad object closure")}
        case json.Delim('['):
            for d.More(){if err:=visit(depth+1);err!=nil{return err}}
            t,err:=d.Token();if err!=nil||t!=json.Delim(']'){return errors.New("bad array closure")}
        default:
            if _,ok:=tok.(json.Delim);ok{return errors.New("unexpected JSON delimiter")}
        }
        return nil
    }
    if err:=visit(0);err!=nil{return err}
    if _,err:=d.Token();err!=io.EOF{return errors.New("extra JSON content")}
    return nil
}

var safeID=regexp.MustCompile(`^[a-z0-9][a-z0-9._-]{0,95}$`)
var knownIntentFields=map[string]bool{
 "schema":true,"intent_id":true,"revision":true,"classification":true,
 "target_kind":true,"language":true,"description":true,"desired_attributes":true,
 "undesired_attributes":true,"hard_constraints":true,"reference_examples":true,
 "audiences":true,"human_review_policy":true,"parameter_bounds":true,
 "source_revision":true,
}
var kinds=map[string]bool{"speech":true,"vocalization":true,"mechanical":true,"foley":true,"ambience":true,"music":true,"scene":true}

func requireJSONString(o map[string]json.RawMessage,k string)(string,error){
    var s string
    b,ok:=o[k];if !ok{return "",fmt.Errorf("missing %s",k)}
    if err:=json.Unmarshal(b,&s);err!=nil||strings.TrimSpace(s)==""{return "",fmt.Errorf("invalid %s",k)}
    return s,nil
}
func validateIntentShape(o map[string]json.RawMessage) error {
    for k:=range o{if !knownIntentFields[k]{return fmt.Errorf("unsupported intent property %s",k)}}
    id,err:=requireJSONString(o,"intent_id");if err!=nil{return err}
    if !safeID.MatchString(id){return errors.New("invalid intent_id")}
    var rev int
    b,ok:=o["revision"];if !ok||json.Unmarshal(b,&rev)!=nil||rev<1{return errors.New("revision must be positive integer")}
    kind,err:=requireJSONString(o,"target_kind");if err!=nil||!kinds[kind]{return errors.New("invalid target_kind")}
    desc,err:=requireJSONString(o,"description");if err!=nil||len(desc)>4096{return errors.New("invalid description length")}
    if raw,ok:=o["language"];ok{
        var lang string
        if json.Unmarshal(raw,&lang)!=nil||(lang!="en"&&lang!="de"&&lang!="th"&&lang!="und"){return errors.New("invalid language")}
    }
    if raw,ok:=o["reference_examples"];ok{
        var refs []struct{
            Role string `json:"role"`
            ArtifactSHA256 string `json:"artifact_sha256"`
            Classification string `json:"classification"`
            RightsReceiptRef string `json:"rights_receipt_ref"`
        }
        decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
        if err:=decoder.Decode(&refs);err!=nil||refs==nil||len(refs)>16{return errors.New("invalid references")}
        for _,r:=range refs{
            if (r.Role!="positive"&&r.Role!="negative"&&r.Role!="contrast")||r.Classification!=Public||!isSHA(r.ArtifactSHA256)||strings.TrimSpace(r.RightsReceiptRef)==""{return errors.New("invalid or private reference")}
        }
    }
    return nil
}
