// floratraits is the public, stdlib-only Flora organ provenance admission gate.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math"
 "os"
 "strings"
)
type Evidence struct {
 Origin string `json:"origin"`
 UncertaintyM float64 `json:"uncertainty_m"`
 URI string `json:"reference_uri,omitempty"`
 SourceSHA256 string `json:"reference_sha256,omitempty"`
 Rights string `json:"reference_rights,omitempty"`
}
type Traits struct {
 LengthM float64 `json:"length_m"`
 WidthM float64 `json:"width_m,omitempty"`
 ThicknessM float64 `json:"thickness_m,omitempty"`
 BaseRadiusM float64 `json:"base_radius_m,omitempty"`
 TipRadiusM float64 `json:"tip_radius_m,omitempty"`
 Venation string `json:"venation,omitempty"`
}
type Organ struct {
 ID string `json:"id"`
 MTGVertex int `json:"mtg_vertex"`
 ParentID string `json:"parent_id,omitempty"`
 Kind string `json:"kind"`
 Attachment [3]float64 `json:"attachment_xyz_m"`
 Traits Traits `json:"traits"`
 Evidence Evidence `json:"evidence"`
}
type Document struct {
 Schema string `json:"schema"`
 Unit string `json:"units"`
 Axis string `json:"coordinate_system"`
 TaxonLabel string `json:"taxon_label"`
 TaxonStatus string `json:"taxon_status"`
 SourceRights string `json:"source_rights"`
 Organs []Organ `json:"organs"`
}
type Receipt struct {
 Schema string `json:"schema"`
 InputSHA256 string `json:"input_sha256"`
 Organs int `json:"organ_count"`
 Stems int `json:"stem_count"`
 Leaves int `json:"leaf_count"`
 Status string `json:"taxon_status"`
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func extent(v,max float64)bool{return finite(v)&&v>0&&v<=max}
func referenceOK(e Evidence)bool{
 if e.Rights!="RIGHTS_CLEARED_REFERENCE"||!(strings.HasPrefix(e.URI,"https://")||strings.HasPrefix(e.URI,"doi:"))||len(e.SourceSHA256)!=64{return false}
 _,err:=hex.DecodeString(e.SourceSHA256);return err==nil
}
func validate(d Document)(Receipt,error){
 fail:=func(reason string)(Receipt,error){return Receipt{},errors.New(reason)}
 if d.Schema!="scp.flora.organ-traits.v1"||d.Unit!="m"||d.Axis!="Z_UP_RIGHT_HANDED"{return fail("schema, SI metres or Z-up axis invalid")}
 if d.TaxonLabel==""||(d.TaxonStatus!="illustrative"&&d.TaxonStatus!="verified"){return fail("taxon claim not explicitly classified")}
 if d.SourceRights!="ORIGINAL_SYNTHETIC"&&d.SourceRights!="RIGHTS_CLEARED_REFERENCE"{return fail("rights must be explicit")}
 if len(d.Organs)==0||len(d.Organs)>128{return fail("organ count out of bounds")}
 ids:=map[string]Organ{};vids:=map[int]bool{};stems,leaves,roots,measured:=0,0,0,0
 for _,o:=range d.Organs{
  if o.ID==""||o.MTGVertex<=0||vids[o.MTGVertex]{return fail("missing/duplicate organ vertex")}
  if _,ok:=ids[o.ID];ok{return fail("duplicate organ ID")}
  ids[o.ID]=o;vids[o.MTGVertex]=true
  for _,v:=range o.Attachment{if !finite(v)||math.Abs(v)>100{return fail("attachment out of bounds")}}
  if !extent(o.Traits.LengthM,50)||!finite(o.Evidence.UncertaintyM)||o.Evidence.UncertaintyM<0{return fail("invalid organ dimensions/uncertainty")}
  if o.Evidence.Origin=="measured" {
   measured++
   if d.SourceRights!="RIGHTS_CLEARED_REFERENCE"||!referenceOK(o.Evidence){return fail("measured trait without independent rights/URI/hash")}
  } else if o.Evidence.Origin!="synthetic"{return fail("unsupported evidence origin")}
  switch o.Kind{
  case "stem":
   stems++
   if !extent(o.Traits.BaseRadiusM,10)||!extent(o.Traits.TipRadiusM,10)||o.Traits.TipRadiusM>o.Traits.BaseRadiusM{return fail("stem taper invalid")}
   if o.Traits.Venation!=""||o.Traits.WidthM!=0||o.Traits.ThicknessM!=0{return fail("stem contains leaf traits")}
  case "leaf":
   leaves++
   if !extent(o.Traits.WidthM,10)||!extent(o.Traits.ThicknessM,2)||o.Traits.BaseRadiusM!=0||o.Traits.TipRadiusM!=0{return fail("leaf blade invalid")}
   if o.Traits.Venation!="unknown"&&o.Traits.Venation!="parallel"&&o.Traits.Venation!="pinnate"&&o.Traits.Venation!="palmate"{return fail("leaf venation unclassified")}
  default:return fail("unsupported organ type")
  }
 }
 if stems==0||leaves==0{return fail("stem and leaf contract required")}
 if d.TaxonStatus=="verified"&&(measured!=len(d.Organs)||d.SourceRights!="RIGHTS_CLEARED_REFERENCE"){return fail("verified taxon needs sourced measurements for every organ")}
 for _,o:=range d.Organs {
  if o.ParentID==""{
   roots++
   if o.Kind!="stem"{return fail("unattached leaf root")}
  }else{
   parent,ok:=ids[o.ParentID]
   if !ok||parent.ID==o.ID{return fail("missing/self-parent MTG lineage")}
   if o.Kind=="leaf"&&parent.Kind!="stem"{return fail("leaf cannot attach to leaf")}
  }
  walked:=map[string]bool{o.ID:true};cur:=o
  for cur.ParentID!=""{
   if walked[cur.ParentID]{return fail("MTG parent cycle")}
   walked[cur.ParentID]=true;cur=ids[cur.ParentID]
  }
 }
 if roots!=1{return fail("requires exactly one stem root")}
 return Receipt{Schema:"scp.flora.organ-traits.receipt.v1",Organs:len(d.Organs),Stems:stems,Leaves:leaves,Status:d.TaxonStatus},nil
}
func parse(data []byte)(Document,error){
 d:=Document{}
 dec:=json.NewDecoder(bytes.NewReader(data));dec.DisallowUnknownFields()
 if err:=dec.Decode(&d);err!=nil{return d,err}
 var excess any
 if err:=dec.Decode(&excess);err!=io.EOF{return d,errors.New("trailing JSON content")}
 return d,nil
}
func admit(data []byte)(Receipt,error){
 d,err:=parse(data);if err!=nil{return Receipt{},err}
 r,err:=validate(d);if err!=nil{return r,err}
 sum:=sha256.Sum256(data);r.InputSHA256=hex.EncodeToString(sum[:]);return r,nil
}
func main(){
 input:=flag.String("input","","public JSON organ-trait document")
 flag.Parse()
 if *input==""{fmt.Fprintln(os.Stderr,"-input is required");os.Exit(2)}
 f,err:=os.Open(*input);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 defer f.Close()
 b,err:=io.ReadAll(io.LimitReader(f,262145))
 if err!=nil||len(b)>262144{fmt.Fprintln(os.Stderr,"invalid/oversized input");os.Exit(2)}
 r,err:=admit(b);if err!=nil{fmt.Fprintln(os.Stderr,"FLORA_TRAIT_REJECTED:",err);os.Exit(1)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 if err:=enc.Encode(r);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
