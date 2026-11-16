package preview

import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "fmt"
 "math"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
)

func TestAllSyntheticPerformanceFamiliesAndExactReplay(t *testing.T){
 fixtures:=Fixtures()
 if len(fixtures)!=17{t.Fatalf("expected 17 independently named source families, got %d",len(fixtures))}
 seenHash:=map[string]string{}
 silentCount:=0
 for name,p:=range fixtures {
  if err:=p.Validate();err!=nil{t.Fatalf("%s invalid contract: %v",name,err)}
  wav,receipt,err:=Render(p);if err!=nil{t.Fatalf("%s render: %v",name,err)}
  if receipt.Schema!="respiratory.preview_receipt.v0"||
     receipt.SampleRateHz!=48000||
     receipt.Samples!=p.Frames[len(p.Frames)-1].EndSample||
     receipt.ModelValidity!="deterministic_original_synthetic_not_biological"{
   t.Fatalf("%s ungrounded receipt %+v",name,receipt)
  }
  if len(wav)!=44+receipt.Samples*2||string(wav[:4])!="RIFF"||string(wav[8:12])!="WAVE"||
   binary.LittleEndian.Uint32(wav[24:28])!=48000{
   t.Fatalf("%s malformed PCM16 source",name)
  }
  hash:=fmt.Sprintf("%x",sha256.Sum256(wav))
  if hash!=receipt.SHA256{t.Fatalf("%s generator hash mismatch",name)}
  again,againReceipt,err:=Render(p)
  if err!=nil||!bytes.Equal(wav,again)||againReceipt.SHA256!=hash{
   t.Fatalf("%s deterministic replay failure: %v",name,err)
  }
  if receipt.Peak>=.99||receipt.RMS<0||math.IsNaN(receipt.RMS)||math.IsInf(receipt.RMS,0){
   t.Fatalf("%s violated headroom/numeric invariant: %+v",name,receipt)
  }
  if name=="no_flow_silence"{
   if receipt.Peak!=0||receipt.RMS!=0{t.Fatalf("zero flow emitted audio in no-source case %+v",receipt)}
   silentCount++
  } else {
   if receipt.Peak<=0.00001||receipt.RMS<=0.00001{t.Fatalf("%s unexpectedly silent %+v",name,receipt)}
  }
  if prev,ok:=seenHash[hash];ok{t.Fatalf("distinct source actions emitted identical waveforms %s and %s",prev,name)}
  seenHash[hash]=name
 }
 if silentCount!=1{t.Fatalf("silence negative control count %d",silentCount)}
 if fixtures["beatbox_nonpulmonary"].Frames[0].TotalFlowM3S!=0{
  t.Fatal("nonpulmonary click illegally required lung airflow")
 }
 if fixtures["straw_suction"].Frames[0].ObjectFlowM3S>=0{
  t.Fatal("straw suction has wrong source-flow direction")
 }
}
func TestNasalVsOralAndVolumeAreNotOneGenericEffect(t *testing.T){
 fs:=Fixtures()
 n,rn,e:=Render(fs["nasal_quiet"]);if e!=nil{t.Fatal(e)}
 o,ro,e:=Render(fs["oral_quiet"]);if e!=nil{t.Fatal(e)}
 heavy,rh,e:=Render(fs["oral_heavy"]);if e!=nil{t.Fatal(e)}
 pant,rp,e:=Render(fs["panting"]);if e!=nil{t.Fatal(e)}
 if bytes.Equal(n,o)||bytes.Equal(o,heavy)||bytes.Equal(heavy,pant){t.Fatal("route, effort and temporal frame controls collapsed")}
 if rn.RMS<=0||ro.RMS<=0||rh.RMS<=ro.RMS||rp.RMS<=0{
  t.Fatalf("inconsistent synthetic signal ranking nasal=%v mouth=%v heavier=%v pant=%v",rn.RMS,ro.RMS,rh.RMS,rp.RMS)
 }
}
func TestNegativeRendererAdmissionAndHeadroom(t *testing.T){
 p:=Fixtures()["humming"]
 p.Classification="PRIVATE_FINAL_CHARACTER_VOICE"
 if _,_,e:=Render(p);e==nil{t.Fatal("private character voice classification accepted")}
 p=Fixtures()["humming"]
 p.Frames[0].EndSample=480001
 if _,_,e:=Render(p);e==nil{t.Fatal("unbounded waveform length accepted")}
 p=Fixtures()["humming"]
 p.Frames[0].TotalFlowM3S=math.NaN()
 if _,_,e:=Render(p);e==nil{t.Fatal("nonfinite source state accepted")}
 p=Fixtures()["scream_proxy"]
 p.Frames[0].Sources=make([]behavior.Source,8)
 for i:=range p.Frames[0].Sources{
  p.Frames[0].Sources[i]=behavior.Source{Kind:behavior.GlottalVoiced,NominalHz:160,Amplitude:1}
 }
 if _,_,e:=Render(p);e==nil{t.Fatal("intentional overdrive was silently clipped")}
}
