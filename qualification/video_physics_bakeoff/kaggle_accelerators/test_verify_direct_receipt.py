import copy
import math
import unittest
from videoqa_kaggle_probe import run
from verify_direct_receipt import verify

CODE = 'a' * 64

def exemplar(backend):
    receipt = copy.deepcopy(run('cpu'))
    receipt.update(requested_backend=backend,
                   actual_backend={'cpu':'cpu','gpu':'cuda','tpu':'tpu'}[backend],
                   executed_source_sha256=CODE)
    if backend == 'gpu':
        receipt['device'] = {'backend':'cuda', 'device_count':2,
                             'device_models':['Tesla T4','Tesla T4'],
                             'separate_device_computation':True}
    if backend == 'tpu':
        receipt['device'] = {'backend':'tpu', 'device_count':8,
                             'device_models':['TPU v5e'] * 8,
                             'separate_device_computation':True}
    return receipt

class IndependentDirectReceiptTest(unittest.TestCase):
    def test_cpu_scientific_receipt(self):
        self.assertEqual(verify(exemplar('cpu'), 'cpu', CODE)['measurements_checked'],8)

    def test_gpu_scientific_shape_without_claiming_provider(self):
        r=verify(exemplar('gpu'),'gpu',CODE)
        self.assertEqual(r['provider_status'],'NOT_VERIFIED_BY_THIS_TOOL')

    def test_tpu_scientific_shape_without_claiming_provider(self):
        self.assertEqual(verify(exemplar('tpu'),'tpu',CODE)['backend'],'tpu')

    def test_mismatched_code_sha(self):
        with self.assertRaisesRegex(ValueError,'SOURCE'):
            verify(exemplar('gpu'), 'gpu', 'b'*64)

    def test_mismatched_fixture_sha(self):
        x=exemplar('gpu');x['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE'):
            verify(x, 'gpu', CODE)

    def test_cpu_disguised_as_gpu(self):
        x=exemplar('cpu')
        with self.assertRaisesRegex(ValueError,'SOURCE'):
            verify(x, 'gpu', CODE)

    def test_missing_second_gpu(self):
        x=exemplar('gpu');x['device']['device_count']=1
        with self.assertRaisesRegex(ValueError,'DEVICE_COUNT'):
            verify(x,'gpu',CODE)

    def test_incompatible_tpu_model(self):
        x=exemplar('tpu');x['device']['device_models']=['CPU']*8
        with self.assertRaisesRegex(ValueError,'TPU_MODEL'):
            verify(x,'tpu',CODE)

    def test_shortened_score_vector(self):
        x=exemplar('gpu');x['metric_scores'].pop()
        with self.assertRaisesRegex(ValueError,'MEASUREMENT'):
            verify(x,'gpu',CODE)

    def test_nonfinite_or_boolean_scores(self):
        for bad in (math.nan,math.inf,-math.inf,True):
            x=exemplar('gpu');x['metric_scores'][5]=bad
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'NUMERIC'):
                verify(x,'gpu',CODE)

    def test_forged_scientific_status(self):
        x=exemplar('gpu');x['status']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'UNTRUSTED'):
            verify(x,'gpu',CODE)

    def test_claims_no_provider_proof(self):
        x=exemplar('tpu')
        self.assertEqual(verify(x,'tpu',CODE)['provider_status'],
                         'NOT_VERIFIED_BY_THIS_TOOL')

if __name__ == '__main__':
    unittest.main()
