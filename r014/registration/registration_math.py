"""Pure numerical R014 registration and bone-proximity diagnostics.

A nearest rig-bone segment is only a rough region classifier. It is not an
anatomical landmark correspondence, nor evidence of correct skinning.
"""
import numpy as np
import re
import unittest


def bone_region(name):
    n=name.lower()
    if n.startswith('finger') or n.startswith('wrist'):
        return 'hand'
    if any(t in n for t in ('upperarm', 'lowerarm', 'shoulder', 'clavicle')):
        return 'arm'
    if n.startswith('toe') or n.startswith('foot'):
        return 'foot'
    if any(t in n for t in ('upperleg', 'lowerleg')):
        return 'leg'
    if any(t in n for t in ('jaw', 'tongue', 'eye', 'head')):
        return 'head'
    if any(t in n for t in ('pelvis', 'hip')):
        return 'pelvis'
    if any(t in n for t in ('spine', 'neck', 'chest')):
        return 'torso'
    return None


def nearest_segment_region(points, segments):
    """Use bounded vectorization, no costly brute-force vertex-by-vertex rig loops."""
    pts=np.asarray(points,dtype=np.float64)
    assert pts.ndim==2 and pts.shape[1]==3 and np.all(np.isfinite(pts))
    nearest=np.full(len(pts),np.inf)
    labels=np.full(len(pts),'unassigned',dtype=object)
    sources=np.full(len(pts),'none',dtype=object)
    for name,start,end in segments:
        reg=bone_region(name)
        if not reg: continue
        a=np.asarray(start,dtype=np.float64)
        b=np.asarray(end,dtype=np.float64)
        axis=b-a
        denom=float(axis@axis)
        if denom<1e-11: continue
        u=np.clip((pts-a)@axis/denom,0,1)
        closest=a+u[:,None]*axis
        dist=np.linalg.norm(pts-closest,axis=1)
        update=dist<nearest
        nearest[update]=dist[update]
        labels[update]=reg
        sources[update]=name
    if np.any(~np.isfinite(nearest)):
        raise ValueError('unclassified body vertices without any source rig bones')
    return labels,sources,nearest


def stats(values):
    x=np.asarray(values,dtype=np.float64)
    if len(x)==0:
        return {'count':0,'status':'NO_COVERAGE'}
    if np.any(~np.isfinite(x)) or np.any(x<0):
        raise ValueError('invalid registration distances')
    return {
        'count':int(len(x)),
        'mean_m':float(x.mean()),
        'p50_m':float(np.percentile(x,50)),
        'p95_m':float(np.percentile(x,95)),
        'max_m':float(x.max()),
        'fraction_over_25mm':float(np.mean(x>.025)),
        'fraction_over_50mm':float(np.mean(x>.05)),
        'fraction_over_100mm':float(np.mean(x>.10)),
    }


def rgb(dist):
    anchors=[(0.,(.15,.57,.32)),(.025,(.42,.79,.38)),
             (.05,(.94,.86,.27)),(.10,(.91,.38,.12)),(.2,(.64,.09,.1))]
    x=max(0.,float(dist))
    if x>=anchors[-1][0]:return anchors[-1][1]
    for (l,c0),(r,c1) in zip(anchors,anchors[1:]):
        if l<=x<=r:
            f=(x-l)/(r-l)
            return tuple((1-f)*a+f*b for a,b in zip(c0,c1))
    return anchors[0][1]


class Controls(unittest.TestCase):
    def test_region_taxonomy(self):
        self.assertEqual(bone_region('finger2-1.L'),'hand')
        self.assertEqual(bone_region('upperarm01.R'),'arm')
        self.assertEqual(bone_region('upperleg01.L'),'leg')
        self.assertEqual(bone_region('jaw'),'head')
        self.assertIsNone(bone_region('unrelated_extra'))
    def test_nearest_segments(self):
        p=np.array([[0.,0.,0.],[2.,0.,0.]])
        s=[('finger1-1.L',[0.,0.,0.],[0.,0.,1.]),
           ('upperleg01.R',[2.,0.,0.],[2.,0.,1.])]
        labels,names,d=nearest_segment_region(p,s)
        self.assertEqual(labels.tolist(),['hand','leg'])
        self.assertTrue(np.allclose(d,0.))
    def test_error_stats_and_color_ends(self):
        x=stats([0,.025,.05,.2])
        self.assertEqual(x['count'],4)
        self.assertAlmostEqual(x['fraction_over_50mm'],.25)
        self.assertEqual(rgb(.3),(.64,.09,.1))
    def test_unsafe_inputs_fail(self):
        with self.assertRaises(ValueError):stats([float('nan')])
        with self.assertRaises(ValueError):nearest_segment_region(np.array([[0.,0.,0.]]),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
