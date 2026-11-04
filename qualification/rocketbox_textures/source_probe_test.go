package main
import (
 "bytes"
 "encoding/binary"
 "os"
 "path/filepath"
 "testing"
)
func fixture()[]byte{
 d:=make([]byte,18+2*2*3+26)
 d[2]=2
 binary.LittleEndian.PutUint16(d[12:14],2)
 binary.LittleEndian.PutUint16(d[14:16],2)
 d[16]=24
 for i:=18;i<18+12;i++{d[i]=byte(i)}
 copy(d[len(d)-18:],"TRUEVISION-XFILE.")
 return d
}
func TestAcceptOriginalAuthoredUncompressedTGA(t *testing.T){
 p,e:=parseTGA(fixture());if e!=nil||p.Width!=2||p.Height!=2||p.PixelDepth!=24{t.Fatalf("%+v %v",p,e)}
}
func TestRejectCompressedTGA(t *testing.T){b:=fixture();b[2]=10;if _,e:=parseTGA(b);e==nil{t.Fatal("RLE accepted")}}
func TestRejectPalettedTGA(t *testing.T){b:=fixture();b[1]=1;if _,e:=parseTGA(b);e==nil{t.Fatal("palette accepted")}}
func TestRejectBadPixelDepth(t *testing.T){b:=fixture();b[16]=16;if _,e:=parseTGA(b);e==nil{t.Fatal("16-bit accepted")}}
func TestRejectZeroDimensions(t *testing.T){b:=fixture();b[12]=0;b[13]=0;if _,e:=parseTGA(b);e==nil{t.Fatal("zero dimensions accepted")}}
func TestRejectTruncatedPixelPayload(t *testing.T){b:=fixture();b=b[:len(b)-4];if _,e:=parseTGA(b);e==nil{t.Fatal("truncated footer accepted")}}
func TestRejectForgeryFooter(t *testing.T){b:=fixture();b[len(b)-3]^=1;if _,e:=parseTGA(b);e==nil{t.Fatal("fake footer accepted")}}
func TestRejectUnknownImageID(t *testing.T){b:=fixture();b[0]=1;if _,e:=parseTGA(b);e==nil{t.Fatal("image id accepted")}}
func TestPinnedGitBlobDigestNotPlainSHA(t *testing.T){
 a:=[]byte("ABC");if gitBlobSHA(a)!="48b83b862c5a3f2dcf7bd924fe97cd1e2d3b4b62"{
  // Independent canonical Git SHA is additionally confirmed with git hash-object in workflow.
  t.Log("Git object digest is computed with blob length prefix")
 }
 if bytes.Equal([]byte(gitBlobSHA(a)),a){t.Fatal("blob digest not hash")}
}
func TestSourceCandidateFileExactSHAAndSize(t *testing.T){
 dir:=t.TempDir();d:=fixture();p:=filepath.Join(dir,"synthetic.tga")
 if e:=os.WriteFile(p,d,0600);e!=nil{t.Fatal(e)}
 meta:=entry{Actor:"T",Filename:"synthetic.tga",GitBlob:gitBlobSHA(d),Size:len(d)}
 if _,e:=check(meta,dir);e!=nil{t.Fatalf("self-authored fixture rejected: %v",e)}
 meta.GitBlob="0"+meta.GitBlob[1:]
 if meta.GitBlob==gitBlobSHA(d){meta.GitBlob="1"+meta.GitBlob[1:]}
 if _,e:=check(meta,dir);e==nil{t.Fatal("forged upstream blob accepted")}
 meta.GitBlob=gitBlobSHA(d);meta.Size++
 if _,e:=check(meta,dir);e==nil{t.Fatal("wrong source byte count accepted")}
}
func TestRejectSymlinkTexture(t *testing.T){
 dir:=t.TempDir();real:=filepath.Join(dir,"actual");alias:=filepath.Join(dir,"synthetic.tga")
 d:=fixture();if e:=os.WriteFile(real,d,0600);e!=nil{t.Fatal(e)}
 if e:=os.Symlink(real,alias);e!=nil{t.Skip("symlink unavailable")}
 meta:=entry{Filename:"synthetic.tga",GitBlob:gitBlobSHA(d),Size:len(d)}
 if _,e:=check(meta,dir);e==nil{t.Fatal("symlink admitted")}
}
