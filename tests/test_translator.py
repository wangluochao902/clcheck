from clchecker.store import Store, Command
from clchecker.translate import Translator
import clchecker.config as config
from textx import metamodel_from_file
import unittest, os
import tests.utils as utils


class Test_Translator(unittest.TestCase):
    def setUp(self):
        synopsis_metamodel = metamodel_from_file(config.SYNOPSIS)
        self.translator = Translator(synopsis_metamodel)
        
    def test_translate1(self):
        self.translator.translate(utils.APT_GET_SYNOP1, save_to_file=True, save_dir=config.SYNOPDIR)
        print(self.translator.spec)

    def test_translate2(self):
        self.translator.translate(utils.APT_GET_SYNOP2, save_to_file=True, save_dir=config.SYNOPDIR)
        print(self.translator.spec)
