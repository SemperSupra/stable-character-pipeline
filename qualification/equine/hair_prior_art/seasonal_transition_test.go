package main

import "testing"

func TestSeasonalRetainedFolliclesCanShortenWithoutRootResampling(t *testing.T) {
  winter:=sampleGroom()
  summer:=sampleGroom()
  summer.Season="summer";summer.LengthScale=.5;summer.DensityScale=.6
  f:=&summer.Fibers[0]
  f.RestCurve=[][3]float64{{.025,.05,0},{.025,.05,-.05},{.025,.05,-.1}}
  f.RestLength=.1
  r:=compareSeasonalStates(winter,summer,nil)
  if r.Verdict!="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"||r.Persistent!=1||
      r.Grown!=0||r.Shed!=0||r.MaxPersistentLengthChangeFraction<.49||
      !r.ScientificHold||r.ReleaseAdmission {
      t.Fatalf("incorrect seasonal retention: %+v",r)
  }
}
func TestSheddingAndGrowthRequireExplicitDistinctEvents(t *testing.T){
  winter:=sampleGroom();other:=sampleGroom()
  original:=winter.Fibers[0]
  other.Fibers[0].ID="pony.black.mane.00002"
  for _,events:=range [][]FiberEvent{nil,{{ID:original.ID,Action:"shed"}}} {
     if r:=compareSeasonalStates(winter,other,events);r.Verdict=="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"{
        t.Fatalf("accepted silent or partial fiber identity replacement: %+v",r)
     }
  }
  r:=compareSeasonalStates(winter,other,[]FiberEvent{
      {ID:original.ID,Action:"shed"},
      {ID:other.Fibers[0].ID,Action:"grow"}})
  if r.Verdict!="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"||r.Grown!=1||r.Shed!=1||r.Persistent!=0{
     t.Fatalf("rejected fully declared shed/grow: %+v",r)
  }
}
func TestSeasonalWrongMeshSeedOrBindingFailsClosed(t *testing.T){
  first:=sampleGroom()
  for _,change:=range []func(*Groom){
      func(g *Groom){g.SourceMeshSHA256="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
      func(g *Groom){g.Seed++},
      func(g *Groom){g.Fibers[0].SourceTriangle[2][1]+=.001},
      func(g *Groom){g.Fibers[0].SkinWeights["neck"]+=.01;g.Fibers[0].SkinWeights["head"]-=.01},
      func(g *Groom){g.GroomID="different-pony"},
  }{
      next:=sampleGroom();change(&next)
      if r:=compareSeasonalStates(first,next,nil);r.Verdict=="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"{
         t.Fatalf("accepted unapproved root/mesh/seed mutation: %+v",r)
      }
  }
}
func TestDuplicateAndFabricatedEventsFailClosed(t *testing.T){
  a:=sampleGroom()
  for _,events:=range [][]FiberEvent{
    {{ID:"fiction",Action:"grow"}},
    {{ID:"pony.black.mane.00001",Action:"shed"}},
    {{ID:"a",Action:"grow"},{ID:"a",Action:"grow"}},
    {{ID:"a",Action:"grow"},{ID:"a",Action:"shed"}},
    {{ID:"x",Action:"rename"}},
  }{
    if r:=compareSeasonalStates(a,a,events);r.Verdict=="PASS_TEMPORAL_SOURCE_IDENTITY_ONLY"{
      t.Fatalf("invalid transition event accepted: %+v",r)
    }
  }
}
