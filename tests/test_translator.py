from clchecker.store import Store, Command
from clchecker.translate import Translator
import config as config
from textx import metamodel_from_file
import pytest, os
from tests import utils


@pytest.fixture
def translator():
    metamodel = metamodel_from_file(config.EMAN)
    translator = Translator(metamodel)
    return translator


def is_diff(str1, str2):
    for i in range(max(len(str1), len(str2))):
        if i >= len(str2) or i >= len(str1) or str1[i] != str2[i]:
            return i


# def test_preprocess(translator):
#     translator.reset()
#     eman = translator.pre_process(utils.eman1)
#     diff = is_diff(eman, utils.after_pre_processed)
#     # assert not diff
#     with open(os.path.join(utils.test_eman1_dir, 'after_pre_processed.eman'), 'w') as f:
#         f.write(eman)


def test_translate1(translator):
    eman1_translated = translator.translate(utils.eman1,
                                            save_to_file=True,
                                            save_dir=config.EMANDIR)
    diff = is_diff(eman1_translated, utils.after_translated)
    # assert not diff
    with open(os.path.join(utils.test_eman1_dir, 'after_translated.txt'),
              'w') as f:
        f.write(eman1_translated)


def test_translate2(translator):
    eman2_translated = translator.translate(
        utils.eman2,
        save_to_file=True,
        save_dir=config.EMANDIR,
        allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=True)
    diff = is_diff(eman2_translated, utils.after_translated)
    # assert not diff
    with open(os.path.join(utils.test_eman2_dir, 'after_translated.txt'),
              'w') as f:
        f.write(eman2_translated)