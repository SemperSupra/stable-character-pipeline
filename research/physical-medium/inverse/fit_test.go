package inverse
import(
 "math"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/physical-medium/gasvoice"
)
func synthetic(c Config,length float64) []byte {
 b,_,e:=gasvoice.Generate(gasvoice.Params{SoundSpeed:c.KnownSoundSpeed,SourceF0:c.SourceF0,TractLength:length,SampleRate:c.SampleRate,Samples:c.Samples})
 if e!=nil {panic(e)}
 return b
}
func TestFitReproducibleWithinBudget(t *testing.T){
 c:=Config{KnownSoundSpeed:343.22218086816235,SourceF0:160,MinLength:0.13,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:12,Seed:71}
 target:=synthetic(c,0.178)
 random,e:=Fit(target,c,"random");if e!=nil{t.Fatal(e)}
 again,e:=Fit(target,c,"random");if e!=nil||random!=again{t.Fatal("random search not reproducible")}
 golden,e:=Fit(target,c,"golden");if e!=nil{t.Fatal(e)}
 for _,x:=range []Result{random,golden}{
  if x.Evaluations!=12||x.BestLength<c.MinLength||x.BestLength>c.MaxLength||!finite(x.BestMSE)||x.BestMSE<0{t.Fatalf("invalid result %+v",x)}
 }
 // This gate demonstrates the intended local search on this frozen synthetic
 // fixture only. It does NOT establish overall algorithm superiority.
 if golden.BestMSE>=random.BestMSE{t.Fatalf("frozen local golden control not better on fixture: golden=%g random=%g",golden.BestMSE,random.BestMSE)}
 // Held-out source pitch changes after fitting; the original reference at
 // a second F0 is never supplied to either optimizer.
 held:=c;held.SourceF0=190
 truth:=synthetic(held,0.178)
 prediction:=synthetic(held,golden.BestLength)
 holdoutLoss,e:=Loss(truth,prediction);if e!=nil||math.IsNaN(holdoutLoss)||holdoutLoss>0.001{t.Fatalf("holdout loss %g err %v",holdoutLoss,e)}
}
func TestRejectMalformedOrUnadmittedFit(t *testing.T){
 c:=Config{KnownSoundSpeed:343,SourceF0:160,MinLength:0.13,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:12,Seed:1}
 target:=synthetic(c,0.18)
 for i,x:=range []Config{
  {KnownSoundSpeed:math.NaN(),SourceF0:160,MinLength:0.13,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:12},
  {KnownSoundSpeed:343,SourceF0:160,MinLength:0.13,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:0},
  {KnownSoundSpeed:343,SourceF0:160,MinLength:0.25,MaxLength:0.23,SampleRate:48000,Samples:4800,Budget:12},
 }{if _,e:=Fit(target,x,"random");e==nil{t.Fatalf("invalid config %d accepted",i)}}
 if _,e:=Fit(target[:100],c,"random");e==nil{t.Fatal("truncated WAV accepted")}
 if _,e:=Fit(target,c,"invented_method");e==nil{t.Fatal("unsupported optimizer accepted")}
}
