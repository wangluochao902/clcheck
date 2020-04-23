import config
import os


test_eman1_dir = os.path.join(config.ROOTDIR, 'tests/test_eman1')
with open(os.path.join(test_eman1_dir, 'eman1.eman'), 'r') as f:
	eman1 = f.read()

with open(os.path.join(test_eman1_dir, 'after_pre_processed.eman'), 'r') as f:
	after_pre_processed = f.read()

with open(os.path.join(test_eman1_dir, 'after_translated.txt'), 'r') as f:
	after_translated = f.read()