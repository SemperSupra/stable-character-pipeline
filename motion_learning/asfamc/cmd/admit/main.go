package main
import(
 "encoding/json"
 "flag"
 "fmt"
 "os"

 "github.com/SemperSupra/stable-character-pipeline/motion_learning/asfamc"
)
func main(){
 af:=flag.String("asf","","synthetic ASF fixture")
 am:=flag.String("amc","","synthetic AMC fixture")
 id:=flag.String("source-id","","synthetic source ID")
 grp:=flag.String("capture-group","","immutable interaction/recording family")
 out:=flag.String("out","","exclusive-create receipt")
 flag.Parse()
 if *af==""||*am==""||*out==""{fmt.Fprintln(os.Stderr,"missing -asf -amc -out");os.Exit(4)}
 a,err:=os.ReadFile(*af);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 m,err:=os.ReadFile(*am);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 r,err:=asfamc.Qualify(a,m,*id,*grp)
 if err!=nil{fmt.Fprintln(os.Stderr,"SOURCE_HOLD:",err);os.Exit(3)}
 f,err:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 defer f.Close()
 e:=json.NewEncoder(f);e.SetIndent("","  ")
 if err:=e.Encode(r);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
}
