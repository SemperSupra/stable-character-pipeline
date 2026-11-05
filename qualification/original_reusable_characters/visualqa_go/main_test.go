package main
import "testing"
func TestPixelClasses(t *testing.T){
 x:=classify([]byte{180,100,99,45,135,143,90,95,93})
 if x.Pink!=1||x.Teal!=1{t.Fatalf("unexpected masks %#v",x)}
}
func TestFailActualOcclusionProxy(t *testing.T){
 a:=make([]Counts,72)
 for i:=range a{a[i]=Counts{Pink:120,Teal:120}}
 a[36]=Counts{Pink:120,Teal:10}
 _,low,status,err:=assess(a)
 if err!=nil||low.Teal!=1||status!="FAIL_COLOR_OCCLUSION_PROXY"{t.Fatalf("%#v %s %v",low,status,err)}
}
func TestPassDoesNotCertifyHuman(t *testing.T){
 a:=make([]Counts,72)
 for i:=range a{a[i]=Counts{Pink:120,Teal:120}}
 _,low,status,err:=assess(a)
 if err!=nil||low.Teal!=0||status!="PASS_COLOR_VISIBILITY_PROXY_ONLY"{t.Fatal(status,err)}
}
func TestRejectMissingFrameOrColors(t *testing.T){
 if _,_,_,e:=assess(make([]Counts,71));e==nil{t.Fatal("missing frame accepted")}
 if _,_,_,e:=assess(make([]Counts,72));e==nil{t.Fatal("missing actors accepted")}
}
