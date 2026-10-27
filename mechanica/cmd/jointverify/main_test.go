package main

import (
 "math"
 "strings"
 "testing"
)
func qZ(degrees float64)[4]float64{
 rad:=degrees*math.Pi/360
 return [4]float64{0,0,math.Sin(rad),math.Cos(rad)}
}
func TestSyntheticRevoluteLimitAndAxisFalsifiers(t *testing.T){
 j:=joint{Name:"synthetic/door",Kind:"revolute",Axis:[3]float64{0,0,1},MinDegrees:-35,MaxDegrees:50}
 cases:=[]struct{name string;q [4]float64;want string}{
  {"in_bounds",qZ(35),""},
  {"negative_bound",qZ(-35),""},
  {"out_of_bounds",qZ(85),"ANGLE_OUT_OF_LIMIT"},
  {"nonfinite",[4]float64{0,0,math.NaN(),1},"QUAT_NONFINITE"},
  {"nonunit",[4]float64{0,0,0,2},"QUAT_NONUNIT"},
  {"wrong_axis",[4]float64{math.Sin(math.Pi/8),0,0,math.Cos(math.Pi/8)},"ROTATION_AXIS_MISMATCH"},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   err:=checkQuaternion(j,tc.q)
   if tc.want==""&&err!=nil{t.Fatal(err)}
   if tc.want!=""&&(err==nil||!strings.Contains(err.Error(),tc.want)){t.Fatalf("wanted %s, got %v",tc.want,err)}
  })
 }
}
func TestSyntheticManifestFaults(t *testing.T){
 j:=joint{Kind:"revolute",Axis:[3]float64{0,0,1},MinDegrees:-10,MaxDegrees:10}
 j.Axis=[3]float64{0,0,0}
 if err:=checkQuaternion(j,qZ(0));err==nil||!strings.Contains(err.Error(),"AXIS_NONUNIT"){t.Fatal(err)}
 j.Axis=[3]float64{0,0,1};j.MinDegrees=15;j.MaxDegrees=10
 if err:=checkQuaternion(j,qZ(0));err==nil||!strings.Contains(err.Error(),"LIMIT_REVERSED"){t.Fatal(err)}
}
func TestTruncatedGLBFailsClosed(t *testing.T){
 _,_,err:=decodeGLB([]byte("glTF"))
 if err==nil||!strings.Contains(err.Error(),"INVALID_GLB_HEADER"){t.Fatal(err)}
}
