#!/usr/bin/env python3
"""Acquire exact public binary wheels, record hashes, and build offline hash lock.

All wheel source is the public Python index. This is original-byte qualification,
not supply-chain licensing/vulnerability admission or real private character use.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sbom_inventory"))
import observed
MAX_WHEEL=700*1024*1024
MAX_TOTAL=900*1024*1024
def fail(reason): raise ValueError(reason)
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def collect(freeze,output,pip_cmd=None):
    if pip_cmd is None:pip_cmd=[sys.executable,"-m","pip"]
    found=observed.parse_pip(freeze)
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    wheelhouse=out/"wheelhouse";wheelhouse.mkdir(exist_ok=True)
    downloads=out/"downloads";downloads.mkdir(exist_ok=True)
    metadata=[]
    total=0
    for name,version in sorted(found.items()):
        dest=downloads/name
        if dest.exists() and any(dest.iterdir()):fail("PREEXISTING_UNVERIFIED_DOWNLOAD_DIR")
        dest.mkdir(exist_ok=True)
        args=[*pip_cmd,"download","--disable-pip-version-check","--no-input",
              "--only-binary=:all:","--no-deps","--dest",str(dest),f"{name}=={version}"]
        subprocess.run(args,check=True,timeout=180,
                       env={**os.environ,"PIP_DISABLE_PIP_VERSION_CHECK":"1"})
        files=list(dest.iterdir())
        if len(files)!=1 or files[0].suffix!=".whl" or files[0].is_symlink():
            fail("AMBIGUOUS_OR_UNSAFE_WHEEL_DOWNLOAD")
        file=files[0]
        if file.stat().st_size<100 or file.stat().st_size>MAX_WHEEL:
            fail("WHEEL_BYTE_BUDGET_EXCEEDED")
        total+=file.stat().st_size
        if total>MAX_TOTAL:fail("WHEELHOUSE_TOTAL_EXCEEDED")
        copy=wheelhouse/file.name
        if copy.exists():fail("WHEEL_FILENAME_COLLISION")
        shutil.copy2(file,copy)
        h=digest(file)
        if digest(copy)!=h:fail("STAGED_WHEEL_BYTE_HASH_DRIFT")
        metadata.append({"name":name,"version":version,"file":file.name,
                         "sha256":h,"bytes":file.stat().st_size})
    requirements="".join(f'{x["name"]}=={x["version"]} --hash=sha256:{x["sha256"]}\n' for x in metadata)
    (out/"requirements-hashed.txt").write_text(requirements)
    result={"schema":"scp.r8b.public-wheel-bytes.v1",
            "status":"WHEEL_ORIGINAL_BYTES_CAPTURED_OFFLINE_INSTALL_PENDING",
            "python":"cp311_linux_amd64",
            "packages":metadata,
            "package_count":len(metadata),
            "total_wheel_bytes":total,
            "requirements_sha256":hashlib.sha256(requirements.encode()).hexdigest(),
            "release":"HELD_R009_NOT_ADMITTED",
            "debian_apt_original_byte_lock":"UNKNOWN",
            "wheel_license_and_vulnerability_review":"UNKNOWN"}
    (out/"wheel-lock-candidate.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--freeze",required=True);p.add_argument("--out",required=True)
    args=p.parse_args()
    try:
        r=collect(Path(args.freeze).read_text(),args.out)
    except (ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
        raise SystemExit("WHEEL_OBSERVATION_FAILED:"+str(e))
    print("WHEELS_CAPTURED_ORIGINAL_BYTES_NOT_LICENSE_ADMITTED",r["package_count"],r["total_wheel_bytes"])
if __name__=="__main__":main()
