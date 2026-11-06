import unittest
import math
from guide_dynamics import Guide,simulate,report,norm,sub

class GuideDynamicsTests(unittest.TestCase):
    def setUp(self):
        self.g=Guide((0.,0.,1.),(-.12,.0,-1.),.35)
    def test_deterministic_root_and_length(self):
        a=simulate(self.g,48,(-6.,.4,0.))
        b=simulate(self.g,48,(-6.,.4,0.))
        self.assertEqual(a,b)
        self.assertEqual(len(a),48)
        for p in a:
            self.assertEqual(p[0],self.g.root)
            for i in range(1,len(p)):
                self.assertLess(abs(norm(sub(p[i],p[i-1]))-.35/4),.00001)
    def test_wind_changes_tip(self):
        calm=simulate(self.g,48,(0.,0.,0.))
        fast=simulate(self.g,48,(-10.,0.,0.))
        self.assertLess(fast[-1][-1][0],calm[-1][-1][0]-.003)
        self.assertLess(report(self.g,48,(-6.,0.,0.))["max_root_drift_m"],1e-9)
    def test_shape_responds_to_length(self):
        long=Guide(self.g.root,self.g.direction,.6)
        p=simulate(long,24,(-4.,0.,0.))
        self.assertEqual(len(p[-1]),5)
        self.assertGreater(norm(sub(p[-1][-1],p[-1][0])),.3)
    def test_real_moving_root_impulse_and_followthrough(self):
        # A synthetic, smooth lateral tail-dock excursion; not a clinical
        # ROM profile. The strand root must follow exactly, while the tip
        # differs measurably from the zero-root-motion wind control.
        p=[(0.,0.,1.)]
        p.extend((0.,.065*math.sin(math.tau*(f-1)/48),1.) for f in range(1,49))
        a=simulate(self.g,48,(-4.,0.,0.),root_frames=p)
        b=simulate(self.g,48,(-4.,0.,0.),root_frames=p)
        static=simulate(self.g,48,(-4.,0.,0.))
        self.assertEqual(a,b)
        self.assertTrue(all(norm(sub(row[0],p[i+1]))<1e-9 for i,row in enumerate(a)))
        self.assertGreater(max(norm(sub(row[-1],other[-1]))
                               for row,other in zip(a,static)),.015)
        self.assertLess(report(self.g,48,(-4.,0.,0.),root_frames=p)["max_root_drift_m"],1e-9)
        self.assertTrue(all(abs(norm(sub(row[i],row[i-1]))-.35/4)<.00002
                            for row in a for i in range(1,len(row))))

    def test_hostile_root_trajectories(self):
        p=[self.g.root]*49
        for bad in (p[:-1],p+[self.g.root],
                    [(1.,0.,1.)]+p[1:],
                    [self.g.root]+[(math.nan,0.,1.)]*48,
                    [self.g.root]+[(4.,0.,1.)]*48):
            with self.assertRaises(ValueError):simulate(self.g,48,root_frames=bad)

    def test_optional_rest_force_reduces_raw_displacement_without_clamp_change(self):
        direct=(-.12,0.,-1.)
        n=math.sqrt(sum(x*x for x in direct))
        tip=tuple(self.g.root[i]+self.g.length*direct[i]/n for i in range(3))
        rest=[tip]*49
        baseline=simulate(self.g,48,(-8.,0.,0.))
        restored=simulate(self.g,48,(-8.,0.,0.),
                          rest_tip_frames=rest,rest_stiffness=60.)
        old_error=norm(sub(baseline[-1][-1],tip))
        new_error=norm(sub(restored[-1][-1],tip))
        self.assertLess(new_error,old_error)
        self.assertGreater(new_error,.0001)
        self.assertEqual(restored,simulate(self.g,48,(-8.,0.,0.),
                              rest_tip_frames=rest,rest_stiffness=60.))
        # Zero force, with or without declared rest targets, must be bit
        # identical to existing accepted source behavior.
        self.assertEqual(baseline,simulate(self.g,48,(-8.,0.,0.),
                               rest_tip_frames=rest,rest_stiffness=0.))

    def test_rest_force_respects_moving_source_root(self):
        direct=(-.12,0.,-1.);n=math.sqrt(sum(x*x for x in direct))
        tip=tuple(self.g.root[i]+self.g.length*direct[i]/n for i in range(3))
        root=[self.g.root]+[(0.,.04*math.sin(math.tau*f/48),1.) for f in range(1,49)]
        rest=[tip]+[tuple(tip[i]+(root[f][i]-root[0][i]) for i in range(3))
                    for f in range(1,49)]
        result=simulate(self.g,48,(-4.,0.,0.),root_frames=root,
                        rest_tip_frames=rest,rest_stiffness=60.)
        self.assertTrue(all(norm(sub(p[0],root[i+1]))<1e-9 for i,p in enumerate(result)))
        self.assertTrue(all(math.isfinite(v) for row in result for p in row for v in p))
        self.assertLess(max(norm(sub(row[i],row[i-1])) for row in result
                            for i in range(1,len(row))),.2)

    def test_rest_force_hostile_missing_nonfinite_wrong_origin_and_speed(self):
        direct=(-.12,0.,-1.);n=math.sqrt(sum(x*x for x in direct))
        tip=tuple(self.g.root[i]+self.g.length*direct[i]/n for i in range(3))
        good=[tip]*49
        for kwargs in ({"rest_stiffness":60.},
                       {"rest_tip_frames":good[:-1],"rest_stiffness":60.},
                       {"rest_tip_frames":[(0.,0.,0.)]+good[1:],"rest_stiffness":60.},
                       {"rest_tip_frames":[tip]+[(0.,99.,0.)]*48,"rest_stiffness":60.},
                       {"rest_tip_frames":[tip]+[(math.nan,0,0)]*48,"rest_stiffness":60.},
                       {"rest_tip_frames":good,"rest_stiffness":-1.},
                       {"rest_tip_frames":good,"rest_stiffness":math.inf},
                       {"rest_tip_frames":good,"rest_stiffness":False}):
            with self.subTest(kwargs=str(kwargs)[:50]):
                with self.assertRaises(ValueError):simulate(self.g,48,**kwargs)

    def test_fail_closed(self):
        for v in (0,241,1.5):
            with self.assertRaises(ValueError):simulate(self.g,v)
        for wind in ((math.nan,0,0),(30,0,0),(0,)):
            with self.assertRaises(ValueError):simulate(self.g,3,wind)
        with self.assertRaises(ValueError):Guide((0,0,0),(0,0,0),.3)
        with self.assertRaises(ValueError):Guide((0,0,0),(0,0,-1),.01)
        with self.assertRaises(ValueError):simulate(self.g,4,collision_sphere=((0,0,0),-1))
if __name__=="__main__":unittest.main()
