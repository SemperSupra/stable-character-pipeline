"""R014 evidence-based automatic video QA. Non-photoreal technical research only.

Never infer human identity, gender or sex from pixels. Compare source-controlled
body-shape macro labels and rig receipts, assess frame coverage, temporal quality,
model resolution and authored motion capability separately. A green CI step does
not mean an accepted character or video.
"""
import argparse,hashlib,json,subprocess,unittest
from pathlib import Path
import cv2
import numpy as np

MACRO={"female":0.0,"male":1.0}

def validate_provenance(sex,gen,motion,studio):
    problems=[]
    actor={x["sex"]:x for x in gen.get("characters",[])}
    if set(actor)!={"female","male"}:problems.append("SOURCE_ACTORS_MISSING")
    elif actor[sex].get("source_gender_macro")!=MACRO[sex]:problems.append("SOURCE_PRESET_INVERTED")
    if motion.get("actor")!=sex or motion.get("source_gender_macro")!=MACRO[sex]:
        problems.append("MOTION_ACTOR_PRESET_MISMATCH")
    if motion.get("source_run")!=43207664661 or motion.get("source_artifact")!="r014-mpfb-eye-MAKESKIN-lookdev":
        problems.append("WRONG_SOURCE_ARTIFACT")
    if gen.get("eye_material_mode")!="MAKESKIN":problems.append("UNQUALIFIED_EYE_MATERIAL")
    if motion.get("source_rig_bones")!=163 or actor.get(sex,{}).get("body_vertices")!=19158:
        problems.append("SOURCE_RIG_OR_VERTICES_DRIFT")
    candidates=[x for x in studio.get("selected_realistic_bases",[]) if x.get("name","").lower()==("geo-body_"+sex+"_realistic")]
    if len(candidates)!=1 or candidates[0].get("rigged") is not False:
        problems.append("SCULPT_SOURCE_UNEXPECTED")
    return problems

def probe_video(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_name,pix_fmt,width,height,nb_frames",
                       "-show_entries","format=duration,bit_rate","-select_streams","v:0","-of","json",str(path)],
                      check=True,capture_output=True,text=True)
    return json.loads(p.stdout)

