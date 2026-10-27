package main

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)
func fixture(t *testing.T)Document{
 t.Helper()
 raw,err:=os.ReadFile(filepath.Join("..","..","examples","flora_traits_synthetic.json"));if err!=nil{t.Fatal(err)}
 d,err:=parse(raw);if err!=nil{t.Fatal(err)};return d
}
func TestSyntheticFixture(t *testing.T){
 d:=fixture(t);r,err:=validate(d);if err!=nil{t.Fatal(err)}
 if r.Organs!=3||r.Stems!=2||r.Leaves!=1||r.Status!="illustrative"{t.Fatalf("%+v",r)}
}
func TestFailClosed(t *testing.T){
 cases:=map[string]func(*Document){
 "fake verified":func(d *Document){d.TaxonStatus="verified"},
 "unlicensed":func(d *Document){d.SourceRights="UNKNOWN"},
 "dangling":func(d *Document){d.Organs[2].ParentID="missing"},
 "leaf root":func(d *Document){d.Organs[2].ParentID=""},
 "cycle":func(d *Document){d.Organs[0].ParentID="stem-001"},
 "duplicate vertex":func(d *Document){d.Organs[1].MTGVertex=2},
 "bad taper":func(d *Document){d.Organs[0].Traits.TipRadiusM=.19},
 "negative length":func(d *Document){d.Organs[1].Traits.LengthM=-1},
 "venation omitted":func(d *Document){d.Organs[2].Traits.Venation=""},
 "unsourced measurement":func(d *Document){d.Organs[2].Evidence.Origin="measured"},
 "fabricated rights":func(d *Document){d.Organs[2].Evidence.Origin="measured";d.SourceRights="RIGHTS_CLEARED_REFERENCE"},
 "centimetre intrusion":func(d *Document){d.Unit="cm"},
 "wrong coordinate frame":func(d *Document){d.Axis="Y_UP"},
 }
 for name,change:=range cases{t.Run(name,func(t *testing.T){d:=fixture(t);change(&d);if _,err:=validate(d);err==nil{t.Fatal("bad fixture admitted")}})}
}
func TestStrictJSON(t *testing.T){
 d:=fixture(t);b,err:=json.Marshal(d);if err!=nil{t.Fatal(err)}
 r,err:=admit(b);if err!=nil||len(r.InputSHA256)!=64{t.Fatal(r,err)}
 if _,err:=admit(append(append([]byte{},b...),b...));err==nil{t.Fatal("trailing duplicate JSON admitted")}
 altered:=bytes.Replace(b,[]byte("Z_UP_RIGHT_HANDED"),[]byte("Y_UP"),1)
 if _,err:=admit(altered);err==nil{t.Fatal("bad source axes admitted")}
}
