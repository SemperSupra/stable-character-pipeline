//go:build linux

// Package linuxhostpeer is a Linux-only experimental observation-ingress
// primitive. It uses kernel SO_PEERCRED rather than trusting caller JSON.
// It does NOT authorize physical audio, grant OS permissions or identify
// an agent/user inside the same process or same UID by itself.
package linuxhostpeer

import (
 "errors"
 "fmt"
 "net"
 "os"
 "syscall"
)

var ErrPeerNotAdmitted = errors.New("linuxhostpeer: unexpected OS peer identity")
var ErrInvalidBinding = errors.New("linuxhostpeer: invalid host binding")

// Permit is supplied by an independently privileged host supervisor.
// It is never to be constructed from client-origin command fields.
type Permit struct {
 UID uint32
 PID int32
}

// Credentials come from the Linux kernel via the connected AF_UNIX socket.
// SO_PEERCRED is evidence about the peer at connection time, not proof that
// the audio device is working, already stopped, or still associated with PID.
func Credentials(conn *net.UnixConn) (Permit,error) {
 if conn==nil {return Permit{},ErrInvalidBinding}
 raw,err:=conn.SyscallConn()
 if err!=nil{return Permit{},err}
 var cred *syscall.Ucred
 var controlErr error
 if err=raw.Control(func(fd uintptr){
  cred,controlErr=syscall.GetsockoptUcred(int(fd),syscall.SOL_SOCKET,syscall.SO_PEERCRED)
 });err!=nil{return Permit{},err}
 if controlErr!=nil{return Permit{},controlErr}
 if cred==nil{return Permit{},ErrPeerNotAdmitted}
 return Permit{UID:cred.Uid,PID:cred.Pid},nil
}

// AuthorizeObservation matches a separately admitted host process binding.
// It explicitly ignores any claimed PID/user/privilege in the JSON payload.
// All untrusted submit routes MUST be separate from this host-only socket.
func AuthorizeObservation(conn *net.UnixConn, trusted Permit) error {
 if trusted.PID<=0 {return ErrInvalidBinding}
 observed,err:=Credentials(conn)
 if err!=nil{return err}
 if observed!=trusted {
  return fmt.Errorf("%w: host process mismatch",ErrPeerNotAdmitted)
 }
 return nil
}

// ListenHostOnly creates a local-only Unix socket and restricts path access;
// the directory must be private/approved. Path mode alone is not origin
// authentication, therefore each connection must also pass SO_PEERCRED.
func ListenHostOnly(path string)(*net.UnixListener,error){
 if path=="" {return nil,ErrInvalidBinding}
 if _,err:=os.Lstat(path);err==nil{return nil,ErrInvalidBinding
 }else if !errors.Is(err,os.ErrNotExist){return nil,err}
 addr,err:=net.ResolveUnixAddr("unix",path)
 if err!=nil{return nil,err}
 listener,err:=net.ListenUnix("unix",addr)
 if err!=nil{return nil,err}
 if err:=os.Chmod(path,0600);err!=nil{listener.Close();return nil,err}
 return listener,nil
}
