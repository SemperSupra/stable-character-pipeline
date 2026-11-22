//go:build linux
package linuxhostpeer

import (
 "encoding/json"
 "errors"
 "net"
 "os"
 "os/exec"
 "path/filepath"
 "testing"
)

func TestOSPeerHelper(t *testing.T) {
 if os.Getenv("AUDIO_PEER_CHILD")!="1" {return}
 address:=&net.UnixAddr{Name:os.Getenv("AUDIO_PEER_SOCKET"),Net:"unix"}
 c,err:=net.DialUnix("unix",nil,address)
 if err!=nil{t.Fatal(err)}
 // Malicious self-reported privilege and PID cannot affect SO_PEERCRED.
 claim:=map[string]any{"action":"host_stopped","host_authorized":true,
  "principal_id":"forged_trusted_host","pid":987654321}
 if err:=json.NewEncoder(c).Encode(claim);err!=nil{t.Fatal(err)}
 if err:=c.Close();err!=nil{t.Fatal(err)}
}

func TestLinuxPeerCredentialPinnedToKernelProcess(t *testing.T) {
 dir,err:=os.MkdirTemp("","audio-peer-")
 if err!=nil{t.Fatal(err)}
 defer os.RemoveAll(dir)
 if err:=os.Chmod(dir,0700);err!=nil{t.Fatal(err)}
 socket:=filepath.Join(dir,"host.sock")
 listener,err:=ListenHostOnly(socket)
 if err!=nil{t.Fatal(err)}
 defer listener.Close()
 if _,err:=ListenHostOnly(socket);!errors.Is(err,ErrInvalidBinding){
  t.Fatalf("existing socket path was replaced: %v",err)
 }
 file,err:=os.Stat(socket);if err!=nil{t.Fatal(err)}
 if file.Mode().Perm()!=0600{t.Fatalf("socket permissions %o",file.Mode().Perm())}
 child:=exec.Command(os.Args[0],"-test.run=^TestOSPeerHelper$")
 child.Env=append(os.Environ(),"AUDIO_PEER_CHILD=1","AUDIO_PEER_SOCKET="+socket)
 if err:=child.Start();err!=nil{t.Fatal(err)}
 accepted,err:=listener.AcceptUnix();if err!=nil{t.Fatal(err)}
 defer accepted.Close()
 found,err:=Credentials(accepted);if err!=nil{t.Fatal(err)}
 expected:=Permit{UID:uint32(os.Getuid()),PID:int32(child.Process.Pid)}
 if found!=expected{t.Fatalf("kernel identity mismatch got %+v expected %+v",found,expected)}
 if err:=AuthorizeObservation(accepted,Permit{UID:expected.UID,PID:expected.PID+1});
  !errors.Is(err,ErrPeerNotAdmitted){t.Fatalf("forged host PID admitted: %v",err)}
 if err:=AuthorizeObservation(accepted,Permit{UID:expected.UID+1,PID:expected.PID});
  !errors.Is(err,ErrPeerNotAdmitted){t.Fatalf("forged host UID admitted: %v",err)}
 if err:=AuthorizeObservation(accepted,expected);err!=nil{
  t.Fatalf("genuine bound kernel host process rejected: %v",err)
 }
 var fake map[string]any
 if err:=json.NewDecoder(accepted).Decode(&fake);err!=nil{t.Fatal(err)}
 if fake["host_authorized"]!=true ||fake["pid"]!=float64(987654321){t.Fatalf("mock claim missing: %+v",fake)}
 // Authentic identity is still the kernel's child PID, not a JSON claim.
 after,err:=Credentials(accepted)
 if err!=nil||after!=expected{t.Fatalf("caller data overwrote kernel credential: %+v %v",after,err)}
 if err:=child.Wait();err!=nil{t.Fatalf("child failed %v",err)}
}

func TestBadHostBindingFailsClosed(t *testing.T) {
 if err:=AuthorizeObservation(nil,Permit{UID:0,PID:1});
  !errors.Is(err,ErrInvalidBinding){t.Fatalf("nil connection admitted: %v",err)}
 if err:=AuthorizeObservation(nil,Permit{UID:0,PID:0});
  !errors.Is(err,ErrInvalidBinding){t.Fatalf("empty binding admitted: %v",err)}
}
