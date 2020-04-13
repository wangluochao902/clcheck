from clchecker.store import Store, Command
from clchecker.translate import Translator
import config as config
from textx import metamodel_from_file
import pytest, os
import tests.utils as utils

@pytest.fixture
def translator():
    metamodel = metamodel_from_file(config.EMAN)
    translator = Translator(metamodel)
    return translator

def is_diff(str1, str2):
    for i in range(max(len(str1), len(str2))):
        if i >= len(str2) or i>=len(str1) or str1[i] != str2[i]:
            return i

def test_preprocess(translator):
    translator.reset()
    eman = translator.preprocess(utils.eman1)
    diff = is_diff(eman, utils.eman1_preprocessed)
    assert not diff

def test_translate(translator):
    eman1_translated = translator.translate(utils.eman1, save_to_file=True, save_dir=config.EMANDIR)
    diff = is_diff(eman1_translated, utils.eman1_translated)
    assert not diff