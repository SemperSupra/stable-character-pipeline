// Package observer validates evidence-grounded visual language observations.
// A valid observation is NOT a verified visual/physical/identity or quality claim.
package observer

import (
 "bytes"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "strings"
)

const Schema = "scp.r033.visual-observation.v1"
const Status = "OBSERVATIONS_UNVERIFIED"
const MaxJSONBytes = 1 << 20

type Timebase struct {
 Numerator int `json:"numerator"`
 Denominator int `json:"denominator"`
}

type Model struct {
 ID string `json:"id"`
 WeightsSHA256 string `json:"weights_sha256"`
 MMProjSHA256 string `json:"mmproj_sha256,omitempty"`
 Runtime string `json:"runtime"`
}

type Box struct {
 X float64 `json:"x"`
 Y float64 `json:"y"`
 Width float64 `json:"width"`
 Height float64 `json:"height"`
}

type Region struct {
 Kind string `json:"kind"`
 Box *Box `json:"box,omitempty"`
}

type Observation struct {
 ClaimKind string `json:"claim_kind"`
 Support string `json:"support"`
 Text string `json:"text"`
 FrameIndices []int `json:"frame_indices"`
 FrameSHA256 []string `json:"frame_sha256"`
 Region Region `json:"region"`
 ConceptHypotheses []string `json:"concept_hypotheses,omitempty"`
 ModelReportedScore *float64 `json:"model_reported_score,omitempty"`
}

type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Canonical bool `json:"canonical"`
 SourceClass string `json:"source_class"`
 SourceAdmissionID string `json:"source_admission_id"`
 SourceMediaSHA256 string `json:"source_media_sha256"`
 MediaKind string `json:"media_kind"`
 FrameCount int `json:"frame_count"`
 Timebase Timebase `json:"timebase"`
 ViewID string `json:"view_id"`
 CameraSHA256 string `json:"camera_sha256"`
 Model Model `json:"model"`
 PromptSHA256 string `json:"prompt_sha256"`
 Observations []Observation `json:"observations"`
}

