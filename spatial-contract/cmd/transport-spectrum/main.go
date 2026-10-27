// transport-spectrum is an independent Go/FFmpeg postrender oracle for
// original source clip-relative seek distinct from scene absolute mute gates.
// It verifies a 690Hz synthetic B clip phase shift caused by 512 source frames,
// while A's 410Hz contribution remains unchanged.
package main

import (
 "encoding/binary"
 "errors"
 "fmt"
 "math"
 "math/cmplx"
 "os"
 "os/exec"
)
const(
 rate=48000
 frames=48000
 channels=6
 gateStart=24575
 gateStop=36865
 sourceSeek=512
)
func decode(path string)([]float32,error){
 b,e:=exec.Command("ffmpeg","-nostdin","-hide_banner","-v","error","-xerror","-i",path,"-f","f32le","-acodec","pcm_f32le","-").Output()
 if e!=nil{return nil,e}
 if len(b)!=frames*channels*4{return nil,errors.New("wrong decoded scene duration or channel count")}
 v:=make([]float32,frames*channels)
 for i:=range v{
  x:=math.Float32frombits(binary.LittleEndian.Uint32(b[i*4:i*4+4]))
  if math.IsNaN(float64(x))||math.IsInf(float64(x),0){return nil,errors.New("nonfinite PCM output")}
  v[i]=x
 }
 return v,nil
}
func phasor(samples []float32,hz float64,ch int)complex128{
 re,im:=0.0,0.0
 // Gate middle: exclude onset/end filter tails and avoid weak channels.
 for frame:=27500;frame<34000;frame++{
  a:=2*math.Pi*hz*float64(frame)/rate
  x:=float64(samples[frame*channels+ch])
  re+=x*math.Cos(a)
  im-=x*math.Sin(a)
 }
 return complex(re,im)
}
func check(original,offset []float32)error{
 if len(original)!=frames*channels||len(offset)!=frames*channels{return errors.New("wrong transport PCM shape")}
 var numerator complex128
 denom,bBefore,bAfter,aBefore,aAfter:=0.0,0.0,0.0,0.0,0.0
 for ch:=0;ch<channels;ch++{
  if ch==3{continue} // LFE excluded; not a transported full-band object
  b0,b1:=phasor(original,690,ch),phasor(offset,690,ch)
  a0,a1:=phasor(original,410,ch),phasor(offset,410,ch)
  numerator+=b1*cmplx.Conj(b0)
  denom+=cmplx.Abs(b0)*cmplx.Abs(b0)
  bBefore+=cmplx.Abs(b0)*cmplx.Abs(b0)
  bAfter+=cmplx.Abs(b1)*cmplx.Abs(b1)
  aBefore+=cmplx.Abs(a0)*cmplx.Abs(a0)
  aAfter+=cmplx.Abs(a1)*cmplx.Abs(a1)
 }
 if denom<1e-5||aBefore<1e-5{return errors.New("no source energy in transport interval")}
 ratio:=numerator/complex(denom,0)
 predicted:=2*math.Pi*690*sourceSeek/rate
 phaseError:=math.Atan2(math.Sin(cmplx.Phase(ratio)-predicted),math.Cos(cmplx.Phase(ratio)-predicted))
 if math.Abs(phaseError)>0.2 || cmplx.Abs(ratio)<0.8 || cmplx.Abs(ratio)>1.2 {
  return fmt.Errorf("source transport phase/amplitude mismatch got=%.5frad want=%.5frad delta=%.5f amp=%.6f",cmplx.Phase(ratio),predicted,phaseError,cmplx.Abs(ratio))
 }
 aRatio:=aAfter/aBefore
 if aRatio<0.95||aRatio>1.05{return fmt.Errorf("independent A410 source changed: power ratio %.8f",aRatio)}
 bRatio:=bAfter/bBefore
 if bRatio<0.8||bRatio>1.2{return fmt.Errorf("B690 phase-shifted transport lost energy: %.8f",bRatio)}
 fmt.Printf("spatial_source_TRANSPORT_PHASE_PASS offset_frames=%d gate=[%d,%d) expected_phase_mod=%.6f measured_phase=%.6f phase_error=%.6f source_A_410_power_ratio=%.6f source_B_690_power_ratio=%.6f legacy_scene_locked_unchanged=true\n",sourceSeek,gateStart,gateStop,math.Atan2(math.Sin(predicted),math.Cos(predicted)),cmplx.Phase(ratio),phaseError,aRatio,bRatio)
 return nil
}
func main(){
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"usage: transport-spectrum CLIP_START0_5.1.wav CLIP_OFFSET512_5.1.wav");os.Exit(2)}
 a,e:=decode(os.Args[1]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 b,e:=decode(os.Args[2]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 if e=check(a,b);e!=nil{fmt.Fprintln(os.Stderr,"SOURCE_TRANSPORT_FIRST_FAILURE",e);os.Exit(1)}
}
