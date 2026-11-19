"""N03D-F1 explicit source-shoe rest vertex influences to native foot bone labels.
Rig labels only; no anatomical acceptance, no contact solver, no source scene mutation.
"""
def choose_side(masses,threshold=.85,gap=.25):
 if not isinstance(masses,dict) or set(masses)!={"L","R"}:raise ValueError("INVALID_SIDE_COUNTS")
 l,r=masses["L"],masses["R"]
 if not all(type(x) in (float,int) and x>=0 for x in (l,r)):raise ValueError("BAD_GROUP_MASS")
 total=l+r
 if total<1e-8:return {"label":"UNKNOWN","dominance":0.,"reason":"NO_ACTUAL_FOOT_WEIGHT"}
 label="L" if l>r else "R"
 dominant=max(l,r)/total
 if dominant<threshold or abs(l-r)/total<gap:
  return {"label":"UNKNOWN","dominance":round(dominant,6),"reason":"SIDE_WEIGHT_AMBIGUOUS"}
 return {"label":label,"dominance":round(dominant,6),"reason":"CANDIDATE_SOURCE_RIG_SIDE_NOT_ANATOMICAL"}
