package main

// Independent RED from actual MMD Tools v4.5.14 VMDImporter:
// each component uses k.interp[idx:idx+16:4] with idx=0,16,32,48.
// https://github.com/MMD-Blender/blender_mmd_tools/blob/v4.5.14/mmd_tools/core/vmd/importer.py
// The original authored linear-looking placeholder MUST not imply qualified
// linear curves unless all four decoded channels equal (20,20,107,107).
// The upstream provider source and native 93-frame VMD first failure are preserved.
import "testing"

func TestMMDToolsActualFourInterpolationChannelsLinear(t *testing.T) {
 data,err:=Write(Fixture())
 if err!=nil { t.Fatal(err) }
 const recordLength=111
 want:=[4]byte{20,20,107,107}
 channelNames:=[]string{"X","Y","Z","Rotation"}
 for i:=0;i<93;i++{
  start:=54+i*recordLength+47
  interp:=data[start:start+64]
  for ch:=0;ch<4;ch++{
   base:=16*ch
   got:=[4]byte{interp[base],interp[base+4],interp[base+8],interp[base+12]}
   if got!=want {
    t.Fatalf("FIRST_RED original VMD key=%d channel=%s actual importer control points=%v want intended linear %v",i,channelNames[ch],got,want)
   }
  }
 }
}

func TestMMDToolsRejectAlteredUnreviewedBezierBank(t *testing.T){
 data,err:=Write(Fixture());if err!=nil{t.Fatal(err)}
 // Mutate the first record Y interpolation bank. The original parser checks
 // only the first bank and mistakenly accepts any Y/Z/rotation corruption.
 pos:=54+47+16
 data[pos]=127
 if _,err:=Parse(data);err==nil {
  t.Fatal("FIRST_RED native source VMD reader accepted forged Y-channel interpolation")
 }
}
