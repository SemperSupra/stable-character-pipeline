"""Source-free, hostile fixture qualification for strict R009 research gates."""
import copy,unittest
from skirt_bounded_research_gate_v1 import evaluate,BoundedGateError
from triangle_vertex_contact_gate_v1 import SLOTS,ACTORS
BASE='a'*64
NEW='b'*64

def fixture():
    frames=['rest',*range(72)]
    def pair(sha,trial):
        bvh={'schema':'scp.r009.makehuman35.triangle_bvh_contact.v1','source_sha256':sha,
             'frames':frames.copy(),'frame_count':73,'actors':{},'backend':'synthetic_fixture',
             'vertex_signed_inclusion_qualified':False,'native_blender_evaluated':False,
             'cloth_physics_qualified':False,'no_triangle_crossing_proven':False,
             'wearable_fit_accepted':False,'natural_gait_accepted':False,'release_approved':False}
        signed={'schema':'scp.r009.makehuman35.signed_wardrobe_contact_sample.v0','source_sha256':sha,
                'witness_frames':frames.copy(),'actors':{},'native_blender_evaluated':False,
                'cloth_fitting_accepted':False,'release_approved':False}
        for actor in ACTORS:
            bvh['actors'][actor]={'slots':{}}
            signed['actors'][actor]={'slots':{}}
            for slot in SLOTS:
                changed=trial and actor=='JuniperOriginal' and slot=='costume_bottom'
                bvh['actors'][actor]['slots'][slot]=[
                  {'frame':frame,'triangle_contact_pairs':2 if changed else 3,
                   'body_triangle_count':100,'garment_triangle_count':100} for frame in frames]
                signed['actors'][actor]['slots'][slot]=[
                  {'frame':frame,'negative_gt_5mm_fraction':.005 if changed else .01,
                   'sign_calibrated':True} for frame in frames]
            bvh['actors'][actor]['any_crossings']=True
        bvh['any_crossings']=True
        bvh['interpretation']='SURFACE_TRIANGLE_CROSSINGS_OBSERVED'
        strain={'schema':'scp.r009.skirt_cpu72_edge_strain.v1','source_sha256':sha,
                'frames':72,'actors':{},'native_blender_evaluated':False,
                'physical_cloth_qualified':False,'garment_fit_accepted':False,'release_approved':False}
        for actor in ACTORS:
            changed=trial and actor=='JuniperOriginal'
            strain['actors'][actor]=[
                {'frame':i,'p99_edge_ratio':1.05 if changed else 1.0,
                'max_edge_ratio':1.08 if changed else 1.0,
                'min_edge_ratio':.94 if changed else 1.0,
                'min_triangle_area_ratio':.91 if changed else 1.0,
                'fraction_strained_gt_50pct':0.,'fraction_area_lt_quarter':0.} for i in range(72)]
        return bvh,signed,strain
    b=pair(BASE,False);c=pair(NEW,True)
    return b[0],b[1],c[0],c[1],b[2],c[2]

class BoundedGateTests(unittest.TestCase):
    def test_pass_means_research_only(self):
        r=evaluate(*fixture())
        self.assertEqual(r['verdict'],'PASS_BOUNDED_RELATIVE_RESEARCH_ONLY')
        self.assertEqual(r['contact_improvement_count'],146)
        self.assertFalse(r['garment_fit_accepted'])
    def test_one_triangle_regression_red(self):
        f=list(fixture());f[2]['actors']['JuniperOriginal']['slots']['costume_bottom'][4]['triangle_contact_pairs']=5
        self.assertEqual(evaluate(*f)['verdict'],'RED_CONTACT_REGRESSION')
    def test_one_vertex_regression_red(self):
        f=list(fixture());f[3]['actors']['JuniperOriginal']['slots']['costume_bottom'][5]['negative_gt_5mm_fraction']=.015
        self.assertEqual(evaluate(*f)['verdict'],'RED_CONTACT_REGRESSION')
    def test_large_stretch_red(self):
        f=list(fixture());f[5]['actors']['JuniperOriginal'][2]['max_edge_ratio']=1.151
        self.assertEqual(evaluate(*f)['verdict'],'RED_DEFORMATION_ENVELOPE')
    def test_collapse_red(self):
        f=list(fixture());f[5]['actors']['JuniperOriginal'][2]['min_triangle_area_ratio']=.79
        self.assertEqual(evaluate(*f)['verdict'],'RED_DEFORMATION_ENVELOPE')
    def test_other_actor_change_hard_fails(self):
        f=list(fixture());f[2]['actors']['AsterOriginal']['slots']['costume_top'][3]['triangle_contact_pairs']=2
        with self.assertRaises(BoundedGateError):evaluate(*f)
    def test_other_actor_strain_hard_fails(self):
        f=list(fixture());f[5]['actors']['AsterOriginal'][3]['max_edge_ratio']=1.02
        with self.assertRaises(BoundedGateError):evaluate(*f)
    def test_lying_physics_flag_hard_fails(self):
        f=list(fixture());f[5]['physical_cloth_qualified']=True
        with self.assertRaises(BoundedGateError):evaluate(*f)
    def test_hash_mismatch_hard_fails(self):
        f=list(fixture());f[5]['source_sha256']='c'*64
        with self.assertRaises(BoundedGateError):evaluate(*f)
    def test_dropped_frame_hard_fails(self):
        f=list(fixture());f[5]['actors']['JuniperOriginal'].pop()
        with self.assertRaises(BoundedGateError):evaluate(*f)
    def test_identical_source_hard_fails(self):
        f=list(fixture());f[5]['source_sha256']=BASE;f[2]['source_sha256']=BASE;f[3]['source_sha256']=BASE
        with self.assertRaises((BoundedGateError,ValueError)):evaluate(*f)
    def test_nonfinite_strain_hard_fails(self):
        f=list(fixture());f[5]['actors']['JuniperOriginal'][10]['p99_edge_ratio']=float('nan')
        with self.assertRaises(BoundedGateError):evaluate(*f)

if __name__=='__main__':unittest.main()
