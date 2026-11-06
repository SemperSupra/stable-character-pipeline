// SPDX-License-Identifier: MIT
// SCP read-only source-original synthetic observation-admission gate.
// This validates image BYTES and capture-family separation, not real-world camera independence.
package main
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "image/png"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "strings"
)
var shaRE=regexp.MustCompile(`^[a-f0-9]{64}$`)
var idRE=regexp.MustCompile(`^[a-z][a-z0-9_-]{2,79}$`)
const maxEntries=128
const maxPNG=8<<20
type Observation struct {
 ID string `json:"id"`
 Path string `json:"path"`
 SHA256 string `json:"sha256"`
 SourceRootSHA256 string `json:"source_root_sha256"`
 CaptureFamily string `json:"capture_family"`
 CameraID string `json:"camera_id"`
 FrameTimeNS int64 `json:"frame_time_ns"`
 Split string `json:"split"`
}
type Manifest struct {
 Schema string `json:"schema"`
 SubjectClass string `json:"subject_class"`
 SubjectID string `json:"subject_id"`
 RightsClass string `json:"rights_class"`
 Observations []Observation `json:"observations"`
}
type ImageReceipt struct{
 ID string `json:"id"`
 SHA256 string `json:"sha256"`
 SourceRootSHA256 string `json:"source_root_sha256"`
 CaptureFamily string `json:"capture_family"`
 CameraID string `json:"camera_id"`
 FrameTimeNS int64 `json:"frame_time_ns"`
 Split string `json:"split"`
 Width int `json:"width"`
 Height int `json:"height"`
}
type Receipt struct{
 Schema string `json:"schema"`
 SubjectID string `json:"subject_id"`
 SubjectClass string `json:"subject_class"`
 ManifestSHA256 string `json:"manifest_sha256"`
 Observations []ImageReceipt `json:"observations"`
 Training int `json:"training_count"`
 Heldout int `json:"heldout_count"`
 TrainingFamilies []string `json:"training_families"`
 HeldoutFamilies []string `json:"heldout_families"`
 CaptureFamilySeparation string `json:"capture_family_separation"`
 CameraIndependence string `json:"camera_independence"`
 ExternalPhotoAdmission string `json:"external_photo_admission"`
 ScientificResult string `json:"scientific_result"`
 Mutation bool `json:"mutates_model"`
}
func tokens(d *json.Decoder)error{
 t,e:=d.Token();if e!=nil{return e}
 sep,ok:=t.(json.Delim);if !ok{return nil}
 switch sep{
 case '{':
  keys:=map[string]bool{}
  for d.More(){x,e:=d.Token();if e!=nil{return e};k,ok:=x.(string);if !ok{return errors.New("non-string key")};if keys[k]{return fmt.Errorf("duplicate JSON key: %s",k)};keys[k]=true;if e=tokens(d);e!=nil{return e}}
  _,e:=d.Token();return e
 case '[':
  for d.More(){if e=tokens(d);e!=nil{return e}};_,e:=d.Token();return e
 }
 return errors.New("invalid JSON nesting")
}
func parse(b []byte)(Manifest,error){
 var m Manifest
 if len(b)==0||len(b)>1<<20{return m,errors.New("manifest size outside bounds")}
 d:=json.NewDecoder(bytes.NewReader(b));if e:=tokens(d);e!=nil{return m,e}
 if _,e:=d.Token();e!=io.EOF{return m,errors.New("trailing JSON")}
 d=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if e:=d.Decode(&m);e!=nil{return m,e}
 if _,e:=d.Token();e!=io.EOF{return m,errors.New("trailing JSON")}
 return m,validate(m)
}
func validate(m Manifest)error{
 if m.Schema!="scp.synthetic_observations.v1"{return errors.New("bad schema")}
 if m.SubjectClass!="public_original_synthetic_human"&&m.SubjectClass!="public_original_synthetic_equine"{return errors.New("protected or unknown subject class")}
 if m.RightsClass!="original_self_authored_synthetic"{return errors.New("unadmitted rights class")}
 if !idRE.MatchString(m.SubjectID){return errors.New("bad subject ID")}
 if len(m.Observations)<3||len(m.Observations)>maxEntries{return errors.New("observation count outside limits")}
 ids:=map[string]bool{}
 paths:=map[string]bool{}
 seenCombination:=map[string]bool{}
 familySplit:=map[string]string{}
 rootSplit:=map[string]string{}
 imageSplit:=map[string]string{}
 training,held:=0,0
 for _,o:=range m.Observations{
  if !idRE.MatchString(o.ID)||!idRE.MatchString(o.CaptureFamily)||!idRE.MatchString(o.CameraID){return errors.New("invalid observation/capture/camera ID")}
  if !shaRE.MatchString(o.SHA256)||!shaRE.MatchString(o.SourceRootSHA256){return errors.New("unverified source SHA")}
  if !filepath.IsLocal(o.Path)||filepath.Ext(o.Path)!=".png"{return errors.New("only root-relative PNG paths admitted")}
  if o.FrameTimeNS<0{return errors.New("negative frame timestamp")}
  if o.Split!="training"&&o.Split!="heldout"{return errors.New("only training/heldout")}
  if ids[o.ID]||paths[o.Path]{return errors.New("duplicate observation id/path")}
  ids[o.ID]=true;paths[o.Path]=true
  pair:=o.CaptureFamily+"|"+o.CameraID+"|"+fmt.Sprint(o.FrameTimeNS)
  if seenCombination[pair]{return errors.New("duplicate capture-camera-timestamp")}
  seenCombination[pair]=true
  for _,check:=range []struct{key,which string;table map[string]string}{
   {o.CaptureFamily,"capture_family",familySplit},
   {o.SourceRootSHA256,"source_root",rootSplit},
   {o.SHA256,"image",imageSplit},
  }{
   if prior,ok:=check.table[check.key];ok&&prior!=o.Split{return errors.New("cross-split "+check.which+" leakage")}
   check.table[check.key]=o.Split
  }
  if o.Split=="training"{training++}else{held++}
 }
 if training<2||held<1{return errors.New("training requires >=2, heldout >=1")}
 cam:=map[string]bool{};for _,o:=range m.Observations{if o.Split=="training"{cam[o.CameraID]=true}}
 if len(cam)<2{return errors.New("at least two declared training cameras required")}
 famtrain,famheld:=map[string]bool{},map[string]bool{}
 for _,o:=range m.Observations{if o.Split=="training"{famtrain[o.CaptureFamily]=true}else{famheld[o.CaptureFamily]=true}}
 if len(famtrain)<1||len(famheld)<1{return errors.New("missing independent capture family declaration")}
 return nil
}
func imageBytes(root string,o Observation)(ImageReceipt,error){
 r:=ImageReceipt{}
 base,e:=filepath.Abs(root);if e!=nil{return r,e}
 realRoot,e:=filepath.EvalSymlinks(base);if e!=nil{return r,e}
 file,e:=filepath.EvalSymlinks(filepath.Join(realRoot,o.Path));if e!=nil{return r,e}
 rel,e:=filepath.Rel(realRoot,file)
 if e!=nil||rel==".."||strings.HasPrefix(rel,".."+string(filepath.Separator)){return r,errors.New("PNG escapes source root")}
 stat,e:=os.Stat(file);if e!=nil{return r,e}
 if !stat.Mode().IsRegular()||stat.Size()>maxPNG{return r,errors.New("not regular, or PNG too large")}
 raw,e:=os.ReadFile(file);if e!=nil{return r,e}
 if len(raw)>maxPNG{return r,errors.New("oversized PNG")}
 hash:=sha256.Sum256(raw);if hex.EncodeToString(hash[:])!=o.SHA256{return r,errors.New("source PNG digest mismatch")}
 cfg,e:=png.DecodeConfig(bytes.NewReader(raw));if e!=nil{return r,e}
 if cfg.Width<1||cfg.Height<1||cfg.Width>2048||cfg.Height>2048||cfg.Width*cfg.Height>2048*2048{return r,errors.New("invalid image size")}
 // Decode full PNG, preventing a valid header over malformed image content.
 if _,e=png.Decode(bytes.NewReader(raw));e!=nil{return r,e}
 return ImageReceipt{ID:o.ID,SHA256:o.SHA256,SourceRootSHA256:o.SourceRootSHA256,CaptureFamily:o.CaptureFamily,
 CameraID:o.CameraID,FrameTimeNS:o.FrameTimeNS,Split:o.Split,Width:cfg.Width,Height:cfg.Height},nil
}
func admit(root string,raw []byte)(Receipt,error){
 m,e:=parse(raw);if e!=nil{return Receipt{},e}
 hash:=sha256.Sum256(raw)
 r:=Receipt{Schema:"scp.synthetic_observation_receipt.v1",SubjectID:m.SubjectID,SubjectClass:m.SubjectClass,ManifestSHA256:hex.EncodeToString(hash[:]),
 CaptureFamilySeparation:"DECLARED_SPLIT_BARRIER_VERIFIED",CameraIndependence:"UNKNOWN_NO_EXTERNAL_CALIBRATION",
 ExternalPhotoAdmission:"NOT_RUN",ScientificResult:"UNKNOWN",Mutation:false}
 ftrain,fheld:=map[string]bool{},map[string]bool{}
 for _,o:=range m.Observations{
  result,e:=imageBytes(root,o);if e!=nil{return Receipt{},fmt.Errorf("image %s: %w",o.ID,e)}
  r.Observations=append(r.Observations,result)
  if o.Split=="training"{r.Training++;ftrain[o.CaptureFamily]=true}else{r.Heldout++;fheld[o.CaptureFamily]=true}
 }
 for f:=range ftrain{r.TrainingFamilies=append(r.TrainingFamilies,f)}
 for f:=range fheld{r.HeldoutFamilies=append(r.HeldoutFamilies,f)}
 sort.Strings(r.TrainingFamilies);sort.Strings(r.HeldoutFamilies)
 sort.Slice(r.Observations,func(i,j int)bool{return r.Observations[i].ID<r.Observations[j].ID})
 return r,nil
}
func main(){
 if len(os.Args)==2&&os.Args[1]=="capabilities"{fmt.Println(`{"schema":"scp.synthetic_observation_capabilities.v1","operations":["admit"],"external_sources":false,"model_mutation":false}`);return}
 if len(os.Args)!=4||os.Args[1]!="admit"{fmt.Fprintln(os.Stderr,"usage: obs-admit capabilities | admit ROOT manifest.json");os.Exit(2)}
 b,e:=os.ReadFile(os.Args[3]);if e==nil{var out Receipt;out,e=admit(os.Args[2],b);if e==nil{e=json.NewEncoder(os.Stdout).Encode(out)}}
 if e!=nil{fmt.Fprintln(os.Stderr,"REJECT_OBSERVATION:",e);os.Exit(2)}
}
