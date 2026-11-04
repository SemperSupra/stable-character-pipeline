package main
import "testing"

func TestMaterialPigmentSeparation(t *testing.T) {
 pixel:=[]byte{66,111,118,135,78,81,24,99,27,128,129,129}
 got:=countPixels(pixel)
 if got.Teal!=1 || got.Pink!=1 {t.Fatalf("material mask is not independent: %+v",got)}
}
func TestOriginalRedAndCorrectiveBlue(t *testing.T){
 pass:=Video{Frames:72,BothAbove500:72};blocked:=Video{Frames:72,BothAbove500:24}
 before:=map[string]Video{"front":pass,"oblique":blocked}
 if e:=qualify(before,map[string]Video{"front":pass,"oblique":pass});e!=nil{t.Fatalf("known correction rejected: %v",e)}
 if e:=qualify(before,map[string]Video{"front":pass,"oblique":blocked});e==nil{t.Fatal("known occluded camera falsely accepted")}
}
func TestFabricatedOriginalRedRejected(t *testing.T){
 pass:=Video{Frames:72,BothAbove500:72}
 if qualify(map[string]Video{"front":pass,"oblique":pass},map[string]Video{"front":pass,"oblique":pass})==nil{t.Fatal("original red missing was silently accepted")}
}
func TestWrongFrameCountRejected(t *testing.T){
 pass:=Video{Frames:72,BothAbove500:72};short:=Video{Frames:71,BothAbove500:72};red:=Video{Frames:72,BothAbove500:24}
 if qualify(map[string]Video{"front":pass,"oblique":red},map[string]Video{"front":short,"oblique":pass})==nil{t.Fatal("short movie falsely accepted")}
}
func TestSingleMissingCorrectedColorRejected(t *testing.T){
 pass:=Video{Frames:72,BothAbove500:72};partial:=Video{Frames:72,BothAbove500:71};red:=Video{Frames:72,BothAbove500:24}
 if qualify(map[string]Video{"front":pass,"oblique":red},map[string]Video{"front":pass,"oblique":partial})==nil{t.Fatal("one invisible frame falsely accepted")}
}
