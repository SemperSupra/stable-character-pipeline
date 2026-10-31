#!/usr/bin/env python3
"""Offline *observed inventory* to CycloneDX 1.6. Never a release/rights admission.

Inputs MUST be captured from the exact built source-safe worker, not user media.
No wheel/APT hashes are fabricated, and omitted licenses remain UNKNOWN.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
from urllib.parse import quote

SHA=re.compile(r"^[0-9a-f]{40}$")
DIGEST=re.compile(r"^sha256:[0-9a-f]{64}$")
PACKAGE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+:-]{0,159}$")
VERSION=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+~: -]{0,159}$")
BASE="sha256:94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd"

def fail(code):
    raise ValueError(code)

def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def parse_pip(data):
    versions={}
    for line in data.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        if line.count("==")!=1:fail("NONPINNED_PYTHON_REQUIREMENT")
        name,version=line.split("==")
        canonical=re.sub(r"[-_.]+","-",name).lower()
        if not PACKAGE.fullmatch(name) or not VERSION.fullmatch(version):fail("UNSAFE_PYTHON_VERSION")
        if canonical in versions:fail("DUPLICATE_PYTHON_PACKAGE")
        versions[canonical]=version
    if versions.get("bpy")!="4.5.0" or versions.get("numpy")!="1.26.4":
        fail("CORE_BLENDER_DEPENDENCY_DRIFT")
    if not (8<=len(versions)<=100):fail("UNEXPECTED_PYTHON_COMPONENT_COUNT")
    return versions

def parse_deb(data):
    versions={}
    for line in data.splitlines():
        if not line.strip():continue
        if line.count("\t")!=1:fail("DEBIAN_INVENTORY_NOT_TAB_SEPARATED")
        name,version=line.split("\t")
        if not PACKAGE.fullmatch(name) or not VERSION.fullmatch(version):
            fail("UNSAFE_DEBIAN_NAME_OR_VERSION")
        if name in versions:fail("DUPLICATE_DEBIAN_PACKAGE")
        versions[name]=version
    if not (150<=len(versions)<=2000) or "ffmpeg" not in versions:
        fail("DEBIAN_INVENTORY_INCOMPLETE")
    return versions

def create(pip_data,deb_data,source_sha,base_digest,image_id):
    if not SHA.fullmatch(source_sha):fail("SOURCE_SHA_INVALID")
    if base_digest!=BASE:fail("BASE_IMAGE_NOT_PINNED")
    if not DIGEST.fullmatch(image_id):fail("LOCAL_IMAGE_ID_INVALID")
    pip=parse_pip(pip_data);deb=parse_deb(deb_data)
    components=[]
    for name,version in sorted(pip.items()):
        purl="pkg:pypi/"+quote(name,safe="-")+"@"+quote(version,safe="._-")
        components.append({"type":"library","name":name,"version":version,"bom-ref":purl,"purl":purl,
            "properties":[{"name":"scp:binary-hash-admission","value":"UNKNOWN_NOT_CAPTURED"},
                          {"name":"scp:license-admission","value":"UNKNOWN_NOT_REVIEWED"}]})
    for name,version in sorted(deb.items()):
        purl="pkg:deb/debian/"+quote(name,safe="-.:")+"@"+quote(version,safe="._~:+-")+"?distro=debian-12"
        components.append({"type":"library","name":name,"version":version,"bom-ref":purl,"purl":purl,
            "properties":[{"name":"scp:binary-hash-admission","value":"UNKNOWN_NOT_CAPTURED"},
                          {"name":"scp:license-admission","value":"UNKNOWN_NOT_REVIEWED"}]})
    result={"bomFormat":"CycloneDX","specVersion":"1.6","version":1,
        "metadata":{"component":{"type":"application","name":"scp-native-worker-source-safe-qualification",
                "version":source_sha},
                "properties":[
                 {"name":"scp:admission","value":"UNKNOWN_NOT_RELEASE_QUALIFIED"},
                 {"name":"scp:base-manifest-digest","value":base_digest},
                 {"name":"scp:observed-local-image-id","value":image_id},
                 {"name":"scp:python-freeze-sha256","value":"sha256:"+hashlib.sha256(pip_data.encode()).hexdigest()},
                 {"name":"scp:debian-inventory-sha256","value":"sha256:"+hashlib.sha256(deb_data.encode()).hexdigest()},
                 {"name":"scp:private-r009","value":"NOT_RUN_NOT_ADMITTED"},
                 {"name":"scp:human-gait","value":"UNKNOWN_OR_FAIL_ABSTRACT_PROXY"},
                 {"name":"scp:transitive-original-byte-lock","value":"UNKNOWN_NOT_PINNED"},
                 {"name":"scp:license-and-vulnerability-admission","value":"UNKNOWN_NOT_QUALIFIED"}]},
        "components":sorted(components,key=lambda c:c["bom-ref"])}
    if len(result["components"])!=len({c["bom-ref"] for c in result["components"]}):
        fail("BOM_REF_COLLISION")
    return result

def main():
    p=argparse.ArgumentParser()
    for x in ("pip","deb","out","source-sha","base-digest","image-id"):
        p.add_argument("--"+x,required=True)
    x=p.parse_args()
    try:
        out=create(Path(x.pip).read_text(),Path(x.deb).read_text(),
                   x.source_sha,x.base_digest,x.image_id.strip())
    except ValueError as err:
        raise SystemExit("SOURCE_SAFE_INVENTORY_HOLD: "+str(err))
    Path(x.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("OBSERVED_SBOM_ONLY_NO_LICENSE_OR_HASH_ADMISSION",len(out["components"]))
if __name__=="__main__":
    main()
