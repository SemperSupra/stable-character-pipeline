package main

import (
    "encoding/json"
    "flag"
    "fmt"
    "os"

    v "github.com/SemperSupra/stable-character-pipeline/motion_learning/fauna_csv"
)

func main(){
    file:=flag.String("source","","read-only native-shaped CSV (synthetic in public workflow)")
    hash:=flag.String("expected-sha256","","independently recorded exact source SHA256")
    out:=flag.String("out","","exclusive-create metadata report")
    flag.Parse()
    if *file==""||*hash==""||*out==""{
        fmt.Fprintln(os.Stderr,"missing -source -expected-sha256 -out")
        os.Exit(4)
    }
    raw,err:=os.ReadFile(*file)
    if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
    p,err:=v.ProbeNativeLayout(raw,*hash)
    if err!=nil{fmt.Fprintln(os.Stderr,"LAYOUT_HOLD:",err);os.Exit(3)}
    f,err:=os.OpenFile(*out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
    if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
    defer f.Close()
    encoder:=json.NewEncoder(f)
    encoder.SetIndent("","  ")
    if err:=encoder.Encode(p);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
}
