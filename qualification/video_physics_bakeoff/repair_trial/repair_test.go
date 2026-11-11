package repairtrial
import "testing"
func boolp(v bool)*bool{return &v}
func example()Track{
 t:=Track{Schema:"scp.synthetic-contact-track.v1"}
 for i,x:=range []float64{.10,.12,.14,.16,.20,.28,.30}{
  t.Frames=append(t.Frames,Frame{Time:float64(i)*.1,X:x,Contact:boolp(i<4)})
 }
 return t
}
func TestCorrectiveAB(t *testing.T){
 b:=example();if Measure(b).Status!="FAIL"{t.Fatalf("bad baseline not detected")}
 c,e:=LockStance(b);if e!=nil{t.Fatal(e)}
 v:=Compare(b,c);if v.Result!="PROVISIONAL_IMPROVEMENT"{t.Fatalf("%+v",v)}
 if v.Candidate.StancePeakMS!=0||len(v.ChangedFrames)!=3{t.Fatalf("%+v",v)}
}
func TestNaiveFullFreezeRejected(t *testing.T){
 b:=example();c:=b;c.Frames=append([]Frame(nil),b.Frames...)
 for i:=range c.Frames{c.Frames[i].X=c.Frames[0].X}
 if v:=Compare(b,c);v.Result!="REJECT"{t.Fatalf("naive freeze wrongly accepted %+v",v)}
}
func TestContactOrTimestampMutationRejected(t *testing.T){
 b:=example();c,_:=LockStance(b);c.Frames[0].Time=.03
 if v:=Compare(b,c);v.Result!="REJECT"{t.Fatalf("timestamp mutation accepted %+v",v)}
 c,_=LockStance(b);c.Frames[2].Contact=boolp(false)
 if v:=Compare(b,c);v.Result!="REJECT"{t.Fatalf("contact mutation accepted %+v",v)}
}
func TestMissingContactAbstains(t *testing.T){
 b:=example();b.Frames[0].Contact=nil
 if Measure(b).Status!="UNKNOWN"{t.Fatalf("missing witness should abstain")}
 if _,e:=LockStance(b);e==nil{t.Fatalf("must reject source without contact")}
}
func TestRepairCreatesTransitionSpikeRejected(t *testing.T){
 b:=example();c,_:=LockStance(b);c.Frames[4].X=.9
 if v:=Compare(b,c);v.Result!="REJECT"{t.Fatalf("swing mutation accepted %+v",v)}
}
