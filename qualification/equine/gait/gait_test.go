package gait

import "testing"

func TestGaitFootfalls(t *testing.T){
    want:=map[string]int{"idle":0,"walk":8,"trot":8,"canter-left":8,"canter-right":8,"gallop-left":8,"gallop-right":8}
    for kind,n:=range want{
        r,e:=Generate("pony-black",kind,"sand",2,24,24,48000)
        if e!=nil { t.Fatalf("%s: %v",kind,e)}
        if len(r.Events)!=n {t.Fatalf("%s: got %d, want %d",kind,len(r.Events),n)}
        if r.Evaluation!="PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT"{t.Fatal("physical overclaim")}
        for _,ev:=range r.Events{
            if ev.Kind!="hoof_impact"||ev.Source!=Basis||ev.ContactState!="planned_contact"{t.Fatal("wrong contract")}
            if ev.Sample!=int64(ev.Frame)*2000 {t.Fatal("sample drift")}
        }
    }
}
func TestFootfallPhases(t *testing.T){
    walks,_:=Generate("pony","walk","sand",1,24,24,48000)
    exp:=[]string{"HL","FL","HR","FR"}
    for i,v:=range exp {
        if walks.Events[i].Foot!=v || walks.Events[i].Frame!=i*6 {t.Fatalf("walk phase %d: %#v",i,walks.Events[i])}
    }
    trots,_:=Generate("pony","trot","soil",1,24,24,48000)
    if trots.Events[0].Frame!=0||trots.Events[1].Frame!=0||trots.Events[2].Frame!=12||trots.Events[3].Frame!=12 {
        t.Fatalf("trot diagonals %#v",trots.Events)
    }
    can,_:=Generate("pony","canter-left","stone",1,24,24,48000)
    if can.Events[0].Frame!=0 || can.Events[1].Frame!=8 || can.Events[2].Frame!=8 || can.Events[3].Frame!=16 {
        t.Fatalf("3-beat left lead %#v",can.Events)
    }
}
func TestSource48FrameWalkAlignment(t *testing.T) {
    r,err:=Generate("pony-black","walk","sand",1,48,24,48000)
    if err!=nil {t.Fatal(err)}
    if r.FramesPerCycle!=48||r.FPS!=24||len(r.Events)!=4 {
        t.Fatalf("expected 4 distinct hoof events across exported 48f cycle: %#v",r)
    }
    wantFoot:=[]string{"HL","FL","HR","FR"}
    for i,event:=range r.Events{
        expectedFrame:=i*12
        if event.Frame!=expectedFrame || event.Sample!=int64(expectedFrame*2000) || event.Foot!=wantFoot[i] {
            t.Fatalf("source 48f planned event mismatch: %#v",event)
        }
        if event.ContactState!="planned_contact" || event.Source!="SYNTHETIC_PLANNED" {
            t.Fatal("source 48f unverified physical claim")
        }
    }
    twice,err:=Generate("pony-black","walk","sand",2,48,24,48000)
    if err!=nil||len(twice.Events)!=8||twice.Events[4].Frame!=48 {
        t.Fatalf("48f cycle repeat must start at frame 48: %#v %v",twice,err)
    }
}

func TestFailClosed(t *testing.T){
    for _,kind:=range []string{"bad","WALK","cantering"}{
        if _,e:=Generate("pony",kind,"sand",2,24,24,48000);e==nil{t.Fatal(kind)}
    }
    if _,e:=Generate("pony","walk","sand",1,25,24,48000);e==nil{t.Fatal("noninteger quarter phase")}
    if _,e:=Generate("pony","walk","sand",1,24,23,48000);e==nil{t.Fatal("noninteger samples")}
    if _,e:=Generate("pony","walk","mud-unknown",1,24,24,48000);e==nil{t.Fatal("unadmitted surface")}
    if _,e:=Generate("","walk","sand",1,24,24,48000);e==nil{t.Fatal("missing actor")}
    if _,e:=Generate("pony","walk","sand",900,24,24,48000);e==nil{t.Fatal("unbounded cycles")}
}
