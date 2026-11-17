package observer
import(
 "encoding/binary"
 "math"
 "math/rand"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
func TestSourceBlindAll17FamiliesAndActualNoiseRoutes(t *testing.T){
 fixtures:=preview.Fixtures()
 if len(fixtures)!=17{t.Fatalf("unexpected fixture count %d",len(fixtures))}
 metrics:=map[string]Metrics{}
 for name,p:=range fixtures{
  wav,_,e:=preview.Render(p);if e!=nil{t.Fatalf("render %s: %v",name,e)}
  m,e:=AnalyzeWAV(wav);if e!=nil{t.Fatalf("observer %s: %v",name,e)}
  if m.Schema!="respiratory.source_blind_pcm_observer.v0"||m.SampleRateHz!=Rate||m.Samples!=(len(wav)-44)/2{
   t.Fatalf("%s ungrounded metrics: %+v",name,m)
  }
  if name=="no_flow_silence"{
   if !m.Silent||m.RMS!=0||m.Peak!=0{t.Fatalf("silent event incorrectly observed: %+v",m)}
  }else if m.Silent||m.RMS<1e-5{
   t.Fatalf("%s source unexpectedly silent: %+v",name,m)
  }
  metrics[name]=m
 }
 nose:=metrics["nasal_quiet"]
 mouth:=metrics["oral_quiet"]
 if !(nose.DifferencedEnergyRatio<mouth.DifferencedEnergyRatio){
  t.Fatalf("oral/nasal filter signature collapsed nasal=%g oral=%g",nose.DifferencedEnergyRatio,mouth.DifferencedEnergyRatio)
 }
 heavy:=metrics["oral_heavy"]
 if !(heavy.RMS>mouth.RMS){t.Fatalf("fixed-geometry higher prescribed flow did not increase synthetic energy: %.8f <= %.8f",heavy.RMS,mouth.RMS)}
 if !(metrics["beatbox_nonpulmonary"].Early20msEnergyFraction>nose.Early20msEnergyFraction){
  t.Fatalf("nonpulmonary click did not show transient early energy, beat=%.6f nose=%.6f",metrics["beatbox_nonpulmonary"].Early20msEnergyFraction,nose.Early20msEnergyFraction)
 }
}
func TestNonpitchedBreathingMustAbstainWhileOriginalSyntheticHumWhistleHaveLines(t *testing.T){
 fs:=preview.Fixtures()
 cases:=[]struct{name string;hz float64;wantPresent bool}{
  {"humming",180,true},
  {"lip_whistling",900,true},
  {"nasal_quiet",180,false},
  {"oral_quiet",180,false},
  {"beatbox_nonpulmonary",180,false},
  {"no_flow_silence",180,false},
 }
 for _,tc:=range cases{
  wav,_,err:=preview.Render(fs[tc.name]);if err!=nil{t.Fatal(err)}
  ev,err:=EvidenceAt(wav,tc.hz);if err!=nil{t.Fatalf("%s: %v",tc.name,err)}
  present:=ev.Status=="coherent_line_present_uncalibrated"
  if present!=tc.wantPresent{
   t.Fatalf("%s probe %.0fHz: status %s evidence %.9f; expected present=%t",tc.name,tc.hz,ev.Status,ev.EnergyFraction,tc.wantPresent)
  }
  if ev.EnergyFraction<0||ev.EnergyFraction>1{t.Fatal("unbounded energy evidence")}
 }
}
// Independent numerical synthetic test oracle: a pure sinusoid concentrates
// line energy at its own frequency, deterministic broadband noise does not.
func mkWAV(x []int16)[]byte{
 w:=make([]byte,44+2*len(x))
 copy(w[:4],"RIFF");binary.LittleEndian.PutUint32(w[4:8],uint32(len(w)-8))
 copy(w[8:12],"WAVE");copy(w[12:16],"fmt ")
 binary.LittleEndian.PutUint32(w[16:20],16)
 binary.LittleEndian.PutUint16(w[20:22],1);binary.LittleEndian.PutUint16(w[22:24],1)
 binary.LittleEndian.PutUint32(w[24:28],Rate)
 binary.LittleEndian.PutUint32(w[28:32],2*Rate)
 binary.LittleEndian.PutUint16(w[32:34],2);binary.LittleEndian.PutUint16(w[34:36],16)
 copy(w[36:40],"data");binary.LittleEndian.PutUint32(w[40:44],uint32(2*len(x)))
 for i,v:=range x{binary.LittleEndian.PutUint16(w[44+2*i:46+2*i],uint16(v))}
 return w
}
func TestIndependentToneVsNoiseCalibrationAndInputCorruption(t *testing.T){
 const n=12000
 sinus:=make([]int16,n);noise:=make([]int16,n)
 rng:=rand.New(rand.NewSource(23))
 for i:=0;i<n;i++{
  sinus[i]=int16(math.Round(12000*math.Sin(2*math.Pi*160*float64(i)/Rate)))
  noise[i]=int16(rng.Intn(24001)-12000)
 }
 s,e:=EvidenceAt(mkWAV(sinus),160);if e!=nil{t.Fatal(e)}
 if s.Status!="coherent_line_present_uncalibrated"||s.EnergyFraction<.98{t.Fatalf("pure tone not accepted %+v",s)}
 n160,e:=EvidenceAt(mkWAV(noise),160);if e!=nil{t.Fatal(e)}
 if n160.Status!="abstain_no_line"||n160.EnergyFraction>.03{t.Fatalf("noise falsely declared tonal %+v",n160)}
 base:=mkWAV(sinus)
 cases:=[][]byte{nil,[]byte("not wav"),base[:len(base)-1]}
 wrongRate:=append([]byte(nil),base...)
 binary.LittleEndian.PutUint32(wrongRate[24:28],44100)
 cases=append(cases,wrongRate)
 wrongLength:=append([]byte(nil),base...)
 binary.LittleEndian.PutUint32(wrongLength[40:44],100)
 cases=append(cases,wrongLength)
 clipping:=make([]int16,4800);clipping[0]=32767
 cases=append(cases,mkWAV(clipping))
 for i,c:=range cases{
  if _,err:=AnalyzeWAV(c);err==nil{t.Fatalf("bad/near-clipped wav %d accepted",i)}
 }
 for _,hz:=range []float64{0,-1,math.Inf(1),math.NaN(),9001}{
  if _,err:=EvidenceAt(base,hz);err==nil{t.Fatalf("invalid Hz %f accepted",hz)}
 }
}
