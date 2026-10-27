// Package catalog enforces minimum source-rights and provenance admission.
// Do not mistake this narrow mechanical validator for legal clearance.
package catalog
import ("encoding/json";"errors";"fmt";"strings")
type Entry struct { ID string `json:"id"`; Kind string `json:"kind"`; Source string `json:"source"`; Formats []string `json:"formats"`; Status string `json:"status"`; License string `json:"license"`; Redistribution string `json:"redistribution"`; Publication string `json:"publication"`; Notes string `json:"notes"` }
type Catalog struct { Schema string `json:"schema"`; Entries []Entry `json:"entries"` }
func Validate(data []byte) (Catalog,error) {
 var c Catalog
 if err:=json.Unmarshal(data,&c);err!=nil{return c,err}
 if c.Schema!="scp.mmd.asset-catalog.v1"||len(c.Entries)==0{return c,errors.New("invalid schema or empty entries")}
 seen:=map[string]bool{}
 kinds:=map[string]bool{"fixture":true,"tool":true,"motion-source":true,"asset-index":true}
 statuses:=map[string]bool{"UNTRIED":true,"PROBED":true,"QUALIFIED":true,"REJECTED":true,"HOLD":true}
 for i,e:=range c.Entries {
  prefix:=fmt.Sprintf("entry %d (%s): ",i,e.ID)
  if e.ID==""||seen[e.ID]{return c,errors.New(prefix+"missing or duplicate id")}
  seen[e.ID]=true
  if !kinds[e.Kind]||!statuses[e.Status]{return c,errors.New(prefix+"invalid kind or status")}
  if !strings.HasPrefix(e.Source,"https://")&&!strings.HasPrefix(e.Source,"generated://"){return c,errors.New(prefix+"invalid source scheme")}
  if e.License==""||len(e.Formats)==0{return c,errors.New(prefix+"missing license classification or formats")}
  switch e.Publication {
  case "METADATA_ONLY":
  case "GENERATED_ARTIFACT":
   if e.Kind!="fixture"||!strings.HasPrefix(e.Source,"generated://")||e.Redistribution!="GRANTED"{return c,errors.New(prefix+"generated artifact requires original authored source")}
  case "THIRD_PARTY_ARTIFACT":
   if e.Redistribution!="GRANTED"||strings.HasPrefix(e.Source,"generated://")||e.Status!="QUALIFIED"{return c,errors.New(prefix+"third-party asset lacks redistribution/qualification evidence")}
  default:return c,errors.New(prefix+"invalid publication mode")
  }
 }
 return c,nil
}
