package timebase

import ("strings";"testing";"math")
func fixture(stride float64)Plan{
 p:=Plan{SourceSHA:strings.Repeat("a",64),FPS:12,SourceFrames:72,SceneStart:0,SceneEnd:71}
 for _,id:=range []string{"ASTER","JUNIPER"}{
  s:=Slot{ID:id}
  for j:=0;j<126;j++{
   c:=make([]Key,72)
   for i:=range c{
    x:=float64(i)*stride
    c[i]=Key{Frame:x,Value:float64(i)+float64(j)/100,LeftHandleX:x-.3*stride,RightHandleX:x+.3*stride}
   }
   s.Curves=append(s.Curves,c)
  }
  p.Slots=append(p.Slots,s)
 }
 return p
}
func TestDoubleImportDetectionAndReversibleCopy(t *testing.T){
 p:=fixture(2)
 f,e:=Inspect(p)
 if e!=nil||f.Status!="RED_DOUBLE_FRAME_IMPORT__RETIME_DIAGNOSTIC_ONLY"||f.Keys!=18144||f.Curves!=252{t.Fatalf("%+v %v",f,e)}
 out,e:=Retime(p,.5);if e!=nil{t.Fatal(e)}
 f,e=Inspect(out)
 if e!=nil||f.Status!="PASS_SYNTHETIC_FRAME_INDEX_ALIGNMENT_ONLY"{t.Fatalf("%+v %v",f,e)}
 if p.Slots[0].Curves[0][31].Frame!=62||out.Slots[0].Curves[0][31].Frame!=31{t.Fatal("source mutated or timebase wrong")}
 if out.Slots[0].Curves[0][31].Value!=p.Slots[0].Curves[0][31].Value{t.Fatal("pose value changed")}
 if out.Slots[0].Curves[0][31].LeftHandleX!=p.Slots[0].Curves[0][31].LeftHandleX*.5{t.Fatal("handle x unchanged")}
}
func TestTamperControls(t *testing.T){
 cases:=[]struct{name string;edit func(*Plan)}{
  {"one slot absent",func(p *Plan){p.Slots=p.Slots[:1]}},
  {"duplicate slot",func(p *Plan){p.Slots[1].ID="ASTER"}},
  {"missing curve",func(p *Plan){p.Slots[0].Curves=p.Slots[0].Curves[:125]}},
  {"missing key",func(p *Plan){p.Slots[0].Curves[0]=p.Slots[0].Curves[0][:71]}},
  {"mixed stride",func(p *Plan){p.Slots[0].Curves[0][31].Frame+=.4}},
  {"wrong scene FPS",func(p *Plan){p.FPS=24}},
  {"wrong scene extent",func(p *Plan){p.SceneEnd=142}},
  {"bad provenance",func(p *Plan){p.SourceSHA="fake"}},
  {"nonfinite handle",func(p *Plan){p.Slots[1].Curves[17][18].LeftHandleX=math.NaN()}},
  {"reversed left handle",func(p *Plan){p.Slots[0].Curves[2][10].LeftHandleX=21}},
  {"reversed right handle",func(p *Plan){p.Slots[0].Curves[2][10].RightHandleX=19}},
  {"left handle crosses preceding key",func(p *Plan){p.Slots[0].Curves[2][10].LeftHandleX=17}},
  {"right handle crosses following key",func(p *Plan){p.Slots[0].Curves[2][10].RightHandleX=23}},
  {"unrecognized stride",func(p *Plan){for a:=range p.Slots{for b:=range p.Slots[a].Curves{for c:=range p.Slots[a].Curves[b]{p.Slots[a].Curves[b][c].Frame=float64(c)*3}}}}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){p:=fixture(2);tc.edit(&p);if _,e:=Inspect(p);e==nil{t.Fatal("adversarial timebase accepted")}})}
}
func TestNoBlindRetime(t *testing.T){
 if _,e:=Retime(fixture(1),.5);e==nil{t.Fatal("correct clock must not be retimed")}
 if _,e:=Retime(fixture(2),1);e==nil{t.Fatal("incorrect correction factor accepted")}
}
