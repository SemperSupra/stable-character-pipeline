"""W3 fail-closed independent monitor red controls, no native tool required."""
import math
import struct
import unittest

from prepare_native_w3 import samples, BLOCK, CASE_BLOCKS
from inspect_native_w3 import decode_float_pcm, normalized_error, measure_case, GAIN_LIMIT

def wav(samples_,channels=6):
    raw=struct.pack("<"+"f"*len(samples_),*samples_)
    h=bytearray(44)
    h[:4]=b"RIFF";struct.pack_into("<I",h,4,len(raw)+36)
    h[8:16]=b"WAVEfmt "
    struct.pack_into("<IHHIIHH",h,16,16,3,channels,48000,48000*channels*4,channels*4,32)
    h[36:40]=b"data";struct.pack_into("<I",h,40,len(raw))
    return bytes(h)+raw

class W3Red(unittest.TestCase):
    def test_original_source_prng_determinism(self):
        a=list(samples("impulse_burst",CASE_BLOCKS*BLOCK))
        b=list(samples("impulse_burst",CASE_BLOCKS*BLOCK))
        self.assertEqual(a,b)
        self.assertEqual(a[0],round(.4*32767))
        self.assertEqual(a[BLOCK],0)
        self.assertTrue(any(x!=0 for x in a[1:BLOCK]))
        self.assertTrue(all(x==0 for x in a[BLOCK:]))

    def test_frequency_distinct(self):
        a=list(samples("sine_930",400))
        self.assertEqual(a[0],0)
        self.assertNotEqual(a[50],list(samples("impulse_burst",400))[50])
        self.assertTrue(all(abs(x)<=32767 for x in a))

    def test_header_truncation_channel_swap_and_nonfinite(self):
        good=wav([0.,.1,0,0,0,0])
        self.assertEqual(len(decode_float_pcm(good,6,1)),6)
        for bad in (good[:-1],wav([0.,float("nan"),0,0,0,0]),
                    wav([0.,float("inf"),0,0,0,0]),
                    wav([0.,1.2,0,0,0,0])):
            with self.assertRaises(ValueError):decode_float_pcm(bad,6,1)
        with self.assertRaises(ValueError):decode_float_pcm(good,8,1)
        with self.assertRaises(ValueError):decode_float_pcm(good+b"\x00",6,1)

    def test_gain_order_and_source_frequency_threshold(self):
        a=[.6,0,.8,0,0,0]
        b=[.06,0,.08,0,0,0]
        self.assertLess(normalized_error(b,a),1e-12)
        swapped=[0,.06,.08,0,0,0]
        self.assertGreater(normalized_error(swapped,a),GAIN_LIMIT)
        self.assertEqual(GAIN_LIMIT,.005)

    def test_lfe_red(self):
        bad=[0.]* (CASE_BLOCKS*BLOCK*6)
        bad[3]=.1
        with self.assertRaises(ValueError):measure_case(bad,6,0,[1,0,0,0,0,0],None)
    def test_silent_case_red(self):
        with self.assertRaises(ValueError):
            measure_case([0.]*(CASE_BLOCKS*BLOCK*6),6,0,[1,0,0,0,0,0],None)
    def test_wrong_frame_count_red(self):
        with self.assertRaises(ValueError):
            measure_case([0.]*100,6,0,[1,0,0,0,0,0],930)

if __name__=="__main__":
    unittest.main()
