package main

import (
 "bytes"
 "encoding/binary"
 "os"
 "path/filepath"
 "testing"
)

func z(s string) []byte {return append([]byte(s),0)}
func attr(name,typ string,val []byte) []byte {
 b:=append(z(name),z(typ)...)
 var size [4]byte
 binary.LittleEndian.PutUint32(size[:],uint32(len(val)))
 b=append(b,size[:]...);return append(b,val...)
}
func channel(name string) []byte {
 b:=z(name)
 b=append(b,[]byte{2,0,0,0,0,0,0,0}...)
 b=append(b,[]byte{1,0,0,0,1,0,0,0}...)
 return b
}
func sample(bad bool) []byte {
 ch:=[]byte{}
 names:=[]string{"ViewLayer.Combined.R","ViewLayer.Combined.G","ViewLayer.Combined.B","ViewLayer.Depth.Z","ViewLayer.Normal.X","ViewLayer.Normal.Y","ViewLayer.Normal.Z","ViewLayer.Vector.X","ViewLayer.Vector.Y","ViewLayer.IndexOB.X"}
 if bad {names=names[:len(names)-1]}
 for _,s:=range names{ch=append(ch,channel(s)...)}
 ch=append(ch,0)
 b:=[]byte{0x76,0x2f,0x31,0x01,2,0,0,0}
 b=append(b,attr("channels","chlist",ch)...)
 b=append(b,attr("dataWindow","box2i",bytes.Repeat([]byte{0},16))...)
 b=append(b,attr("compression","compression",[]byte{3})...)
 b=append(b,0)
 return append(b,bytes.Repeat([]byte{0},80)...)
}
func TestHeaderAndFiveGroups(t *testing.T){c,err:=inspect(sample(false));if err!=nil{t.Fatal(err)};p,err:=passes(c);if err!=nil{t.Fatal(err)};if len(p)!=5 {t.Fatalf("groups %v",p)}}
func TestRejectSignatureAndTruncation(t *testing.T){for _,b:=range [][]byte{{},bytes.Repeat([]byte{0},50),sample(false)[:25]} {if _,err:=inspect(b);err==nil{t.Fatal("invalid header passed")}}}
func TestRejectMissingObjectID(t *testing.T){c,err:=inspect(sample(true));if err!=nil{t.Fatal(err)};if _,err:=passes(c);err==nil{t.Fatal("missing segmentation accepted")}}
func TestRejectDuplicatedChannel(t *testing.T){ch:=append(channel("ViewLayer.Combined.R"),channel("ViewLayer.Combined.R")...);ch=append(ch,0);if _,err:=parseChannels(ch);err==nil{t.Fatal("duplicate channel")}}
func TestRejectBadSampling(t *testing.T){ch:=channel("A.X");ch[len(ch)-1]=0;ch[len(ch)-2]=0;ch[len(ch)-3]=0;ch[len(ch)-4]=0;ch=append(ch,0);if _,err:=parseChannels(ch);err==nil{t.Fatal("zero sampling")}}
func TestPairedActualInputContract(t *testing.T){d:=t.TempDir();a:=filepath.Join(d,"a.exr");b:=filepath.Join(d,"b.exr");if err:=os.WriteFile(a,sample(false),0600);err!=nil{t.Fatal(err)};if err:=os.WriteFile(b,sample(false),0600);err!=nil{t.Fatal(err)};x,err:=audit(a,b);if err!=nil{t.Fatal(err)};if x.Status!="EXR_HEADER_CHANNELS_VERIFIED" {t.Fatal(x.Status)};if err:=os.WriteFile(b,sample(true),0600);err!=nil{t.Fatal(err)};if _,err:=audit(a,b);err==nil{t.Fatal("mismatched passes accepted")}}
func TestRejectSymlink(t *testing.T){d:=t.TempDir();actual:=filepath.Join(d,"true.exr");alias:=filepath.Join(d,"alias.exr");if err:=os.WriteFile(actual,sample(false),0600);err!=nil{t.Fatal(err)};if err:=os.Symlink(actual,alias);err!=nil{t.Fatal(err)};if _,_,err:=read(alias);err==nil{t.Fatal("symlink accepted")}}
