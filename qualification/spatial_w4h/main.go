package main
import("encoding/json";"flag";"fmt";"os")
func main(){
 out:=flag.String("out","","receipt path");flag.Parse()
 if *out==""{fmt.Fprintln(os.Stderr,"RECEIPT_PATH_REQUIRED");os.Exit(2)}
 r,e:=MakeReceipt(sample());if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(*out,append(b,byte(10)),0644);e!=nil{panic(e)}
 fmt.Println("W4H_TYPED_ANNOTATION_PASS",r.CueCount)
}
