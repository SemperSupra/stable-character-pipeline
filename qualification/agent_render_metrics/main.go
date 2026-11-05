// Public-original synthetic rendered-silhouette observer.
// Measures actual decoded PNG pixels. Never executes an optimizer or modifies a model.
package main

import (
  "bytes"
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "errors"
  "fmt"
  "image"
  "image/png"
  "io"
  "math"
  "os"
  "path/filepath"
  "regexp"
  "strings"
)
const maxPNGBytes = 8 << 20
const maxPixels = 2048 * 2048
var shaRE=regexp.MustCompile(`^[0-9a-f]{64}$`)
var idRE=regexp.MustCompile(`^[a-z][a-z0-9_]{2,63}$`)
type Source struct {
  Path string `json:"path"`
  SHA256 string `json:"sha256"`
}
type Request struct {
  Schema string `json:"schema"`
  ExperimentID string `json:"experiment_id"`
  BaselineSHA256 string `json:"baseline_sha256"`
  CandidateSHA256 string `json:"candidate_sha256"`
  SubjectClass string `json:"subject_class"`
  CameraID string `json:"camera_id"`
  FrameIndex int `json:"frame_index"`
  Split string `json:"split"`
  Channel string `json:"mask_channel"`
  Threshold int `json:"threshold"`
  Reference Source `json:"reference"`
  Baseline Source `json:"baseline_render"`
  Candidate Source `json:"candidate_render"`
}
type Comparison struct {
  IoU float64 `json:"iou"`
  Precision float64 `json:"precision"`
  Recall float64 `json:"recall"`
  Intersection int `json:"intersection_pixels"`
  Union int `json:"union_pixels"`
  Foreground int `json:"render_foreground_pixels"`
  Nonbinary int `json:"render_soft_edge_pixels"`
}
type Receipt struct {
  Schema string `json:"schema"`
  ExperimentID string `json:"experiment_id"`
  BaselineSHA256 string `json:"baseline_sha256"`
  CandidateSHA256 string `json:"candidate_sha256"`
  CameraID string `json:"camera_id"`
  FrameIndex int `json:"frame_index"`
  Split string `json:"split"`
  SubjectClass string `json:"subject_class"`
  MaskChannel string `json:"mask_channel"`
  Threshold int `json:"threshold"`
  Width int `json:"width"`
  Height int `json:"height"`
  ReferenceSHA256 string `json:"reference_sha256"`
  BaselineImageSHA256 string `json:"baseline_image_sha256"`
  CandidateImageSHA256 string `json:"candidate_image_sha256"`
  ReferenceForeground int `json:"reference_foreground_pixels"`
  ReferenceSoftEdge int `json:"reference_soft_edge_pixels"`
  Baseline Comparison `json:"baseline"`
  Candidate Comparison `json:"candidate"`
  DeltaIoU float64 `json:"delta_iou"`
  Verdict string `json:"verdict"`
  SourceAttestation string `json:"source_attestation"`
}
func walk(d *json.Decoder)error{
  t,e:=d.Token();if e!=nil{return e}
  delim,ok:=t.(json.Delim);if !ok{return nil}
  switch delim{
  case '{':
    seen:=map[string]bool{}
    for d.More(){
      tok,e:=d.Token();if e!=nil{return e}
      k,ok:=tok.(string);if !ok{return errors.New("non-string JSON key")}
      if seen[k]{return fmt.Errorf("duplicate JSON key %q",k)}
      seen[k]=true
      if e=walk(d);e!=nil{return e}
    }
    _,e=d.Token();return e
  case '[':
    for d.More(){if e=walk(d);e!=nil{return e}}
    _,e=d.Token();return e
  default:return errors.New("bad JSON delimiter")
  }
}
func parse(raw []byte)(Request,error){
  var req Request
  if len(raw)==0||len(raw)>1<<20{return req,errors.New("invalid JSON length")}
  d:=json.NewDecoder(bytes.NewReader(raw))
  if e:=walk(d);e!=nil{return req,e}
  if _,e:=d.Token();e!=io.EOF{return req,errors.New("trailing JSON")}
  d=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
  if e:=d.Decode(&req);e!=nil{return req,e}
  if _,e:=d.Token();e!=io.EOF{return req,errors.New("trailing JSON")}
  return req,validate(req)
}
func validate(q Request)error{
  if q.Schema!="scp.render_masks.v1"{return errors.New("schema mismatch")}
  if !idRE.MatchString(q.ExperimentID)||!idRE.MatchString(q.CameraID){return errors.New("invalid experiment/camera ID")}
  if !shaRE.MatchString(q.BaselineSHA256)||!shaRE.MatchString(q.CandidateSHA256)||q.BaselineSHA256==q.CandidateSHA256{return errors.New("invalid or identical model hashes")}
  if q.SubjectClass!="public_original_synthetic_equine"&&q.SubjectClass!="public_original_synthetic_human"{return errors.New("inadmissible subject")}
  if q.FrameIndex<0||q.FrameIndex>1000000{return errors.New("invalid frame index")}
  if q.Split!="heldout"{return errors.New("heldout split declaration required")}
  if q.Channel!="alpha"&&q.Channel!="luma"{return errors.New("explicit alpha or luma mask channel required")}
  if q.Threshold<1||q.Threshold>254{return errors.New("threshold outside 1..254")}
  for _,s:=range []Source{q.Reference,q.Baseline,q.Candidate}{
    if !filepath.IsLocal(s.Path)||!shaRE.MatchString(s.SHA256){return errors.New("invalid source-relative path or SHA")}
  }
  return nil
}
func load(root string,s Source,channel string,threshold int)([]bool,int,int,int,error){
  if !filepath.IsLocal(s.Path){return nil,0,0,0,errors.New("nonlocal path")}
  rootAbs,e:=filepath.Abs(root);if e!=nil{return nil,0,0,0,e}
  realRoot,e:=filepath.EvalSymlinks(rootAbs);if e!=nil{return nil,0,0,0,e}
  realFile,e:=filepath.EvalSymlinks(filepath.Join(realRoot,s.Path));if e!=nil{return nil,0,0,0,e}
  relative,e:=filepath.Rel(realRoot,realFile)
  if e!=nil||relative==".."||strings.HasPrefix(relative,".."+string(filepath.Separator)){return nil,0,0,0,errors.New("source escapes root")}
  st,e:=os.Stat(realFile);if e!=nil{return nil,0,0,0,e}
  if !st.Mode().IsRegular()||st.Size()>maxPNGBytes{return nil,0,0,0,errors.New("source not bounded regular file")}
  raw,e:=os.ReadFile(realFile);if e!=nil{return nil,0,0,0,e}
  if len(raw)>maxPNGBytes{return nil,0,0,0,errors.New("oversized source")}
  h:=sha256.Sum256(raw);if hex.EncodeToString(h[:])!=s.SHA256{return nil,0,0,0,errors.New("image SHA mismatch")}
  cfg,e:=png.DecodeConfig(bytes.NewReader(raw));if e!=nil{return nil,0,0,0,e}
  if cfg.Width<1||cfg.Height<1||cfg.Width>2048||cfg.Height>2048||cfg.Width*cfg.Height>maxPixels{return nil,0,0,0,errors.New("image dimension limit")}
  img,e:=png.Decode(bytes.NewReader(raw));if e!=nil{return nil,0,0,0,e}
  return mask(img,channel,threshold)
}
func mask(img image.Image,channel string,threshold int)([]bool,int,int,int,error){
  bounds:=img.Bounds();w,h:=bounds.Dx(),bounds.Dy()
  if w<1||h<1||w>2048||h>2048||w*h>maxPixels{return nil,0,0,0,errors.New("invalid dimensions")}
  data:=make([]bool,w*h);soft:=0;limit:=uint32(threshold)*257
  for y:=0;y<h;y++{for x:=0;x<w;x++{
    r,g,b,a:=img.At(bounds.Min.X+x,bounds.Min.Y+y).RGBA()
    var v uint32
    if channel=="alpha"{v=a}else{
      if r!=g||r!=b{return nil,0,0,0,errors.New("luma mask must be grayscale")}
      v=r
    }
    if v>0&&v<65535{soft++}
    data[y*w+x]=v>=limit
  }}
  return data,w,h,soft,nil
}
func score(ref,got []bool,refPixels,soft int)Comparison{
  c:=Comparison{Nonbinary:soft}
  for i,v:=range got{
    if v{c.Foreground++}
    if v&&ref[i]{c.Intersection++}
  }
  c.Union=refPixels+c.Foreground-c.Intersection
  if c.Union>0{c.IoU=float64(c.Intersection)/float64(c.Union)}
  if c.Foreground>0{c.Precision=float64(c.Intersection)/float64(c.Foreground)}
  c.Recall=float64(c.Intersection)/float64(refPixels)
  return c
}
func measure(root string,q Request)(Receipt,error){
  var out Receipt
  ref,w,h,refSoft,e:=load(root,q.Reference,q.Channel,q.Threshold);if e!=nil{return out,fmt.Errorf("reference: %w",e)}
  base,bw,bh,baseSoft,e:=load(root,q.Baseline,q.Channel,q.Threshold);if e!=nil{return out,fmt.Errorf("baseline: %w",e)}
  cand,cw,ch,candSoft,e:=load(root,q.Candidate,q.Channel,q.Threshold);if e!=nil{return out,fmt.Errorf("candidate: %w",e)}
  if w!=bw||w!=cw||h!=bh||h!=ch{return out,errors.New("source dimensions disagree")}
  refCount:=0;for _,v:=range ref{if v{refCount++}}
  if refCount==0{return out,errors.New("reference contains no foreground")}
  bs:=score(ref,base,refCount,baseSoft)
  cs:=score(ref,cand,refCount,candSoft)
  delta:=cs.IoU-bs.IoU
  if math.IsNaN(delta){return out,errors.New("nonfinite metric")}
  out=Receipt{
    Schema:"scp.render_mask_metrics.v1",ExperimentID:q.ExperimentID,
    BaselineSHA256:q.BaselineSHA256,CandidateSHA256:q.CandidateSHA256,
    CameraID:q.CameraID,FrameIndex:q.FrameIndex,Split:q.Split,SubjectClass:q.SubjectClass,
    MaskChannel:q.Channel,Threshold:q.Threshold,Width:w,Height:h,
    ReferenceSHA256:q.Reference.SHA256,BaselineImageSHA256:q.Baseline.SHA256,CandidateImageSHA256:q.Candidate.SHA256,
    ReferenceForeground:refCount,ReferenceSoftEdge:refSoft,Baseline:bs,Candidate:cs,DeltaIoU:delta,
    Verdict:"MEASURED_ONLY_NOT_ANATOMICAL_ACCEPTANCE",
    SourceAttestation:"UNAUTHENTICATED_SPLIT_AND_CAMERA_METADATA",
  }
  return out,nil
}
func run(args []string)error{
  if len(args)==1&&args[0]=="capabilities"{
    return json.NewEncoder(os.Stdout).Encode(map[string]any{"schema":"scp.render_mask_capabilities.v1","operations":[]string{"measure"},"media":"bounded_png_masks","model_mutation":false,"authority":"candidate_only"})
  }
  if len(args)!=3||args[0]!="measure"{return errors.New("usage: agent-render-metrics capabilities | measure ROOT manifest.json")}
  b,e:=os.ReadFile(args[2]);if e!=nil{return e}
  q,e:=parse(b);if e!=nil{return e}
  report,e:=measure(args[1],q);if e!=nil{return e}
  return json.NewEncoder(os.Stdout).Encode(report)
}
func main(){if e:=run(os.Args[1:]);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
