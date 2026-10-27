import hashlib
import unittest
import numpy as np
from synthetic import build,JOINTS,FOOT_JOINTS
from train import create_windows,train

class Synthetic(unittest.TestCase):
    def test_reproducible_both_domains(self):
        for d in JOINTS:
            a,m=build(d,16,12)
            b,n=build(d,16,12)
            self.assertTrue(np.array_equal(a,b));self.assertEqual(m['data_float32_sha256'],n['data_float32_sha256'])
            self.assertEqual(a.dtype,np.float32)
            self.assertTrue(np.isfinite(a).all())
            self.assertEqual(a.shape,(16,12,len(JOINTS[d]),3))
            self.assertEqual(m['observed'],False)
            self.assertEqual(hashlib.sha256(a.tobytes()).hexdigest(),m['data_float32_sha256'])
    def test_separate_holdout(self):
        for d in JOINTS:
            a,_=build(d,128,48)
            x,y=create_windows(a[:96]);vx,vy=create_windows(a[96:])
            self.assertEqual(len(x),96*44);self.assertEqual(len(vx),32*44)
            self.assertEqual(x.shape[-1],len(JOINTS[d])*3)
    def test_missing_spec_fails(self):
        with self.assertRaises(ValueError):build('notanimal')
        with self.assertRaises(ValueError):build('fauna',4,6)
    def test_cpu_learning(self):
        for d in JOINTS:
            result,params,_,_,_,generated=train(d,backend='cpu',steps=50,batch_per_device=16)
            self.assertLess(result['heldout_residual_mse'],result['persistence_baseline_mse'])
            self.assertLess(result['heldout_residual_mse'],result['shuffled_control_mse'])
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(generated.shape,(24,len(JOINTS[d]),3))
            self.assertTrue(np.isfinite(generated).all())

if __name__=='__main__':unittest.main()
