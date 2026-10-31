"""R14 independent source-exact SBOM identity check; never emits release approval."""
import re
from release_admission import inspect
SHA40=re.compile(r"^[0-9a-f]{40}$")
SHA64=re.compile(r"^sha256:[0-9a-f]{64}$")

def verify(bom):
  verdict=inspect(bom)
  metadata=bom.get("metadata",{})
  component=metadata.get("component")
  if not isinstance(component,dict) or not isinstance(component.get("version"),str) or not SHA40.fullmatch(component["version"]):
    raise ValueError("UNBOUND_GIT_SOURCE")
  props={item["name"]:item["value"] for item in metadata["properties"]}
  if props.get("scp:private-r009")!="NOT_RUN_NOT_ADMITTED":
    raise ValueError("PRIVATE_RUNNER_OR_SOURCE_NOT_HELD")
  if not isinstance(props.get("scp:observed-local-image-id"),str) or not SHA64.fullmatch(props["scp:observed-local-image-id"]):
    raise ValueError("IMAGE_ID_NOT_PINNED")
  if not isinstance(props.get("scp:base-manifest-digest"),str) or not SHA64.fullmatch(props["scp:base-manifest-digest"]):
    raise ValueError("BASE_MANIFEST_NOT_PINNED")
  for c in bom["components"]:
    if c.get("hashes") or c.get("licenses"):
      raise ValueError("UNVERIFIED_RIGHTS_OR_BINARY_DIGEST_CLAIM")
    states=c.get("properties")
    if not isinstance(states,list):raise ValueError("COMPONENT_PROVENANCE_ABSENT")
    observed={}
    for item in states:
      if (not isinstance(item,dict) or set(item)!={"name","value"}
          or type(item["name"]) is not str or type(item["value"]) is not str
          or item["name"] in observed):
        raise ValueError("COMPONENT_DUPLICATE_OR_MALFORMED_PROVENANCE")
      observed[item["name"]]=item["value"]
    if observed.get("scp:binary-hash-admission")!="UNKNOWN_NOT_CAPTURED" or observed.get("scp:license-admission")!="UNKNOWN_NOT_REVIEWED":
      raise ValueError("COMPONENT_SOURCE_ADMISSION_FORGED")
  return dict(verdict,git_source=component["version"],supply_provenance="UNKNOWN_ORIGINAL_BINARY_AND_RIGHTS")
