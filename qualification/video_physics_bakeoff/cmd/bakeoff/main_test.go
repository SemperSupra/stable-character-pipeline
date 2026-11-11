package main
import("os";"path/filepath";"testing";"strings")
func TestMotionFixtures(t *testing.T){
 for _,tc:=range []struct{f,want string}{{"clean.json","PASS"},{"skate.json","FAIL"},{"unknown.json","UNKNOWN"}}{
  t.Run(tc.f,func(t *testing.T){v,_,_,e:=analyzeMotion(filepath.Join("../../fixtures",tc.f));if e!=nil||v!=tc.want{t.Fatalf("verdict=%s err=%v",v,e)}})
 }
}
func TestInvalidTime(t *testing.T){
 dir:=t.TempDir();f:=filepath.Join(dir,"bad.json")
 if e:=os.WriteFile(f,[]byte(`{"schema":"scp.motion-observation.v1","samples":[{"time_s":0,"foot_x_m":0,"foot_y_m":0,"contact":true},{"time_s":0,"foot_x_m":0,"foot_y_m":0,"contact":true}]}`),0600);e!=nil{t.Fatal(e)}
 v,why,_,e:=analyzeMotion(f);if e!=nil||v!="UNKNOWN"||!strings.Contains(strings.Join(why,","),"TIME"){t.Fatalf("%v %s %v",e,v,why)}
}
func TestTraversal(t *testing.T){
 r:=evaluate(t.TempDir(),Case{ID:"bad",Kind:"motion",Path:"../file",Expect:"PASS"})
 if r.Error==""||r.Verdict!="UNKNOWN"{t.Fatalf("%+v",r)}
}
