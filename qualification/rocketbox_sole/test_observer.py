"""Deterministic independent falsifiers; synthetic tests do not prove actual gait."""
import math,unittest
from observer import ROOTS,SIDES,FRAMES,metrics
def fixture():
    rows=[]
    for i in range(FRAMES):
        row={}
        for a in ROOTS:
            for s in SIDES:
                row[a+':'+s]={'min_z':.02 if i<4 else .15,'x':i*.01,'y':0.0}
        rows.append(row)
    return rows
class Test(unittest.TestCase):
    def test_synthetic_near_floor_no_large_slide(self):
        r=metrics(fixture(),0)
        self.assertEqual(r[ROOTS[0]]['L']['consecutive_near_ground_pairs'],3)
        self.assertEqual(r[ROOTS[0]]['L']['classification'],'NO_LARGE_SLIDE_IN_OBSERVED_NEAR_GROUND_WINDOWS')
    def test_forged_slide_detected(self):
        x=fixture()
        for i in range(1,4):x[i][ROOTS[0]+':L']['x']+=i*.12
        self.assertEqual(metrics(x,0)[ROOTS[0]]['L']['classification'],'OBSERVED_POSSIBLE_SLIDE')
    def test_airborne_no_ground_truth(self):
        x=fixture()
        for row in x:
            for v in row.values():v['min_z']=.2
        self.assertEqual(metrics(x,0)[ROOTS[0]]['R']['classification'],'UNKNOWN_NO_CONSECUTIVE_NEAR_GROUND_SAMPLES')
    def test_deep_penetration_not_contact(self):
        x=fixture()
        for row in x:
            for v in row.values():v['min_z']=-.25
        self.assertEqual(metrics(x,0)[ROOTS[1]]['L']['classification'],'UNKNOWN_NO_CONSECUTIVE_NEAR_GROUND_SAMPLES')
    def test_nonfinite_point_denied(self):
        x=fixture();x[2][ROOTS[0]+':L']['x']=float('nan')
        with self.assertRaisesRegex(ValueError,'NONFINITE_FOOT_REGION'):metrics(x,0)
    def test_boolean_point_denied(self):
        x=fixture();x[2][ROOTS[0]+':L']['y']=True
        with self.assertRaisesRegex(ValueError,'NONFINITE_FOOT_REGION'):metrics(x,0)
    def test_nonfinite_ground_denied(self):
        with self.assertRaisesRegex(ValueError,'GROUND_NONFINITE'):metrics(fixture(),float('inf'))
    def test_71_frames_denied(self):
        with self.assertRaisesRegex(ValueError,'FRAME_COUNT_NOT_72'):metrics(fixture()[:-1],0)
if __name__=='__main__':unittest.main()
