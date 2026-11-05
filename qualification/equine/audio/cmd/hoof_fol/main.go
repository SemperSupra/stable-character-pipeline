package main
import("flag";"fmt";"os";"stablecharacter/equine/audio")
func main(){
 in:=flag.String("input","","event JSON")
 wav:=flag.String("wav","","output WAV")
 receipt:=flag.String("receipt","","evidence JSON")
 seconds:=flag.Int("seconds",2,"bounded duration")
 flag.Parse()
 if *in==""||*wav==""||*receipt==""{fmt.Fprintln(os.Stderr,"-input/-wav/-receipt required");os.Exit(2)}
 if err:=audio.Write(*in,*wav,*receipt,*seconds);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
