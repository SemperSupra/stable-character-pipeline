package main

import (
    "encoding/json"
    "math"
    "strings"
    "testing"
)
func sampleGroom() Groom {
    f:=Fiber{ID:"pony.black.mane.00001",Region:"mane",
        SourceTriangle:[3][3]float64{{0,0,0},{.1,0,0},{0,.1,0}},
        Barycentric:[3]float64{.25,.25,.5},
        SkinWeights:map[string]float64{"neck":.7,"head":.3},
        RestCurve:[][3]float64{{.025,.05,0},{.025,.05,-.1},{.025,.05,-.2}},
        RestLength:.2,RootRadius:.001,TipRadius:.0001}
    return Groom{Schema:"equine.groom.v1",GroomID:"synthetic_shetland_black_v1",
        Units:"m",SourceKind:"original_synthetic",
        SourceMeshSHA256:strings.Repeat("a",64),Seed:20261106,
        Season:"winter",LengthScale:1,DensityScale:1,Fibers:[]Fiber{f}}
}
func encode(g Groom) []byte{b,e:=json.Marshal(g);if e!=nil{panic(e)};return b}
func TestSourceContractValidNoScienceAdmission(t *testing.T){
    src:=encode(sampleGroom());r,e:=run(src)
    if e!=nil {t.Fatal(e)}
    if r.Verdict!="PASS_SOURCE_SCHEMA_ONLY"||len(r.Failures)!=0||!r.ScientificHold||r.ReleaseAdmission{
        t.Fatalf("unsafe contract %+v",r)
    }
    if r.RegionCounts["mane"]!=1||r.FiberCount!=1 {t.Fatal(r)}
    second,_:=run(src)
    if r.SourceSHA256!=second.SourceSHA256 {t.Fatal("nondeterministic source receipt")}
}
func TestMalformedOrTrailingJSONFailsClosed(t *testing.T){
    src:=encode(sampleGroom())
    for _,b:=range [][]byte{[]byte("{} garbage"),append(src,[]byte(" {}")...),
       []byte(strings.Replace(string(src),"\"season\":", "\"extra\":9,\"season\":",1))}{
        if _,e:=run(b);e==nil && !strings.EqualFold(string(b),"{} garbage"){t.Fatalf("accepted malformed/extra json %s",b)}
    }
    if _,e:=run([]byte("{} garbage"));e==nil{t.Fatal("accepted malformed")}
}
func TestHostilePerturbations(t *testing.T){
    testCases:=map[string]func(*Groom){
        "bary_sum":func(g *Groom){g.Fibers[0].Barycentric[0]=.5},
        "bary_nan":func(g *Groom){g.Fibers[0].Barycentric[0]=math.NaN()},
        "wrong_root":func(g *Groom){g.Fibers[0].RestCurve[0][1]+=.01},
        "zero_segment":func(g *Groom){g.Fibers[0].RestCurve[1]=g.Fibers[0].RestCurve[0]},
        "wrong_length":func(g *Groom){g.Fibers[0].RestLength=.08},
        "bad_taper":func(g *Groom){g.Fibers[0].TipRadius=.002},
        "bad_radius_nan":func(g *Groom){g.Fibers[0].RootRadius=math.NaN()},
        "skin_sum":func(g *Groom){g.Fibers[0].SkinWeights["neck"]=.6},
        "unknown_source":func(g *Groom){g.SourceKind="unknown_third_party"},
        "unknown_season":func(g *Groom){g.Season="autumn_undefined"},
        "bad_unit":func(g *Groom){g.Units="cm"},
        "missing_source_hash":func(g *Groom){g.SourceMeshSHA256="none"},
        "duplicate":func(g *Groom){g.Fibers=append(g.Fibers,g.Fibers[0])},
        "empty":func(g *Groom){g.Fibers=nil},
    }
    for name,modify:=range testCases{
        t.Run(name,func(t *testing.T){
            g:=sampleGroom();modify(&g)
            // Some hostile NaNs cannot be marshaled; call the pure validator
            // and still require a rejection without a panic or false PASS.
            r:=validate(g,[]byte(name))
            if r.Verdict!="REJECT_INVALID_SOURCE"||!r.ScientificHold||r.ReleaseAdmission||len(r.Failures)<1{
                t.Fatalf("accepted corrupt source %s: %+v",name,r)
            }
        })
    }
}
