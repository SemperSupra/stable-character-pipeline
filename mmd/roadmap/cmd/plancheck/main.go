package main

import (
    "encoding/json"
    "flag"
    "fmt"
    "os"

    "github.com/SemperSupra/stable-character-pipeline/mmd/roadmap"
)

func main() {
    input := flag.String("input","workplan.v1.json","path to the authoritative JSON roadmap")
    format := flag.String("format","markdown","markdown or json snapshot")
    flag.Parse()
    content,err:=os.ReadFile(*input)
    if err!=nil {fmt.Fprintln(os.Stderr,"roadmap input:",err);os.Exit(2)}
    plan,err:=roadmap.Decode(content)
    if err!=nil {fmt.Fprintln(os.Stderr,"roadmap validation:",err);os.Exit(1)}
    switch *format {
    case "markdown":
        fmt.Print(roadmap.Markdown(plan))
    case "json":
        b,err:=json.MarshalIndent(roadmap.Summarize(plan),"","  ")
        if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(1)}
        fmt.Println(string(b))
    default:
        fmt.Fprintln(os.Stderr,"unsupported format (markdown or json)")
        os.Exit(2)
    }
}