func validSHA(s string)bool{
 if len(s)!=64{return false}
 _,err:=hex.DecodeString(s)
 return err==nil && s==strings.ToLower(s)
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func boxValid(b *Box)bool{
 if b==nil{return false}
 for _,v:=range []float64{b.X,b.Y,b.Width,b.Height}{if !finite(v){return false}}
 return b.X>=0&&b.Y>=0&&b.Width>0&&b.Height>0&&b.X<=1&&b.Y<=1&&b.X+b.Width<=1&&b.Y+b.Height<=1
}

func (r Receipt) Validate()error{
 if r.Schema!=Schema||r.Status!=Status||r.Canonical{return errors.New("INVALID_SCHEMA_STATUS_OR_CANONICAL_ASSERTION")}
 if r.SourceClass!="public_synthetic"&&r.SourceClass!="private_admitted"{return errors.New("INVALID_SOURCE_CLASS")}
 if r.SourceAdmissionID==""||!validSHA(r.SourceMediaSHA256){return errors.New("UNBOUND_SOURCE_ARTIFACT")}
 if r.MediaKind!="image"&&r.MediaKind!="video"{return errors.New("INVALID_MEDIA_KIND")}
 if r.FrameCount<=0||r.FrameCount>1000000{return errors.New("INVALID_FRAME_COUNT")}
 if r.MediaKind=="image" && (r.FrameCount!=1||r.Timebase.Numerator!=0||r.Timebase.Denominator!=0){return errors.New("INVALID_STILL_IMAGE_TIMEBASE")}
 if r.MediaKind=="video" && (r.FrameCount<2||r.Timebase.Numerator<=0||r.Timebase.Numerator>10000000||r.Timebase.Denominator<=0||r.Timebase.Denominator>100000){return errors.New("INVALID_VIDEO_TIMEBASE")}
 if r.ViewID==""||!validSHA(r.CameraSHA256)||!validSHA(r.PromptSHA256){return errors.New("UNBOUND_VIEW_OR_PROMPT")}
 if r.Model.ID==""||r.Model.Runtime==""||!validSHA(r.Model.WeightsSHA256){return errors.New("UNBOUND_MODEL")}
 if r.Model.MMProjSHA256!=""&&!validSHA(r.Model.MMProjSHA256){return errors.New("UNBOUND_MM_PROJECTION")}
 if len(r.Observations)==0||len(r.Observations)>200{return errors.New("INVALID_OBSERVATION_COUNT")}
 for i,o:=range r.Observations{
  validKind:=map[string]bool{"appearance":true,"morphology_visible":true,"pose":true,"face_expression":true,"hair":true,"temporal_behavior":true,"visual_artifact":true}
  if !validKind[o.ClaimKind]{return fmt.Errorf("UNKNOWN_CLAIM_KIND:%d",i)}
  if o.Support!="direct"&&o.Support!="inferred"&&o.Support!="unknown"{return fmt.Errorf("UNKNOWN_SUPPORT:%d",i)}
  if strings.TrimSpace(o.Text)==""||len(o.Text)>2000{return fmt.Errorf("INVALID_DESCRIPTION:%d",i)}
  if len(o.FrameIndices)==0||len(o.FrameIndices)>100||len(o.FrameIndices)!=len(o.FrameSHA256){return fmt.Errorf("INVALID_FRAME_WITNESS:%d",i)}
  previous:=-1
  for j,k:=range o.FrameIndices{
   if k<=previous||k>=r.FrameCount||!validSHA(o.FrameSHA256[j]){return fmt.Errorf("INVALID_SORTED_FRAME_REF:%d",i)}
   previous=k
  }
  if o.ClaimKind=="temporal_behavior"&&(r.MediaKind!="video"||len(o.FrameIndices)<2){return fmt.Errorf("UNSUPPORTED_SINGLE_FRAME_BEHAVIOR:%d",i)}
  if o.Region.Kind=="bbox" {
   if !boxValid(o.Region.Box){return fmt.Errorf("INVALID_BOX:%d",i)}
  }else if o.Region.Kind=="full_frame" {
   if o.Region.Box!=nil{return fmt.Errorf("UNEXPECTED_BOX:%d",i)}
  }else{return fmt.Errorf("MISSING_EVIDENCE_REGION:%d",i)}
  seen:=map[string]bool{}
  for _,hyp:=range o.ConceptHypotheses {
   if strings.TrimSpace(hyp)==""||len(hyp)>128||seen[hyp]{return fmt.Errorf("INVALID_CONCEPT_HYPOTHESIS:%d",i)}
   seen[hyp]=true
  }
  if o.Support=="unknown" && (o.ModelReportedScore!=nil||len(o.ConceptHypotheses)>0){return fmt.Errorf("UNKNOWN_MUST_ABSTAIN:%d",i)}
  if o.ModelReportedScore!=nil&&(!finite(*o.ModelReportedScore)||*o.ModelReportedScore<0||*o.ModelReportedScore>1){return fmt.Errorf("INVALID_UNCALIBRATED_SCORE:%d",i)}
 }
 return nil
}

func scanJSONValue(d *json.Decoder,depth int)error{
 if depth>64{return errors.New("JSON_NESTING_EXCEEDS_BUDGET")}
 tok,err:=d.Token();if err!=nil{return err}
 delim,ok:=tok.(json.Delim);if !ok{return nil}
 switch delim{
 case '{':
  seen:=map[string]bool{}
  for d.More(){
   kt,err:=d.Token();if err!=nil{return err}
   key,ok:=kt.(string);if !ok{return errors.New("OBJECT_KEY_REQUIRED")}
   if seen[key]{return fmt.Errorf("DUPLICATE_JSON_KEY:%s",key)}
   seen[key]=true
   if err:=scanJSONValue(d,depth+1);err!=nil{return err}
  }
  end,err:=d.Token();if err!=nil{return err}
  if end!=json.Delim('}') {return errors.New("BAD_OBJECT_END")}
 case '[':
  for d.More(){if err:=scanJSONValue(d,depth+1);err!=nil{return err}}
  end,err:=d.Token();if err!=nil{return err}
  if end!=json.Delim(']'){return errors.New("BAD_ARRAY_END")}
 default:return errors.New("UNEXPECTED_JSON_DELIMITER")
 }
 return nil
}

func DecodeAndValidate(reader io.Reader)(Receipt,error){
 var r Receipt
 raw,err:=io.ReadAll(io.LimitReader(reader,MaxJSONBytes+1));if err!=nil{return r,err}
 if len(raw)>MaxJSONBytes{return r,errors.New("JSON_EXCEEDS_BYTE_BUDGET")}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if err:=scanJSONValue(d,0);err!=nil{return r,err}
 var trailing any
 if err:=d.Decode(&trailing);err!=io.EOF{
  if err==nil{return r,errors.New("TRAILING_JSON")}
  return r,fmt.Errorf("TRAILING_INVALID_JSON:%w",err)
 }
 d=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&r);err!=nil{return r,err}
 if err:=r.Validate();err!=nil{return r,err}
 return r,nil
}
