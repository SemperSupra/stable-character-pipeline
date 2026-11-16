// Package inverse provides a bounded, synthetic-only inverse audio fitting test.
// It does not recover a person's real anatomy from a voice recording.
package inverse

import(
  "encoding/binary"
  "errors"
  "fmt"
  "math"
  "math/rand"

  "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/gasvoice"
)

type Config struct{
  KnownSoundSpeed float64 `json:"known_sound_speed_mps"`
  SourceF0 float64 `json:"source_f0_hz"`
  MinLength float64 `json:"min_length_m"`
  MaxLength float64 `json:"max_length_m"`
  SampleRate int `json:"sample_rate_hz"`
  Samples int `json:"samples"`
  Budget int `json:"budget"`
  Seed int64 `json:"seed"`
}

type Result struct{
  Method string `json:"method"`
  Seed int64 `json:"seed"`
  Evaluations int `json:"evaluations"`
  BestLength float64 `json:"best_length_m"`
  BestMSE float64 `json:"best_pcm_mse"`
}

func validateWAV(wav []byte,rate,n int)error{
 if len(wav)!=44+2*n||string(wav[:4])!="RIFF"||string(wav[8:12])!="WAVE"||
 string(wav[12:16])!="fmt "||string(wav[36:40])!="data"||
 binary.LittleEndian.Uint32(wav[4:8])!=uint32(len(wav)-8)||
 binary.LittleEndian.Uint16(wav[20:22])!=1||binary.LittleEndian.Uint16(wav[22:24])!=1||
 binary.LittleEndian.Uint16(wav[34:36])!=16||
 binary.LittleEndian.Uint32(wav[24:28])!=uint32(rate)||
 binary.LittleEndian.Uint32(wav[40:44])!=uint32(2*n){
  return errors.New("reference WAV does not match prescribed synthetic fixture")
 }
 return nil
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}

// Loss uses actual generated PCM rather than the generator's declared F1.
// This is a same-model toy self-consistency test and assumes phase alignment.
func Loss(reference []byte, candidate []byte)(float64,error){
 if len(reference)!=len(candidate)||len(reference)<46||(len(reference)-44)%2!=0{return 0,errors.New("mismatched PCM")}
 total:=0.0
 for i:=44;i<len(reference);i+=2 {
  a:=int16(binary.LittleEndian.Uint16(reference[i:i+2]))
  b:=int16(binary.LittleEndian.Uint16(candidate[i:i+2]))
  diff:=float64(int(a)-int(b))/32768
  total+=diff*diff
 }
 return total/float64((len(reference)-44)/2),nil
}

func Fit(reference []byte,c Config,method string)(Result,error){
 r:=Result{Method:method,Seed:c.Seed}
 if !(finite(c.KnownSoundSpeed)&&finite(c.SourceF0)&&finite(c.MinLength)&&finite(c.MaxLength))||
 c.KnownSoundSpeed<100||c.KnownSoundSpeed>2000||c.SourceF0<70||c.SourceF0>600||
 c.MinLength<0.08||c.MaxLength>0.4||c.MaxLength<=c.MinLength||
 c.SampleRate!=48000||c.Samples<4800||c.Samples>48000||c.Budget<4||c.Budget>60 {
  return r,errors.New("unadmitted inverse fitting parameters or budget")
 }
 if err:=validateWAV(reference,c.SampleRate,c.Samples);err!=nil{return r,err}
 r.BestMSE=math.Inf(1)
 evaluate:=func(length float64)(float64,error){
  candidate,_,err:=gasvoice.Generate(gasvoice.Params{
   SoundSpeed:c.KnownSoundSpeed,SourceF0:c.SourceF0,TractLength:length,
   SampleRate:c.SampleRate,Samples:c.Samples,
  });if err!=nil{return 0,err}
  mse,err:=Loss(reference,candidate);if err!=nil{return 0,err}
  r.Evaluations++
  if mse<r.BestMSE{r.BestMSE=mse;r.BestLength=length}
  return mse,nil
 }
 switch method{
 case "random":
  rng:=rand.New(rand.NewSource(c.Seed))
  for i:=0;i<c.Budget;i++{
   if _,err:=evaluate(c.MinLength+rng.Float64()*(c.MaxLength-c.MinLength));err!=nil{return r,err}
  }
 case "golden":
  // Golden section assumes local unimodality. It is not guaranteed globally
  // optimal; adversarial multimodal cases must remain in a later bakeoff.
  a,z:=c.MinLength,c.MaxLength
  phi:=(math.Sqrt(5)-1)/2
  x:=z-phi*(z-a);y:=a+phi*(z-a)
  fx,err:=evaluate(x);if err!=nil{return r,err}
  fy,err:=evaluate(y);if err!=nil{return r,err}
  for i:=2;i<c.Budget;i++{
    if fx<fy{
      z=y;y=x;fy=fx;x=z-phi*(z-a)
      fx,err=evaluate(x)
    }else{
      a=x;x=y;fx=fy;y=a+phi*(z-a)
      fy,err=evaluate(y)
    }
    if err!=nil{return r,err}
  }
 default:return r,fmt.Errorf("unknown search method: %s",method)
 }
 if r.Evaluations!=c.Budget||!finite(r.BestMSE){return r,errors.New("invalid search outcome")}
 return r,nil
}
