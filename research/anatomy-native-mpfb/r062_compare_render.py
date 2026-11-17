"""R062 exact RGBA8 matched native Blender render comparison with mutation control."""
import argparse
import hashlib
import json
from pathlib import Path

def hold(s):raise ValueError("R062_PIXEL_HOLD "+s)
def sha(x):return hashlib.sha256(x).hexdigest()

def compare(a,b,px,py):
    for v in (a,b):
        if v.get("schema")!="r062.original-synthetic-blender-cycles-render.v1" or v.get("status")!="PASS_NARROW_NATIVE_CPU_IMAGE_CAPTURE_ONLY":
            hold("actual native rendered image receipt required")
        if v.get("image_size")!=[128,128] or v.get("engine")!="CYCLES_CPU_SAMPLES_8_SEED_17":
            hold("unexpected renderer/resolution/seed")
        if v.get("original_synthetic_proxy_vertices")!=840 or min(v.get("channel_unique_value_counts",[])[:3])<10:
            hold("blank/failed actual two-proxy raster witness")
    if a["glb_sha256"]==b["glb_sha256"]:hold("source/derived bytes same; no experiment")
    for k in ("blender_version","engine","camera","image_size"):
        if a[k]!=b[k]:hold("render environment/camera not comparable "+k)
    if len(px)!=len(py) or len(px)!=128*128*4:hold("pixel buffer size mismatch")
    if sha(px)!=a["pixels_rgba8_sha256"] or sha(py)!=b["pixels_rgba8_sha256"]:
        hold("image file changed after hash receipt")
    channel_deltas=[abs(l-r) for l,r in zip(px,py)]
    mismatched=sum(x>0 for x in channel_deltas)
    rgb_deltas=[channel_deltas[i] for i in range(len(channel_deltas)) if i%4!=3]
    varying_pixels=sum(any(px[i+k]!=py[i+k] for k in range(3)) for i in range(0,len(px),4))
    return {
      "schema":"r062.original-synthetic-cycles-pixel-parity.v1",
      "status":"PASS_NARROW_MATCHED_8BIT_PIXELS" if mismatched==0 else "FAIL_NARROW_MATCHED_8BIT_PIXELS",
      "native_images_compared":2,
      "width":128,"height":128,
      "source_sha256":a["glb_sha256"],"derived_sha256":b["glb_sha256"],
      "mismatched_channels":mismatched,
      "mismatched_rgb_pixels":varying_pixels,
      "max_absolute_rgb_channel_delta_8bit":max(rgb_deltas) if rgb_deltas else 0,
      "mean_absolute_rgb_channel_delta_8bit":sum(rgb_deltas)/len(rgb_deltas) if rgb_deltas else 0,
      "source_rgba8_sha256":sha(px),"derived_rgba8_sha256":sha(py),
      "limits":"Exact 8-bit neutral-material fixed orthographic frame-1 synthetic proxy raster only. Not continuous smooth normal equivalence or visual acceptance on new lighting, real geometry or full animation."
    }

def main():
    p=argparse.ArgumentParser()
    for name in ("original","derived","original_pixels","derived_pixels","out"):
        p.add_argument("--"+name.replace("_","-"),required=True)
    args=p.parse_args()
    a=json.loads(Path(args.original).read_text())
    b=json.loads(Path(args.derived).read_text())
    pa=Path(args.original_pixels).read_bytes()
    pb=Path(args.derived_pixels).read_bytes()
    result=compare(a,b,pa,pb)
    changed=bytearray(pb); changed[12]=(changed[12]+1)%256
    mutated=dict(b);mutated["pixels_rgba8_sha256"]=sha(changed)
    if compare(a,mutated,pa,changed)["mismatched_channels"]==0:
        hold("deliberate pixel change not detected")
    result["negative_control"]={"pixel_mutation_detected":True}
    Path(args.out).write_text(json.dumps(result,sort_keys=True)+"\n")
    print("R062_CYCLES_PIXEL_PARITY "+json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
