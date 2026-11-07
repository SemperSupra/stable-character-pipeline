"""Source-free profile input tests (stdlib, safe on public runners)."""
import unittest
from skirt_yoke_profile_contract_v1 import validate,ProfileError,SOURCE_SHA256
class ProfileTests(unittest.TestCase):
    def test_valid_profile(self):
        self.assertTrue(validate('JuniperOriginal',.35,.8))
    def test_wrong_actor(self):
        with self.assertRaises(ProfileError):validate('Nonexistent',.35,.8)
    def test_invalid_strength(self):
        for x in (float('nan'),float('inf'),True,-.01,.96):
            with self.subTest(x=x),self.assertRaises(ProfileError):validate('JuniperOriginal',x,.8)
    def test_invalid_hip_share(self):
        for x in (float('nan'),float('inf'),False,-.01,.81):
            with self.subTest(x=x),self.assertRaises(ProfileError):validate('JuniperOriginal',.35,x)
    def test_pinned_source(self):
        self.assertEqual(SOURCE_SHA256,'ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af')
if __name__=='__main__':unittest.main()
