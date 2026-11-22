"""Adversarial pure first-key factor controls used by actual Blender oracle."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from math_contract import step_metric,summarize_channels

class Co:
    def __init__(self,x,y):self.x=x;self.y=y
class Key:
    def __init__(self,x,y):self.co=Co(x,y)
class Curve:
    def __init__(self,i,ys):
        self.data_path='pose.bones["foot.L"].location'
        self.array_index=i
        self.keyframe_points=[Key(j,float(v)) for j,v in enumerate(ys)]

class NativeKeyFactor(unittest.TestCase):
    def test_frame_si_speed_from_exact_60hz(self):
        x=step_metric([(0.,0.,0.),(.02,0.,0.),(.025,0.,0.)])
        self.assertEqual(x["first_3d_speed_mps"],1.2)
        self.assertEqual(x["next_3d_speed_mps"],.3)

    def test_3d_not_xy_alone(self):
        x=step_metric([(0.,0.,0.),(0.,0.,.5),(0.,0.,.5)])
        self.assertEqual(x["first_xy_speed_mps"],0.)
        self.assertEqual(x["first_3d_speed_mps"],30.)

    def test_source_very_slow_and_native_fast_are_distinct(self):
        a=step_metric([(0.,0.,0.),(0.,.0001,0.),(0.,.0002,0.)])
        b=step_metric([(0.,0.,0.),(0.,.3,0.),(0.,.301,0.)])
        self.assertLess(a["first_3d_speed_mps"],.01)
        self.assertGreater(b["first_3d_speed_mps"],10.)

    def test_nonfinite_bool_rejection(self):
        for bad in (math.nan,math.inf,-math.inf,True):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                step_metric([(0.,0.,0.),(bad,0.,0.),(0.,0.,0.)])

    def test_bad_sample_count_and_dt(self):
        with self.assertRaisesRegex(ValueError,"INVALID_FIRST_KEY_SEQUENCE"):
            step_metric([(0.,0.,0.),(0.,0.,0.)])
        with self.assertRaisesRegex(ValueError,"INVALID_FIRST_KEY_SEQUENCE"):
            step_metric([(0.,0.,0.)]*3,dt=0.0)

    def test_action_first_key_localization(self):
        curves=[Curve(i,[0,20 if i==2 else 1,20.001 if i==2 else 1.01])
                for i in range(12)]
        out=summarize_channels(curves)
        self.assertEqual(out["inspected_animated_and_constant_channels"],12)
        self.assertEqual(out["top_12_first_key_channel_deltas"][0]["array_index"],2)
        self.assertTrue(out["values_mixed_units_no_raw_norm_conclusion"])

    def test_action_nonfinite_must_fail(self):
        curves=[Curve(i,[0,0,0]) for i in range(12)]
        curves[0].keyframe_points[1].co.y=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE"):
            summarize_channels(curves)

    def test_action_incomplete_curve_excluded_and_guarded(self):
        curves=[Curve(i,[0,1,2]) for i in range(9)]
        curves.append(Curve(10,[0,0,0]))
        curves[-1].keyframe_points.pop()
        with self.assertRaisesRegex(ValueError,"SOURCE_ACTION_FIRST_KEYS_INSUFFICIENT"):
            summarize_channels(curves)

if __name__=="__main__":unittest.main()
