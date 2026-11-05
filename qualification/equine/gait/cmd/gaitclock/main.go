package main
import(
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "stablecharacter/equine/gait"
)
func main(){
 gaitName:=flag.String("gait","walk","idle/walk/trot/canter-left/canter-right/gallop-left/gallop-right")
 surface:=flag.String("surface","sand","sand/stone/soil/grass")
 actor:=flag.String("actor","pony-black","actor identity")
 out:=flag.String("out","","output path (empty stdout)")
 cycles:=flag.Int("cycles",2,"bounded gait cycles")
 framesPerCycle:=flag.Int("frames-per-cycle",24,"source animation frames per gait cycle (24 or 48 typical)")
 fps:=flag.Int("fps",24,"video frame rate, 48000 must divide evenly")
 flag.Parse()
 receipt,err:=gait.Generate(*actor,*gaitName,*surface,*cycles,*framesPerCycle,*fps,48000)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 b,err:=json.MarshalIndent(receipt,"","  ")
 if err!=nil {panic(err)}
 b=append(b,'\n')
 if *out==""{os.Stdout.Write(b)}else if err=os.WriteFile(*out,b,0644);err!=nil{panic(err)}
}
