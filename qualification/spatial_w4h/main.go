package main
import("encoding/json";"flag";"fmt";"os")
func main(){
 out:=flag.String("out","","receipt path");packetOut:=flag.String("packet-out","","optional original source packet path");flag.Parse()
 if *out==""{fmt.Fprintln(os.Stderr,"RECEIPT_PATH_REQUIRED");os.Exit(2)}
 p:=sample();r,e:=MakeReceipt(p);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 b,e:=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(*out,append(b,byte(10)),0644);e!=nil{panic(e)}
 if *packetOut!=""{raw,err:=json.MarshalIndent(p,"","  ");if err!=nil{panic(err)};if err=os.WriteFile(*packetOut,append(raw,byte(10)),0644);err!=nil{panic(err)}}
 fmt.Println("W4H_TYPED_ANNOTATION_PASS",r.CueCount)
}
