package asfamc

import (
 "math"
 "os"
 "strings"
 "testing"
)

func originals(t *testing.T)([]byte,[]byte){
 t.Helper()
 a,err:=os.ReadFile("testdata/leg.synthetic.asf");if err!=nil{t.Fatal(err)}
 m,err:=os.ReadFile("testdata/leg.synthetic.amc");if err!=nil{t.Fatal(err)}
 return a,m
}
func TestSyntheticMetadataDoesNotClaimMeasuredContact(t *testing.T){
 a,m:=originals(t);r,err:=Qualify(a,m,"synthetic/leg-v1","synthetic/leg-session-1")
 if err!=nil{t.Fatal(err)}
 if len(r.Frames)!=2||len(r.Skeleton.Bones)!=2||r.Frames[0].Number!=1{
  t.Fatalf("lost structure %#v",r)}
 if math.Abs(r.Frames[1].RootMeters[0]-(1/.45)*.0254)>1e-12 ||
 math.Abs(r.Frames[1].RootMeters[1]-2*(1/.45)*.0254)>1e-12 ||
 math.Abs(r.Frames[1].RootMeters[2]-3*(1/.45)*.0254)>1e-12 {t.Fatalf("root conversion mismatch %+v",r.Frames[1].RootMeters)}
 if r.Admission!="NOT_ADMITTED"||r.FKConverted||r.ObservedGroundContact||r.ObservedTimestamp||
 r.NativeFrameRate!="UNKNOWN"||len(r.Unknown)<4 {t.Fatal("unsupported inference/promoted source")}
 if r.Skeleton.Bones[0].Parent!="root"||r.Skeleton.Bones[1].Parent!="lhip"{t.Fatal("hierarchy not preserved")}
 if r.ASFSHA256!=digest(a)||r.AMCSHA256!=digest(m) {t.Fatal("byte ancestry not preserved")}
}
func TestFailClosedSourceAndChannelMutations(t *testing.T){
 a,m:=originals(t)
 cases:=[]struct{name string;asf,amc func(string)string}{
 {"missing rights marker",func(s string)string{return strings.Replace(s,Marker,"notadmitted",1)},nil},
 {"unverified physical unit",func(s string)string{return strings.Replace(s,"length 0.45","length 1.0",1)},nil},
 {"radian angle",func(s string)string{return strings.Replace(s,"angle deg","angle rad",1)},nil},
 {"bad root order",func(s string)string{return strings.Replace(s,"TZ RX","TX RX",1)},nil},
 {"unknown bone DOF",func(s string)string{return strings.Replace(s,"dof rx ry rz","dof qx ry rz",1)},nil},
 {"cyclic hierarchy",func(s string)string{return strings.Replace(s,"root lhip","lknee lhip",1)},nil},
 {"duplicated bone name",func(s string)string{return strings.Replace(s,"name lknee","name lhip",1)},nil},
 {"missing hierarchy",func(s string)string{return strings.Replace(s,":hierarchy",":documentation",1)},nil},
 {"missing frame",nil,func(s string)string{return strings.Replace(s,"\n2\nroot","\n3\nroot",1)}},
 {"duplicate joint",nil,func(s string)string{return strings.Replace(s,"lhip 1 0 -1","lhip 1 0 -1\nlhip 1 0 -1",1)}},
 {"missing joint",nil,func(s string)string{return strings.Replace(s,"lknee 4\n","",1)}},
 {"nan observation",nil,func(s string)string{return strings.Replace(s,"root 1 2 3","root NaN 2 3",1)}},
 {"unknown channel",nil,func(s string)string{return strings.Replace(s,"lhip 1 0 -1","unknown 1 0 -1",1)}},
 {"extra joint coordinate",nil,func(s string)string{return strings.Replace(s,"lknee 4","lknee 4 5",1)}},
 {"missing degrees header",nil,func(s string)string{return strings.Replace(s,":degrees",":radians",1)}},
 {"duplicate source frame",nil,func(s string)string{return strings.Replace(s,"\n2\nroot","\n1\nroot",1)}},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){
  aa,mm:=string(a),string(m)
  if tc.asf!=nil{aa=tc.asf(aa)}
  if tc.amc!=nil{mm=tc.amc(mm)}
  if _,err:=Qualify([]byte(aa),[]byte(mm),"syn","same-group");err==nil{
   t.Fatal("bad source/channel treated as qualifiable")
  }
 })}
}
func TestInteractionAncestrySplitBarrier(t *testing.T){
 ok:=[]Record{
  {ID:"cmu-18-01-a",Group:"handshake-18-19-01",Family:"cmu-18-19-01",Split:"train"},
  {ID:"cmu-19-01-b",Group:"handshake-18-19-01",Family:"cmu-18-19-01",Split:"train"},
  {ID:"cmu-02-01",Group:"walk-02-01",Family:"cmu-02-01",Split:"test"},
 }
 if err:=CheckSplit(ok);err!=nil {t.Fatal(err)}
 bad:=append([]Record(nil),ok...)
 bad[1].Split="validation"
 if err:=CheckSplit(bad);err==nil{t.Fatal("same recorded interaction leaked across train/validation")}
 bad=append([]Record(nil),ok...)
 bad[1].Group="transformed-copy-under-new-label"
 bad[1].Split="validation"
 if err:=CheckSplit(bad);err==nil{t.Fatal("same derivative source family leaked through renamed group")}
 bad=append([]Record(nil),ok...)
 bad[1].ID=bad[0].ID
 if err:=CheckSplit(bad);err==nil{t.Fatal("duplicate source IDs admitted")}
}
