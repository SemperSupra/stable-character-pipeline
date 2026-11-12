"""Resumable exact-hash public source archive acquisition for disposable CI.

Retains only partial bytes *inside the same ephemeral runner*. A successful
download must match both pinned byte count and SHA-256. No implicit fallback
mirrors, trust-on-first-use, or unsigned caches.
"""
import argparse,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path

PINNED_BYTES=280737770
PINNED_SHA="b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107"
SOURCE_URL=("https://files2.makehumancommunity.org/asset_packs/"
            "makehuman_system_assets/makehuman_system_assets_cc0.zip")

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def curl_fetch(path,offset,timeout):
    # HTTP range is mandatory for existing bytes. curl fails if the server
    # does not honor a resume request, instead of appending a duplicate blob.
    cmd=["curl","--fail","--location","--silent","--show-error",
         "--connect-timeout","25","--max-time",str(timeout),
         "--retry","0","--continue-at","-","--output",str(path),SOURCE_URL]
    run=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return run.returncode,run.stderr[-1600:]

def acquire(path,expected_size,expected_hash,fetcher,max_attempts=14):
    path.parent.mkdir(parents=True,exist_ok=True)
    stalls=0
    history=[]
    for attempt in range(1,max_attempts+1):
        old=path.stat().st_size if path.exists() else 0
        if old>expected_size:raise ValueError("partial file exceeds expected source size")
        if old==expected_size:
            observed=digest(path)
            if observed!=expected_hash:raise ValueError("complete archive SHA256 mismatches pinned publisher bytes")
            return {"status":"PASS_PINNED_ARCHIVE_VERIFIED",
                    "source_url":SOURCE_URL,"sha256":observed,
                    "bytes":old,"fetch_attempts":len(history),
                    "progress_bytes":[item["delta"] for item in history]}
        rc,detail=fetcher(path,old)
        now=path.stat().st_size if path.exists() else 0
        if now<old or now>expected_size:
            raise ValueError("invalid partial download length")
        delta=now-old
        history.append({"attempt":attempt,"offset":old,"returncode":rc,"delta":delta})
        print("R014_ARCHIVE_PROGRESS",json.dumps(history[-1],sort_keys=True),flush=True)
        if now==expected_size:
            observed=digest(path)
            if observed!=expected_hash:
                raise ValueError("complete resumed archive SHA256 mismatch")
            return {"status":"PASS_PINNED_ARCHIVE_VERIFIED",
                    "source_url":SOURCE_URL,"sha256":observed,
                    "bytes":now,"fetch_attempts":len(history),
                    "progress_bytes":[item["delta"] for item in history]}
        if delta==0:
            stalls+=1
            if stalls>=3:raise RuntimeError("resumable transfer made no progress for three attempts: "+detail)
        else:stalls=0
    raise RuntimeError("source archive still incomplete after bounded resumable attempts")

class Controls(unittest.TestCase):
    def test_partial_then_resume_with_exact_sha(self):
        expected=b"ABCDEF" * 100
        h=hashlib.sha256(expected).hexdigest()
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"asset.bin"
            calls=[]
            def mock(path,offset):
                calls.append(offset)
                with path.open("ab") as f:
                    f.write(expected[offset:offset+250])
                return (28 if len(calls)==1 else 0),""
            r=acquire(path,len(expected),h,mock,5)
            self.assertEqual(r["status"],"PASS_PINNED_ARCHIVE_VERIFIED")
            self.assertEqual(calls,[0,250,500])
    def test_wrong_digest_never_promoted(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"a"
            def mock(path,offset):
                path.write_bytes(b"bad")
                return 0,""
            with self.assertRaisesRegex(ValueError,"SHA256"):
                acquire(path,3,hashlib.sha256(b"good").hexdigest(),mock)
    def test_no_progress_is_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(RuntimeError,"no progress"):
                acquire(Path(t)/"a",10,"0"*64,lambda path,offset:(28,"timeout"),8)
    def test_overrun_fails(self):
        with tempfile.TemporaryDirectory() as t:
            def mock(path,offset):
                path.write_bytes(b"12345")
                return 0,""
            with self.assertRaisesRegex(ValueError,"invalid partial"):
                acquire(Path(t)/"a",4,"0"*64,mock)
    def test_preserves_preexisting_partial(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"a";path.write_bytes(b"abc")
            expected=b"abcdef"
            def mock(path,offset):
                self.assertEqual(offset,3)
                with path.open("ab") as f:f.write(b"def")
                return 0,""
            self.assertEqual(acquire(path,len(expected),hashlib.sha256(expected).hexdigest(),mock)["fetch_attempts"],1)
if __name__=="__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        p=argparse.ArgumentParser()
        p.add_argument("--out",required=True,type=Path)
        p.add_argument("--receipt",required=True,type=Path)
        p.add_argument("--max-attempts",type=int,default=14)
        p.add_argument("--per-attempt-seconds",type=int,default=240)
        a=p.parse_args()
        if not (1<=a.max_attempts<=20) or not (60<=a.per_attempt_seconds<=360):
            p.error("invalid bounds")
        result=acquire(a.out,PINNED_BYTES,PINNED_SHA,
                       lambda path,offset:curl_fetch(path,offset,a.per_attempt_seconds),
                       max_attempts=a.max_attempts)
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("R014_ARCHIVE_VERIFIED",json.dumps(result,sort_keys=True))
