// Command dual-spectrum checks that two original monophonic dry source
// frequencies are independently present in the SAME actual six-channel PCM.
// Strictly a bounded spectral-content oracle, not a perceptual spatial test.
package main

import (
 "encoding/binary"
 "errors"
 "fmt"
 "math"
 "os"
 "os/exec"
)
const rate=48000
const frames=48000
const nch=6

func decode(path string)([]float32,error){
 b,e:=exec.Command("ffmpeg","-hide_banner","-nostdin","-v","error","-xerror",
  "-i",path,"-f","f32le","-acodec","pcm_f32le","-").Output()
 if e!=nil{return nil,e}
 if len(b)!=frames*nch*4{return nil,errors.New("expected 48k frames of six-channel float32")}
 result:=make([]float32,frames*nch)
 for i:=range result {
  value:=math.Float32frombits(binary.LittleEndian.Uint32(b[4*i:4*i+4]))
  if math.IsNaN(float64(value))||math.IsInf(float64(value),0){return nil,errors.New("nonfinite native output")}
  result[i]=value
 }
 return result,nil
}
func spectralEnergy(samples []float32,hz float64)float64{
 var sum float64
 for ch:=0;ch<nch;ch++{
  re,im:=0.0,0.0
  for i:=0;i<frames;i++ {
   v:=float64(samples[i*nch+ch])
   angle:=2*math.Pi*hz*float64(i)/rate
   re+=v*math.Cos(angle)
   im+=v*math.Sin(angle)
  }
  amplitude:=2*math.Hypot(re,im)/frames
  sum+=amplitude*amplitude
 }
 return sum
}
func verify(actual,changed []float32)error {
 if len(actual)!=frames*nch||len(changed)!=frames*nch{return errors.New("invalid channel/frame length")}
 a410,a690,a930:=spectralEnergy(actual,410),spectralEnergy(actual,690),spectralEnergy(actual,930)
 b410,b690,b930:=spectralEnergy(changed,410),spectralEnergy(changed,690),spectralEnergy(changed,930)
 if a410<1e-6||a690<1e-6||b410<1e-6||b930<1e-6 {
  return fmt.Errorf("missing dry-source spectral contribution A:410=%g 690=%g B:410=%g 930=%g",a410,a690,b410,b930)
 }
 if b690>=a690*0.1||a930>=b930*0.1{return fmt.Errorf("source B tone switch not isolated: original 690=%g altered 690=%g original 930=%g altered 930=%g",a690,b690,a930,b930)}
 ratio:=b410/a410
 if ratio<0.7||ratio>1.3{return fmt.Errorf("source A 410Hz energy unexpectedly changed under source B retune: ratio=%g",ratio)}
 fmt.Printf("spatial_w3_source_content_ISOLATION_PASS original_A_410=%.9g original_B_690=%.9g retuned_A_410=%.9g retuned_B_930=%.9g retained_A_ratio=%.6f removed_B_690_ratio=%.6f\n",a410,a690,b410,b930,ratio,b690/a690)
 return nil
}

func windowEnergy(samples []float32,hz float64,start,stop int)float64{
 var power float64
 for ch:=0;ch<nch;ch++{
  re,im:=0.0,0.0
  for i:=start;i<stop;i++{
   v:=float64(samples[i*nch+ch])
   angle:=2*math.Pi*hz*float64(i)/rate
   re+=v*math.Cos(angle)
   im+=v*math.Sin(angle)
  }
  amp:=2*math.Hypot(re,im)/float64(stop-start)
  power+=amp*amp
 }
 return power
}
// Window checks spectrally isolated source B remains active only in the declared
// gate. It checks broad temporal energy, NOT exact acoustic ringing/impulse onset.
func checkActivity(original,gated []float32)error{
 windows:=[]struct{name string;start,stop int;active bool}{
  {"before",0,22000,false},
  {"inside",27000,35000,true},
  {"after",39000,48000,false},
 }
 for _,w:=range windows{
  if w.stop>frames||w.start<0||w.stop<=w.start{return errors.New("invalid QA window")}
  priorB:=windowEnergy(original,690,w.start,w.stop)
  gatedB:=windowEnergy(gated,690,w.start,w.stop)
  priorA:=windowEnergy(original,410,w.start,w.stop)
  gatedA:=windowEnergy(gated,410,w.start,w.stop)
  if priorB<1e-6||priorA<1e-6||gatedA<1e-6{return fmt.Errorf("missing original source in %s interval",w.name)}
  ar:=gatedA/priorA
  if ar<0.7||ar>1.3{return fmt.Errorf("source A changed under B gating in %s interval: %.8f",w.name,ar)}
  ratio:=gatedB/priorB
  if w.active{
   if ratio<0.5||ratio>1.5{return fmt.Errorf("B activity lost in %s interval %.8f",w.name,ratio)}
  }else if ratio>0.03{
   return fmt.Errorf("B activity leaked into muted %s interval %.8f",w.name,ratio)
  }
  fmt.Printf("spatial_w3b_window_OBS window=%s source_A_retained_ratio=%.6f B_690_energy_ratio=%.8f expected_active=%v\n",w.name,ar,ratio,w.active)
 }
 fmt.Println("spatial_w3b_source_sample_windows_PASS onset_frame=24575 stop_frame=36865 acoustic_residual_not_sample_zero_claimed")
 return nil
}
func main(){
 if len(os.Args)==4&&os.Args[1]=="windows"{
  original,e:=decode(os.Args[2]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
  gated,e:=decode(os.Args[3]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
  if e=checkActivity(original,gated);e!=nil{fmt.Fprintln(os.Stderr,"WINDOW_FIRST_FAILURE",e);os.Exit(1)}
  return
 }
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"usage: dual-spectrum original_5.1.wav retuned_B_5.1.wav | windows ORIGINAL_5.1.wav GATED_B_5.1.wav");os.Exit(2)}
 a,e:=decode(os.Args[1]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 b,e:=decode(os.Args[2]);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 if e=verify(a,b);e!=nil{fmt.Fprintln(os.Stderr,"SPECTRAL_FIRST_FAILURE",e);os.Exit(1)}
}
