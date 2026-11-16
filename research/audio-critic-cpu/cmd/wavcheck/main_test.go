package main
import ("bytes";"os";"path/filepath";"testing")
func TestReadBounded(t *testing.T){
 p:=filepath.Join(t.TempDir(),"fixture.bin")
 original:=bytes.Repeat([]byte("synthetic"),100)
 if e:=os.WriteFile(p,original,0600);e!=nil{t.Fatal(e)}
 if _,e:=readBounded(p,32);e==nil{t.Fatal("input limit failure not detected")}
 got,e:=readBounded(p,int64(len(original)));if e!=nil||!bytes.Equal(got,original){t.Fatalf("bounded read failure: %v",e)}
 if _,e:=readBounded(p,0);e==nil{t.Fatal("invalid limit accepted")}
}
