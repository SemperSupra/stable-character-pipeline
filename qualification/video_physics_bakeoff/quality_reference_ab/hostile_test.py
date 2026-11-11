#!/usr/bin/env python3
"""Adversarial source-bound PSNR/SSIM receipt and timestamp evidence checks."""
import pathlib
import shutil
import subprocess
import sys
import tempfile

root = pathlib.Path(sys.argv[1]).resolve()
script = pathlib.Path(__file__).with_name('score.py')
for name, filename, mutate in [
    ('drop-frame', 'candidate.ssim', lambda x: '\n'.join(x.splitlines()[:-1])+'\n'),
    ('duplicate-frame', 'baseline.psnr', lambda x: x+x.splitlines()[-1]+'\n'),
    ('nan-metric', 'candidate.psnr', lambda x: x.replace('psnr_avg:', 'psnr_avg:nan#', 1)),
]:
    with tempfile.TemporaryDirectory() as td:
        target = pathlib.Path(td)
        for path in root.iterdir():
            if path.is_file(): shutil.copyfile(path, target/path.name)
        artifact = target/filename
        artifact.write_text(mutate(artifact.read_text()))
        result = subprocess.run([sys.executable, str(script), str(target)], text=True, capture_output=True)
        if result.returncode == 0:
            raise AssertionError(f'{name} incorrectly produced successful receipt')
        print(f'{name}: expected rejection')
