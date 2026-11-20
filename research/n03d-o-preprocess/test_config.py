import unittest
from config import SETTINGS,variant_settings
class VendorSettings(unittest.TestCase):
 def test_factorial(self):self.assertEqual(set(SETTINGS.values()),{(True,True),(False,True),(True,False),(False,False)})
 def test_default(self):self.assertEqual(SETTINGS['auto_normalized'],(True,True))
 def test_no_auto_scale(self):self.assertFalse(variant_settings('fixed_normalized')['useAutoScale'])
 def test_no_normalization(self):self.assertFalse(variant_settings('auto_unmodified')['useNormalizeSource'])
 def test_both_disabled(self):self.assertEqual(SETTINGS['fixed_unmodified'],(False,False))
 def test_unknown_fails(self):
  with self.assertRaisesRegex(ValueError,'BAD_PREPROCESSING_VARIANT'):variant_settings('anything')
if __name__=='__main__':unittest.main()