def foreground(im):
    h,w=im.shape[:2]
    corners=np.concatenate((im[:18,:18].reshape(-1,3),im[-18:,:18].reshape(-1,3),
                            im[:18,-18:].reshape(-1,3),im[-18:,-18:].reshape(-1,3)))
    bg=np.median(corners.astype(np.float32),axis=0)
    binary=(np.linalg.norm(im.astype(np.float32)-bg,axis=2)>22).astype(np.uint8)
    binary=cv2.morphologyEx(binary,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,labels,stats,_=cv2.connectedComponentsWithStats(binary,8)
    if n<2:return np.zeros((h,w),np.uint8),[0,0,0,0],0
    idx=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    box=stats[idx,:4].astype(int).tolist()
    x,y,bw,bh=box
    return (labels==idx).astype(np.uint8),box,min(x,y,w-x-bw,h-y-bh)

def qa(sex,path,motion,gen,studio):
    evidence=probe_video(path)
    cv=cv2.VideoCapture(str(path))
    assert cv.isOpened(),"cannot decode source video"
    frames=[]
    while True:
        ok,im=cv.read()
        if not ok:break
        frames.append(im)
    cv.release()
    assert len(frames)>0,"empty video stream"
    masks=[];boxes=[];margins=[]
    for frame in frames:
        m,b,margin=foreground(frame)
        masks.append(m);boxes.append(b);margins.append(margin)
    h,w=frames[0].shape[:2]
    ious=[];changed=[];optical=[]
    for i in range(len(frames)-1):
        m0,m1=masks[i],masks[i+1]
        union=np.count_nonzero(m0|m1)
        ious.append(float(np.count_nonzero(m0&m1)/union if union else 0.))
        changed.append(float(np.count_nonzero(m0!=m1)/(w*h)))
        gray0=cv2.cvtColor(frames[i],cv2.COLOR_BGR2GRAY)
        gray1=cv2.cvtColor(frames[i+1],cv2.COLOR_BGR2GRAY)
        flow=cv2.calcOpticalFlowFarneback(gray0,gray1,None,.5,3,15,3,5,1.2,0)
        mask=(m0|m1).astype(bool)
        optical.append(float(np.median(np.linalg.norm(flow,axis=2)[mask])) if mask.any() else 0.)
    errors=validate_provenance(sex,gen,motion,studio)
    fmt=evidence["streams"][0]
    if fmt.get("codec_name")!="h264":errors.append("NOT_H264")
    if fmt.get("pix_fmt")!="yuv420p":errors.append("NONPORTABLE_PIXEL_FORMAT")
    if len(frames)!=72 or abs(float(evidence["format"]["duration"])-3)>0.05:
        errors.append("FRAME_COUNT_OR_DURATION")
    if min(margins)<5:errors.append("FRAME_EDGE_CROP")
    if min(np.count_nonzero(m)/(w*h) for m in masks)<.012:errors.append("ABSENT_CHARACTER")
    if np.percentile(ious,2)<.73:errors.append("SILHOUETTE_JUMP")
    if np.percentile(changed,90)<.00002:errors.append("NEARLY_STATIC_VIDEO")
    # These are mandatory qualitative gates, deliberately never auto-waived.
    holds=[
        "NO_4K_HIGH_RES_RENDER_448x576",
        "MPFB_BASE_NOT_BLENDER_STUDIO_MULTRES_SCUlPT",
        "NO_PHOTOREAL_SKIN_EYE_HAIR_QUALIFICATION",
        "NO_AUTHORED_FACS_OR_LIP_SYNC",
        "NO_AUTHORED_FINGER_JOINT_GESTURES",
        "NO_FOOT_CONTACT_OR_FORWARD_GAIT",
        "NO_COMPLETE_EXTERNAL_REPRODUCTIVE_ANATOMY_QUALIFICATION",
        "NO_CALIBRATED_VOLUME_COLLISION_SOFT_TISSUE"
    ]
    metrics={
      "frames":len(frames),"seconds":float(evidence["format"]["duration"]),
      "resolution":[w,h],"bitrate_kbps":float(evidence["format"]["bit_rate"])/1000,
      "foreground_min_percent":float(min(np.count_nonzero(m)/(w*h) for m in masks)*100),
      "foreground_median_percent":float(np.median([np.count_nonzero(m)/(w*h) for m in masks])*100),
      "subject_median_height_percent":float(np.median([b[3]/h*100 for b in boxes])),
      "border_margin_min_pixels":min(margins),
      "silhouette_iou_median":float(np.median(ious)),
      "silhouette_iou_p02":float(np.percentile(ious,2)),
      "changed_foreground_p90":float(np.percentile(changed,90)),
      "optical_flow_median_px_per_frame":float(np.median(optical)),
    }
    return {"actor":sex,"visual_quality":"HOLD","provenance_errors":errors,
            "promotion_holds":holds,"source_sex_shape_preset":MACRO[sex],
            "sex_label_validation":"SOURCE_MACRO_CONSISTENT_NOT_PIXEL_CLASSIFICATION" if not errors else "HOLD",
            "current_render_model":"MPFB textured adult (19158 source verts, 163 bone rig)",
            "higher_detail_model":"Blender Studio CC0 sculpt (10582 BASE verts and Multires) NOT rig-qualified or used",
            "video_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "metrics":metrics,
            "limitations":["Foreground segmentation assumes fixed studio background; not a general human detector",
                           "2D optical flow is not a physical/biomechanical motion test",
                           "No automated sex inference from appearance, no medical genital anatomy acceptance",
                           "This qualifies instrumented evidence capture, never photoreal video release"]},frames,boxes

def render_sheet(out,sex,frames,boxes):
    ids=[0,round(len(frames)*.12),round(len(frames)*.3),round(len(frames)*.53),
         round(len(frames)*.74),len(frames)-1]
    cards=[]
    for i in ids:
        img=frames[i].copy()
        x,y,w,h=boxes[i]
        cv2.rectangle(img,(x,y),(x+w,y+h),(0,95,250),2)
        cv2.putText(img,sex.upper()+"  f="+str(i+1),(10,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),2)
        cards.append(cv2.resize(img,(320,411),interpolation=cv2.INTER_AREA))
    cv2.imwrite(str(out),np.vstack((np.hstack(cards[:3]),np.hstack(cards[3:]))))

class NegativeControls(unittest.TestCase):
    def test_correct_macros(self):
        g={"eye_material_mode":"MAKESKIN","characters":[{"sex":"female","source_gender_macro":0.0,"body_vertices":19158},{"sex":"male","source_gender_macro":1.0,"body_vertices":19158}]}
        r={"actor":"female","source_gender_macro":0,"source_run":43207664661,"source_artifact":"r014-mpfb-eye-MAKESKIN-lookdev","source_rig_bones":163}
        s={"selected_realistic_bases":[{"name":"GEO-body_female_realistic","rigged":False}]}
        self.assertEqual(validate_provenance("female",g,r,s),[])
        g["characters"][0]["source_gender_macro"]=1.0
        self.assertIn("SOURCE_PRESET_INVERTED",validate_provenance("female",g,r,s))
    def test_missing_body(self):
        x=np.full((128,128,3),160,dtype=np.uint8)
        m,b,margin=foreground(x)
        self.assertEqual(np.count_nonzero(m),0)
    def test_detects_visible_geometry(self):
        x=np.full((128,128,3),160,dtype=np.uint8)
        cv2.rectangle(x,(30,20),(98,110),(210,185,170),-1)
        m,b,margin=foreground(x)
        self.assertGreater(m.mean(),.3)
        self.assertGreater(margin,5)

if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        p=argparse.ArgumentParser()
        p.add_argument("--sex",choices=["female","male"],required=True)
        p.add_argument("--video",type=Path,required=True)
        p.add_argument("--receipt",type=Path,required=True)
        p.add_argument("--generation",type=Path,required=True)
        p.add_argument("--studio",type=Path,required=True)
        p.add_argument("--out",type=Path,required=True)
        a=p.parse_args()
        a.out.mkdir(parents=True,exist_ok=True)
        evidence,frames,boxes=qa(a.sex,a.video,json.loads(a.receipt.read_text()),
                                 json.loads(a.generation.read_text()),json.loads(a.studio.read_text()))
        (a.out/"qa.json").write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")
        render_sheet(a.out/"visual_diagnostics.png",a.sex,frames,boxes)
        print("R014_VIDEO_QA",json.dumps({k:v for k,v in evidence.items() if k!="limitations"},sort_keys=True))
        if evidence["provenance_errors"]:
            raise SystemExit("FAIL_CROSS_SOURCE_PROVENANCE: "+str(evidence["provenance_errors"]))
