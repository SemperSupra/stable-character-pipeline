package main
import ("math";"strings";"testing")
func fixtureExchange()(SurfacePacket,SurfacePacket,[]SurfaceDelta){
 b:=SurfacePacket{Schema:exchangeSchema,Source:"original_synthetic",Entity:"pony.synthetic",MeshSHA256:strings.Repeat("a",64),Solver:"blender45",Units:"SI",Frame:"world_Z_up",RateHz:120,Tick:0,ScienceHold:true,
 Patches:[]PatchState{{ID:"mane.root",Wet:.25,Deposit:.001,Residue:.02,TempK:290}},
 Contacts:[]ContactObservation{{ID:"hit.1",PatchID:"mane.root",OtherID:"body.neck",Evidence:"triangle_overlap",PointM:[3]float64{1,2,3},Observed:true}}}
 a:=b;a.Tick=5;a.Solver="blender52.experimental";a.Patches=append([]PatchState{},b.Patches...);a.Patches[0].Wet=.3
 a.Contacts=append([]ContactObservation{},b.Contacts...)
 return b,a,[]SurfaceDelta{{PatchID:"mane.root",Reason:"experimental_solver",Wet:.05}}
}
func TestSurfaceSourceTransfer(t *testing.T){
 b,a,c:=fixtureExchange();r:=exchangeSurface(b,a,c)
 if r.Verdict!="PASS_EXPLICIT_TRANSFER_ONLY"||r.Preserved!=1||r.Changes!=1||len(r.Errors)>0||!r.ScienceHold||r.Release{t.Fatalf("false reject %+v",r)}
 a.Patches[0]=b.Patches[0];r=exchangeSurface(b,a,nil)
 if r.Verdict!="PASS_EXPLICIT_TRANSFER_ONLY"||r.Changes!=0{t.Fatal(r)}
}
func TestSurfaceHostileControls(t *testing.T){
 mutants:=map[string]func(*SurfacePacket,*SurfacePacket,*[]SurfaceDelta){
 "rights":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Source="external_unreviewed"},
 "hold":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.ScienceHold=false},
 "release":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Release=true},
 "units":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Units="cm"},
 "axis":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Frame="Y_up"},
 "tick":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Tick=0},
 "gap":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Tick=120*601},
 "mesh":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.MeshSHA256=strings.Repeat("b",64)},
 "silent_change":func(b,a *SurfacePacket,d *[]SurfaceDelta){*d=nil},
 "delta_mismatch":func(b,a *SurfacePacket,d *[]SurfaceDelta){(*d)[0].Wet=.08},
 "orphan_delta":func(b,a *SurfacePacket,d *[]SurfaceDelta){(*d)[0].PatchID="lost.patch"},
 "duplicate_delta":func(b,a *SurfacePacket,d *[]SurfaceDelta){*d=append(*d,(*d)[0])},
 "negative_mass":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Patches[0].Residue=-1},
 "nonfinite_temp":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Patches[0].TempK=math.NaN()},
 "missing_patch":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Patches=nil},
 "forged_force":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Contacts[0].Evidence="measured_force"},
 "planned_as_observed":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Contacts[0].Observed=false},
 "negative_distance":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Contacts[0].DistanceM=-.01},
 "overlap_distance":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Contacts[0].DistanceM=.1},
 "wrong_patch":func(b,a *SurfacePacket,d *[]SurfaceDelta){a.Contacts[0].PatchID="lost.patch"},
 }
 if len(mutants)!=20{t.Fatalf("mutant fixture drift %d",len(mutants))}
 for name,mutate:=range mutants{t.Run(name,func(t *testing.T){
  b,a,d:=fixtureExchange();mutate(&b,&a,&d);r:=exchangeSurface(b,a,d)
  if r.Verdict!="REJECT_EXCHANGE"||len(r.Errors)==0||!r.ScienceHold||r.Release{t.Fatalf("false accept %+v",r)}
 })}
}
