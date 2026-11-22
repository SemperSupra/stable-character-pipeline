// Native Darwin-only peer credential proof. No audio, network RPC or
// credentials from JSON are trusted. This is NOT host permission authority.
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

static void must(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL macOS peer identity: %s: errno=%d\n", message, errno);
        exit(2);
    }
}
int main(void) {
    char folder[]="/tmp/audio-peer-macos-XXXXXX";
    must(mkdtemp(folder)!=NULL,"private temporary directory");
    must(chmod(folder,0700)==0,"directory mode");
    char path[sizeof(((struct sockaddr_un *)0)->sun_path)];
    int written=snprintf(path,sizeof(path),"%s/host.sock",folder);
    must(written>0&&(size_t)written<sizeof(path),"bounded socket path");
    int server=socket(AF_UNIX,SOCK_STREAM,0);
    must(server>=0,"create AF_UNIX socket");
    struct sockaddr_un address;
    memset(&address,0,sizeof(address));
    address.sun_family=AF_UNIX;
    memcpy(address.sun_path,path,(size_t)written+1);
    must(bind(server,(struct sockaddr*)&address,sizeof(address))==0,"bind local-only socket");
    must(chmod(path,0600)==0,"socket permissions");
    must(listen(server,1)==0,"listen");
    pid_t child=fork();
    must(child>=0,"fork isolated child");
    if(child==0) {
        close(server);
        int client=socket(AF_UNIX,SOCK_STREAM,0);
        if(client<0) _exit(31);
        if(connect(client,(struct sockaddr*)&address,sizeof(address))!=0)_exit(32);
        // Self-asserted privilege and fake process ID MUST NOT be trusted.
        const char message[]="{\"host_authorized\":true,\"pid\":987654321,\"uid\":0}\n";
        if(write(client,message,sizeof(message)-1)!=(ssize_t)(sizeof(message)-1))_exit(33);
        close(client);
        _exit(0);
    }
    int peer=accept(server,NULL,NULL);
    must(peer>=0,"accept real child");
    uid_t peerUID=(uid_t)-1;
    gid_t peerGID=(gid_t)-1;
    must(getpeereid(peer,&peerUID,&peerGID)==0,"kernel getpeereid");
    pid_t peerPID=-1;
    socklen_t size=sizeof(peerPID);
    must(getsockopt(peer,SOL_LOCAL,LOCAL_PEERPID,&peerPID,&size)==0,"kernel LOCAL_PEERPID");
    must(size==sizeof(peerPID),"peer PID returned correct type");
    must(peerPID==child,"child PID must come from kernel not JSON");
    must(peerUID==geteuid()&&peerGID==getegid(),"peer UID/GID from kernel");
    must(peerPID!=987654321,"forged child PID not trusted");
    char message[128]={0};
    ssize_t n=read(peer,message,sizeof(message)-1);
    must(n>0&&strstr(message,"987654321")!=NULL,"forged JSON received only as untrusted data");
    int status=0;
    must(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0,"child exited cleanly");
    close(peer);close(server);
    must(unlink(path)==0,"socket cleanup");
    must(rmdir(folder)==0,"private directory cleanup");
    printf("PASS Darwin getpeereid UID/GID + LOCAL_PEERPID: real subprocess, fake JSON ignored; no audio device\n");
    return 0;
}
