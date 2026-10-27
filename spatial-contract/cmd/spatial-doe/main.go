// spatial-doe prints the deterministic, source-independent W3c experiment
// manifest. It does not render spatial PCM or certify either native engine.
package main

import (
 "encoding/json"
 "fmt"
 "os"
 "example.invalid/spatial-contract/doe"
)
func main(){
 if len(os.Args)!=2||os.Args[1]!="plan"{fmt.Fprintln(os.Stderr,"usage: spatial-doe plan");os.Exit(2)}
 m,e:=doe.Generate();if e!=nil{fmt.Fprintln(os.Stderr,"SPATIAL_DOE_FIRST_FAILURE",e);os.Exit(1)}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ")
 if e=encoder.Encode(m);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
}
