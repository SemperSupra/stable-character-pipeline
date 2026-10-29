// Package editmap applies loss-declared, no-retime cut-only edit lists
// to canonical 48k sample-indexed cues and independent rational VFR PTS.
// It is a source-timeline planner, NOT an encoder or varispeed resampler.
package editmap
import(
 "errors"
 "example.invalid/spatial-contract/avsync"
)
var ErrEdit=errors.New("avsync editmap: gaps, overlaps, reorder or invalid VFR timebase")
const Bound=avsync.MaxDurationSamples

type Span struct{
 SourceStartSample int64
 SourceEndSample int64
 DestinationStartSample int64
}
func ValidateSpans(spans []Span)error{
 if len(spans)==0||len(spans)>4096{return ErrEdit}
 next:=int64(0);sourceEnd:=int64(0)
 for i,s:=range spans{
  if s.SourceStartSample<0||s.SourceEndSample<=s.SourceStartSample||
   s.SourceEndSample>Bound||s.DestinationStartSample!=next||
   (i>0&&s.SourceStartSample<sourceEnd){return ErrEdit}
  size:=s.SourceEndSample-s.SourceStartSample
  if size>Bound-next{return ErrEdit}
  next+=size
  sourceEnd=s.SourceEndSample
 }
 return nil
}
func OutputLength(spans []Span)(int64,error){
 if err:=ValidateSpans(spans);err!=nil{return 0,err}
 s:=spans[len(spans)-1]
 return s.DestinationStartSample+(s.SourceEndSample-s.SourceStartSample),nil
}
// AtSource maps a cue through an edit list; false means it is intentionally
// cut out, not displaced to the next visible frame.
func AtSource(spans []Span,sourceSample int64)(int64,bool,error){
 if err:=ValidateSpans(spans);err!=nil||sourceSample<0{return 0,false,ErrEdit}
 for _,s:=range spans {
  if sourceSample>=s.SourceStartSample && sourceSample<s.SourceEndSample{
   return s.DestinationStartSample+(sourceSample-s.SourceStartSample),true,nil
  }
 }
 return 0,false,nil
}
func before(a,b avsync.Seconds)bool{
 return a.Numerator*b.Denominator<b.Numerator*a.Denominator
}
func ValidateVFR(pts []avsync.Seconds,endSample int64)error {
 if len(pts)==0||len(pts)>10000||endSample<=0||endSample>Bound{return ErrEdit}
 for i,p:=range pts {
  if p.Numerator<0||p.Denominator<=0||p.Denominator>1000000||
   p.Numerator>36000*p.Denominator||
   p.Numerator*avsync.AudioHz>=endSample*p.Denominator{return ErrEdit}
  if i==0&&(p.Numerator!=0){return ErrEdit}
  if i>0&&!before(pts[i-1],p){return ErrEdit}
 }
 return nil
}
// FrameContaining consults the real ordered VFR presentation samples, never
// pretends an average frame rate is a constant presentation period.
func FrameContaining(pts []avsync.Seconds,endSample,sample int64)(int,error){
 if err:=ValidateVFR(pts,endSample);err!=nil||sample<0||sample>=endSample{
  return 0,ErrEdit
 }
 low,high:=0,len(pts)
 for low<high{
  m:=(low+high)/2
  p:=pts[m]
  if p.Numerator*avsync.AudioHz<=sample*p.Denominator{low=m+1}else{high=m}
 }
 if low==0{return 0,ErrEdit}
 return low-1,nil
}
type Cue struct {
 SourceSample int64 `json:"source_sample"`
 DestinationSample int64 `json:"destination_sample"`
 DestinationVideoFrame int `json:"destination_video_frame"`
 Cut bool `json:"cut"`
}
func Map(spans []Span,pts []avsync.Seconds,sourceSample int64)(Cue,error){
 end,err:=OutputLength(spans);if err!=nil{return Cue{},err}
 if err=ValidateVFR(pts,end);err!=nil{return Cue{},err}
 out,keep,err:=AtSource(spans,sourceSample)
 if err!=nil{return Cue{},err}
 if !keep{return Cue{SourceSample:sourceSample,Cut:true,DestinationVideoFrame:-1},nil}
 frame,err:=FrameContaining(pts,end,out)
 if err!=nil{return Cue{},err}
 return Cue{SourceSample:sourceSample,DestinationSample:out,DestinationVideoFrame:frame},nil
}
