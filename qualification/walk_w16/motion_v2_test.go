package main
import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)
func clone(p Packet)Packet{
 b,e:=json.Marshal(p);if e!=nil{panic(e)}
 var x Packet
 if e=json.Unmarshal(b,&x);e!=nil{panic(e)}
 return x
}
func TestOriginalSourcePacket(t *testing.T){
 for _,prof:=range []string{"forward","outward"} {
  p:=sample(prof)
  b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
  got,e:=Decode(b);if e!=nil{t.Fatal(prof,e)}
  if got.Actors[0].Profile!=prof||len(got.Actors)!=2{t.Fatal("profile or actor corruption")}
  for _,a:=range got.Actors {if a.Frames[0].Foot.Anchor==nil{t.Fatal("lost contact")}}
 }
}
func TestHostileSourcePacketsFailClosed(t *testing.T) {
 mutations:=[]struct{name string;change func(*Packet)}{
  {"rights_spoof",func(p *Packet){p.Rights="UNVERIFIED"}},
  {"missing_origin",func(p *Packet){p.OriginCommit=""}},
  {"basis_silent_swap",func(p *Packet){p.Basis="BLENDER_Z_UP"}},
  {"missing_conversion",func(p *Packet){p.BasisConversion=""}},
  {"units_silent_swap",func(p *Packet){p.Units="METERS"}},
  {"fps_mismatch",func(p *Packet){p.FPSNum=ptr(30)}},
  {"duplicate_actor",func(p *Packet){p.Actors[1].ID=p.Actors[0].ID}},
  {"duplicate_bone",func(p *Packet){p.Actors[0].Bones[3].ID="knee"}},
  {"parent_cycle",func(p *Packet){p.Actors[0].Bones[1].Parent="ankle"}},
  {"missing_frame_clock",func(p *Packet){p.Actors[0].Frames[1].TimeNum=nil}},
  {"frame_clock_drift",func(p *Packet){p.Actors[0].Frames[1].TimeNum=ptr(13)}},
  {"time_den_drift",func(p *Packet){p.Actors[0].Frames[1].TimeDen=ptr(30)}},
  {"duplicate_frame",func(p *Packet){p.Actors[0].Frames[1].Index=ptr(0);p.Actors[0].Frames[1].TimeNum=ptr(0)}},
  {"missing_quat",func(p *Packet){delete(p.Actors[0].Frames[0].Local,"ankle")}},
  {"nonunit_quat",func(p *Packet){p.Actors[0].Frames[0].Local["knee"]=Q{0,0,0,2}}},
  {"grounded_anchor_missing",func(p *Packet){p.Actors[0].Frames[0].Foot.Anchor=nil}},
  {"planted_slip",func(p *Packet){p.Actors[0].Frames[1].Foot.Anchor=&V{2,0,0}}},
  {"swing_forged_anchor",func(p *Packet){p.Actors[0].Frames[2].Foot.Anchor=&V{2,0,0}}},
  {"contact_unsupported",func(p *Packet){p.Actors[0].Frames[2].Foot.State="force_measured"}},
  {"actor_role_spoof",func(p *Packet){p.Actors[0].ID="PRIVATE_CHARACTER"}},
 }
 for _,tc:=range mutations{t.Run(tc.name,func(t *testing.T){
  p:=clone(sample("forward"));tc.change(&p)
  b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
  if _,e:=Decode(b);e==nil{t.Fatal("HOSTILE_PACKET_ACCEPTED")}
 })}
}
func TestMalformedJsonAndUnqualifiedScope(t *testing.T){
 b,e:=json.Marshal(sample("forward"));if e!=nil{t.Fatal(e)}
 for _,raw:=range [][]byte{append(append([]byte{},b...),b...),append(append([]byte{},b...),[]byte("garbage")...),
 bytes.Replace(b,[]byte("\"schema\":"),[]byte("\"unexpected\":17,\"schema\":"),1)}{
  if _,e:=Decode(raw);e==nil{t.Fatal("MALFORMED_OR_UNKNOWN_ACCEPTED")}
 }
 if !validQ(Q{0,0,0,-1}){t.Fatal("quaternion sign parity rejected")}
 if validQ(Q{0,0,0,0}){t.Fatal("zero quaternion accepted")}
 if strings.Contains(sample("forward").Rights,"PRIVATE"){t.Fatal("private source contaminated fixture")}
}
