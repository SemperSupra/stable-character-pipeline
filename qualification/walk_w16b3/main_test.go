package main
import("encoding/json";"testing")
func TestDualLegOriginal(t *testing.T){
 for _,profile:=range []string{"forward","outward"}{
  p,r,e:=makePacket(profile);if e!=nil{t.Fatal(e)}
  if e=Validate(p);e!=nil{t.Fatal(e)}
  if r.Observations!=28||r.MaxIKError>1e-8||len(p.Actors)!=2{t.Fatal(r)}
  b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
  var decoded Packet;if e=json.Unmarshal(b,&decoded);e!=nil{t.Fatal(e)}
  if e=Validate(decoded);e!=nil{t.Fatal(e)}
  for _,a:=range p.Actors {for _,f:=range a.Frames {for _,l:=range f.Legs {
   if l.Contact!="unknown"{t.Fatal("CONTACT_FALSE_GREEN")}
  }}}
 }
}
func TestHardNegatives(t *testing.T){
 source,_,e:=makePacket("forward");if e!=nil{t.Fatal(e)}
 for name,mutate:=range map[string]func(*Packet){
  "rights":func(p *Packet){p.Rights="UNKNOWN_RIGHTS"},
  "origin":func(p *Packet){p.OriginSHA="forged"},
  "time":func(p *Packet){p.Actors[0].Frames[2].TimeDen=0},
  "frame":func(p *Packet){p.Actors[0].Frames[1].Frame=24},
  "parent":func(p *Packet){p.Actors[0].Frames[0].Legs[0].Parent="Wrong"},
  "contact":func(p *Packet){p.Actors[0].Frames[0].Legs[0].Contact="stance"},
  "basis":func(p *Packet){p.Basis="GLTF_Y_UP_UNANNOUNCED"},
  "quat":func(p *Packet){p.Actors[0].Frames[1].Legs[0].UpperWorld=[4]float64{}},
  "duplicate":func(p *Packet){p.Actors[1].ID="CobaltOriginal"},
 }{
  var p Packet;data,_:=json.Marshal(source);_ = json.Unmarshal(data,&p)
  mutate(&p)
  if e:=Validate(p);e==nil{t.Fatal("BAD_"+name+"_ACCEPTED")}
 }
 if _,_,e:=makePacket("private");e==nil{t.Fatal("UNQUALIFIED_PROFILE")}
}
