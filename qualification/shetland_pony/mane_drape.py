"""Original pony long mane, forelock and tail drape guides.

Anchors are source-original synthetic. Gravity-aware guide vectors hang from
dorsal crest on both sides; unlike older grass-like upright hair. The guides
remain geometric cards in portable GLB, not full simulated hair strands.
"""
import math,random

def guides(rng):
    hair=[]
    # Long Shetland mane, parting over the neck and falling down on both sides.
    for i in range(440):
        side=-1 if i%2==0 else 1
        x=rng.uniform(.365,.705)
        y=side*rng.uniform(.042,.13)
        z=1.18+(x-.40)*.04+rng.uniform(-.012,.025)
        direction=(rng.uniform(-.16,.06),side*rng.uniform(.60,.95),rng.uniform(-.62,-.31))
        length=rng.uniform(.19,.36)
        hair.append(((x,y,z),direction,length,rng.uniform(.0023,.0048),
                     'neck' if x<.61 else 'head'))
    # Forward-falling flaxen forelock from ears onto forehead, not a hedgehog spike.
    for i in range(230):
        x=rng.uniform(.68,.82)
        y=rng.uniform(-.11,.11)
        z=rng.uniform(1.24,1.35)
        direction=(rng.uniform(.45,.78),rng.uniform(-.26,.26),rng.uniform(-.68,-.36))
        hair.append(((x,y,z),direction,rng.uniform(.15,.27),rng.uniform(.002,.004),'head'))
    # Long full tail hair with downward gravity field; no standing radial spikes.
    for i in range(380):
        x=rng.uniform(-.72,-.84)
        y=rng.uniform(-.080,.080)
        z=rng.uniform(.46,.86)
        direction=(rng.uniform(-.27,-.10),rng.uniform(-.24,.24),rng.uniform(-1.,-.73))
        hair.append(((x,y,z),direction,rng.uniform(.22,.43),rng.uniform(.0025,.0048),
                     'tail_1' if z>.69 else ('tail_2' if z>.51 else 'tail_3')))
    return hair

def validate_guides(hair):
    if len(hair)!=1050:raise ValueError("missing tuft guides")
    for point,vec,length,width,bone in hair:
        if bone not in ('neck','head','tail_1','tail_2','tail_3'):
            raise ValueError("unknown rig group")
        if not (.14<length<.44 and .001<width<.006):
            raise ValueError("unbounded hair geometry")
        if not all(math.isfinite(v) for v in (*point,*vec)):
            raise ValueError("non-finite groom guide")
        if vec[2]>=0:raise ValueError("upward grass-like guide")
    return {"schema":"equine.longhair.drape.v1","guide_count":len(hair),
            "mane":440,"forelock":230,"tail":380,
            "max_guide_length_m":max(g[2] for g in hair),
            "all_guides_downward":True,"source":"original synthetic; no source image on runner",
            "biological_quality":"UNQUALIFIED"}
