package critic
import (
 "encoding/binary"
 "math"
 "testing"
)
func wav(rate int, values []int16) []byte {
 n:=len(values)*2;b:=make([]byte,44+n)
 copy(b[:4],"RIFF");binary.LittleEndian.PutUint32(b[4:8],uint32(36+n));copy(b[8:12],"WAVE");copy(b[12:16],"fmt ");binary.LittleEndian.PutUint32(b[16:20],16);binary.LittleEndian.PutUint16(b[20:22],1);binary.LittleEndian.PutUint16(b[22:24],1);binary.LittleEndian.PutUint32(b[24:28],uint32(rate));binary.LittleEndian.PutUint32(b[28:32],uint32(rate*2));binary.LittleEndian.PutUint16(b[32:34],2);binary.LittleEndian.PutUint16(b[34:36],16);copy(b[36:40],"data");binary.LittleEndian.PutUint32(b[40:44],uint32(n))
 for i,x:=range values{binary.LittleEndian.PutUint16(b[44+i*2:46+i*2],uint16(x))};return b
}
func TestRealMeasurements(t *testing.T){
 samples:=make([]int16,48000)
 for i:=range samples{samples[i]=int16(math.Round(16384*math.Sin(2*math.Pi*150*float64(i)/48000)))}
 m,e:=Measure(wav(48000,samples));if e!=nil{t.Fatal(e)}
 if m.Silent||m.ClippedSamples!=0||m.SampleRate!=48000||m.Samples!=48000||m.Peak<0.49||m.Peak>0.51||m.RMS<0.34||m.RMS>0.36{t.Fatalf("bad metrics %+v",m)}
 if math.Abs(m.FundamentalHz-150)>1||m.FundamentalConfidence<0.95{t.Fatalf("bad F0 estimate %+v",m)}
}
func TestSilenceClippingAndAbstention(t *testing.T){
 m,e:=Measure(wav(16000,make([]int16,1600)));if e!=nil||!m.Silent||m.FundamentalHz!=0{t.Fatalf("silence: %+v %v",m,e)}
 c:=make([]int16,1600);for i:=range c{c[i]=32767};m,e=Measure(wav(16000,c));if e!=nil||m.ClippedSamples!=len(c){t.Fatalf("clipping: %+v %v",m,e)}
}
func TestInvalidWav(t *testing.T){
 good:=wav(48000,make([]int16,100))
 variants:=[][]byte{nil,[]byte("RIFF"),good[:len(good)-1],append([]byte(nil),good...),append([]byte(nil),good...),append([]byte(nil),good...)}
 variants[3][22]=2
 variants[4][20]=3
 binary.LittleEndian.PutUint32(variants[5][40:44],math.MaxUint32)
 for i,b:=range variants{if _,e:=Measure(b);e==nil{t.Fatalf("invalid WAV %d accepted",i)}}
}
