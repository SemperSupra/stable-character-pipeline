"""Bounded offline review of observed package inventory, never a release permit."""
import json
import re

def inspect(bom):
    if not isinstance(bom, dict) or bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise ValueError("INVALID_INVENTORY_SCHEMA")
    components = bom.get("components")
    if not isinstance(components, list) or len(components) < 150:
        raise ValueError("INCOMPLETE_COMPONENT_INVENTORY")
    refs = []
    for entry in components:
        if not isinstance(entry, dict) or not isinstance(entry.get("bom-ref"), str):
            raise ValueError("INVALID_COMPONENT")
        refs.append(entry["bom-ref"])
    if len(set(refs)) != len(refs):
        raise ValueError("DUPLICATE_COMPONENT")
    meta = bom.get("metadata", {})
    props = meta.get("properties", [])
    if not isinstance(props, list):
        raise ValueError("INVALID_PROPERTIES")
    pairs = [(p.get("name"),p.get("value")) for p in props if isinstance(p,dict)]
    if len(pairs)!=len(props) or len(set(k for k,v in pairs)) != len(pairs):
        raise ValueError("DUPLICATE_PROPERTIES")
    marks = dict(pairs)
    if marks.get("scp:admission")!="UNKNOWN_NOT_RELEASE_QUALIFIED":
        raise ValueError("UNAUTHORIZED_PROMOTION")
    return {"schema":"scp.supply.review.v1","status":"HOLD_INDEPENDENT_ORIGINAL_BINARY_LICENSE_CVE_ISSUER_REVIEW",
            "component_count":len(components),"unverified_components":len(components)}
