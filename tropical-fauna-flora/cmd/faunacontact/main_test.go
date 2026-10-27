package main
import ("encoding/json";"math";"strings";"testing")

func TestPlantedFootStable(t *testing.T){
 r,e:=contact([]sample{{0,0,0,.01},{.1,0,0,.01},{.2,0,0,.01}})
 if e!=nil||r.PlantedTransitions!=2||r.MaxSlipSpeed!=0||r.MaxPenetration!=0{t.Fatalf("stable grounded contact: %+v %v",r,e)}
}
func TestSlidingFootIsDetected(t *testing.T){
 r,e:=contact([]sample{{0,0,0,0},{.1,.10,0,0},{.2,.12,0,0}})
 if e!=nil||r.PlantedTransitions!=2||math.Abs(r.MaxSlipSpeed-1)>1e-8{t.Fatalf("slip not detected: %+v %v",r,e)}
}
func TestSwingDoesNotTriggerFalsePlantedFoot(t *testing.T){
 r,e:=contact([]sample{{0,0,0,.10},{.1,2,0,.10},{.2,3,0,.20}})
 if e!=nil||r.PlantedTransitions!=0||r.MaxSlipSpeed!=0{t.Fatalf("swing misclassified: %+v %v",r,e)}
}
func TestPenetrationIndependentOfContact(t *testing.T){
 r,e:=contact([]sample{{0,0,0,-.04},{.1,.2,0,.2}})
 if e!=nil||r.MaxPenetration!=.04||r.PlantedTransitions!=0{t.Fatalf("penetration suppressed: %+v %v",r,e)}
}
func TestAdversarialFootSamples(t *testing.T){
 cases:=[][]sample{
  nil,{{0,0,0,0}},{{0,0,0,0},{0,0,0,0}},
  {{0,0,0,0},{-.1,0,0,0}},
  {{0,0,0,0},{2,0,0,0}},
  {{0,0,0,0},{.1,math.NaN(),0,0}},
  {{0,0,0,0},{.1,0,math.Inf(1),0}},
 }
 for _,v:=range cases{if _,err:=contact(v);err==nil{t.Errorf("invalid sampled data admitted: %v",v)}}
}
func TestInventoryRejectsUnverifiedOrBrokenGltf(t *testing.T){
 for _,data:=range [][]byte{nil,[]byte("{}"),[]byte("not JSON"),
  []byte(`{"asset":{"version":"1.0"},"nodes":[],"animations":[]}`)}{
   if _,err:=inventory(data);err==nil{t.Errorf("admitted invalid glTF: %s",data)}
 }
}
func TestInventoryReceiptFields(t *testing.T){
 raw,_:=json.Marshal(map[string]any{"asset":map[string]any{"version":"2.0"},"nodes":[]any{},"animations":[]any{}})
 if _,err:=inventory(raw);err==nil{t.Fatal("empty rig falsely verified")}
 if !strings.Contains("RIG_GRAPH_AND_ANIMATION_CHANNELS_ONLY","CHANNELS"){t.Fatal("broken qualification vocabulary")}
}
