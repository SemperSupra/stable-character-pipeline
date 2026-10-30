package main
import ("encoding/json";"flag";"fmt";"os")
func main(){
 input:=flag.String("input","","sampled joint DOF JSON")
 source:=flag.String("source","","source-original bytes SHA256")
 out:=flag.String("out","","JSON receipt path")
 flag.Parse()
 if *input==""||*source==""||*out==""{fmt.Fprintln(os.Stderr,"--input --source --out required");os.Exit(3)}
 file,err:=os.Stat(*input)
 if err!=nil||file.Size()>4000000{fmt.Fprintln(os.Stderr,"INPUT_NOT_ADMITTED");os.Exit(3)}
 src,err:=os.Stat(*source)
 if err!=nil||src.Size()>100000000{fmt.Fprintln(os.Stderr,"SOURCE_NOT_ADMITTED");os.Exit(3)}
 a,err:=os.ReadFile(*input);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 b,err:=os.ReadFile(*source);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 var in Input
 if err=json.Unmarshal(a,&in);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 r:=evaluate(in,b)
 v,_:=json.MarshalIndent(r,"","  ")
 v=append(v,'\n')
 if err=os.WriteFile(*out,v,0600);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 fmt.Println(string(v))
 if r.Status=="FAIL"{os.Exit(2)}
 if r.Status=="UNKNOWN"{os.Exit(3)}
 // 0 means ONLY the bounded, fictional source-authored scalar test,
 // never human/animal/mechanical safety or visual acceptance.
}
