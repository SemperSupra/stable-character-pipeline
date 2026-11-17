// R068 bounded deterministic packaging for a source-only model test candidate.
// Records intervention; cannot repair semantics or bypass syntax/negative tests.
package main
import "strings"

func normalizeCandidateGo(source string) (string,string) {
 s:=strings.TrimSpace(source)
 if strings.HasPrefix(s,"```go"){
  s=strings.TrimSpace(strings.TrimPrefix(s,"```go"))
  if strings.HasSuffix(s,"```"){s=strings.TrimSpace(strings.TrimSuffix(s,"```"))}
  if strings.HasPrefix(s,"import ")||strings.HasPrefix(s,"func Test"){
   return "package main"+string(rune(10))+string(rune(10))+s,"STRIP_FENCE_AND_ADD_PACKAGE"
  }
  return s,"STRIP_FENCE_ONLY"
 }
 if strings.HasPrefix(s,"import ")||strings.HasPrefix(s,"func Test"){
  return "package main"+string(rune(10))+string(rune(10))+s,"ADD_PACKAGE_ONLY"
 }
 return s,"NO_NORMALIZATION"
}
