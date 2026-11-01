package main
import (
 "bytes"
 "encoding/binary"
 "math"
 "testing"
)
func TestNativeStructuralRoundtrip(t *testing.T){
 x,e:=Write(Fixture());if e!=nil{t.Fatal(e)}
 want:=74+93*111
 if len(x)!=want{t.Fatalf("wrong VMD v2 byte structure %d != %d",len(x),want)}
 f,e:=Parse(x);if e!=nil{t.Fatal(e)}
 if len(f)!=93||f[0].Name!="Center"||f[30].Index!=30||f[31].Name!="L_Ankle"||f[92].Name!="R_Ankle"||f[92].Index!=30{t.Fatal("missing typed original frames")}
 if f[0].Rotation[3]!=1||f[30].Position[0]!=1{t.Fatal("wrong original synthetic local pose")}
}
func TestOriginalFormatHardNegatives(t *testing.T){
 base,e:=Write(Fixture());if e!=nil{t.Fatal(e)}
 for name,modify:=range map[string]func([]byte)[]byte{
 "magic":func(a []byte)[]byte{a[0]='X';return a},
 "truncated":func(a []byte)[]byte{return a[:len(a)-1]},
 "surplus":func(a []byte)[]byte{return append(a,0)},
 "nonzero_face_section":func(a []byte)[]byte{a[54+93*111]=1;return a},
 "NaN":func(a []byte)[]byte{binary.LittleEndian.PutUint32(a[54+19:54+23],math.Float32bits(float32(math.NaN())));return a},
 "wrong_actor_name":func(a []byte)[]byte{for i:=54;i<69;i++{a[i]='A'};return a},
 "bad_quat":func(a []byte)[]byte{binary.LittleEndian.PutUint32(a[54+43:54+47],math.Float32bits(2));return a},
 "forged_interpolation":func(a []byte)[]byte{a[54+47]=255;return a},
 "duplicate_frame":func(a []byte)[]byte{binary.LittleEndian.PutUint32(a[54+111+15:54+111+19],0);return a},
 }{
  t.Run(name,func(t *testing.T){bad:=modify(bytes.Clone(base));if _,err:=Parse(bad);err==nil{t.Fatal("forged VMD bytes accepted")}})
 }
}
func TestWriterRejectsImpossibleOriginalInput(t *testing.T){
 for _,mutate:=range []func([]Frame){
  func(a []Frame){a[0].Name="ReallyLongBoneNameNotASCII"},
  func(a []Frame){a[0].Position[0]=float32(math.Inf(1))},
  func(a []Frame){a[0].Rotation[3]=2},
  func(a []Frame){a[1].Index=0},
  func(a []Frame){a[0].Name="left_腕"},
 }{a:=Fixture();mutate(a);if _,err:=Write(a);err==nil{t.Fatal("bad authored fixture was serialized")}}
}
