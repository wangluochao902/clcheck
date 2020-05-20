import config
import os


test_eman1_dir = os.path.join(config.ROOTDIR, 'tests/test_eman1')
eman_dir = os.path.join(config.ROOTDIR, 'eman')
with open(os.path.join(test_eman1_dir, 'eman1.eman'), 'r') as f:
	eman1 = f.read()
with open(os.path.join(eman_dir, 'apt-get.eman'), 'r') as f:
	eman1_full = f.read()

with open(os.path.join(test_eman1_dir, 'after_translated.txt'), 'r') as f:
	after_translated = f.read()

test_eman2_dir = os.path.join(config.ROOTDIR, 'tests/test_eman2')
with open(os.path.join(test_eman2_dir, 'eman2.eman'), 'r') as f:
	eman2 = f.read()
with open(os.path.join(eman_dir, 'tar.eman'), 'r') as f:
	eman2_full = f.read()

with open(os.path.join(test_eman2_dir, 'after_translated.txt'), 'r') as f:
	after_translated = f.read()


with open(os.path.join(eman_dir, 'rm.eman'), 'r') as f:
	eman3_full = f.read()


with open(os.path.join(eman_dir, 'groupadd.eman'), 'r') as f:
	eman_groupadd = f.read()
