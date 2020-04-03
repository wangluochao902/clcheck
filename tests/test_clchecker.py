from clchecker.checker import CLchecker
from clchecker.store import Store, Command
from clchecker.translate import Translator
import clchecker.config as config
import clchecker.errors as errors
from textx import metamodel_from_file
import unittest
import os
import tests.utils as utils


class Test_CLchecker(unittest.TestCase):
    def setUp(self):
        self.store = Store(db='clchecker_test3')
        synopsis_metamodel = metamodel_from_file(config.SYNOPSIS)
        self.translator = Translator(synopsis_metamodel, store=self.store)
        self.clchecker = CLchecker(self.store)

    def tearDown(self):
        self.store.drop_collection(confirm=True)

    def test_get_abs_position(self):
        # both start_line and start_col start from 1
        commandline = """if [ $1 -gt 100 ]  
then 
apt-get --no-upgrade --only-upgrade install hello=1.2
fi"""
        abs_start = self.clchecker.get_abs_position(
            commandline, line_num=1, col_num=6)
        abs_end = self.clchecker.get_abs_position(
            commandline,
            line_num=1, col_num=7)
        start = commandline.find("$1") + 1
        self.assertEqual(abs_start, start)
        self.assertEqual(abs_end, start+len("$1")-1)

        abs_start = self.clchecker.get_abs_position(
            commandline, line_num=2, col_num=1)
        abs_end = self.clchecker.get_abs_position(
            commandline, line_num=2, col_num=4)
        start = commandline.find("then") + 1
        self.assertEqual(abs_start, start)
        self.assertEqual(abs_end, start+len("then")-1)

        abs_start = self.clchecker.get_abs_position(
            commandline, line_num=3, col_num=9)
        abs_end = self.clchecker.get_abs_position(
            commandline, line_num=3, col_num=20)
        start = commandline.find("--no-upgrade") + 1
        self.assertEqual(abs_start, start)
        self.assertEqual(abs_end, start+len("--no-upgrade")-1)

    def test_check_semantics1(self):
        self.store.delete_all_documents(confirm=True)
        self.translator.translate(utils.APT_GET_SYNOP1, save_to_db=True,
                                  save_to_file=True, save_dir=config.SYNOPDIR)
        commandline = "apt-get  install  hello=1.2"
        command_name = "apt-get"
        with self.assertRaises(errors.CLSemanticError) as cm:
            self.clchecker.check_semantics(command_name, commandline)
        exception = cm.exception
        self.assertTrue('Expect -y when `install` occurs' == exception.message)

        commandline = "apt-get -y install hello=1.2"
        self.clchecker.check_semantics(command_name, commandline)

    def test_check_semantics2(self):
        self.store.delete_all_documents(confirm=True)
        self.translator.translate(utils.APT_GET_SYNOP2, save_to_db=True,
                                  save_to_file=True, save_dir=config.SYNOPDIR)
        commandline = "apt-get --no-upgrade --only-upgrade install hello=1.2"
        command_name = "apt-get"
        with self.assertRaises(errors.CLSemanticError) as cm:
            self.clchecker.check_semantics(command_name, commandline)
        exception = cm.exception
        self.assertTrue(
            "`--only-upgrade` and `--no-upgrade` can't occur at the same time" == exception.message)

        commandline = "apt-get -y install hello=1.2"
        self.clchecker.check_semantics(command_name, commandline)

#         commandline = """
# if [ $1 -gt 100 ]
# then
# apt-get --no-upgrade --only-upgrade install hello=1.2
# fi
# """
#         self.clchecker.check_semantics(command_name, commandline)

        # todo: option after subcommand
        # commandline = "apt-get install hello=1.2"
        # self.clchecker.check_semantics(command_name, commandline)
