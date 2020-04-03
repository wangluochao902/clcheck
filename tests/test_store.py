import unittest

from clchecker.store import Store, Command

TX_SYNTAX = '''
Main_Rule:
	command="apt-get" statement=UnorderedStatement_0
;

LongOption_0:
	option_key="--no-install-recommends"
;

SequentialStatement_0:
	element0=LongOption_0?
;

OptionalCollection_0:
	statement0=SequentialStatement_0
;

LongOption_1:
	option_key="--install-suggests"
;
'''


class Test_Store(unittest.TestCase):
    def setUp(self):
        self.store = Store(db='clchecker_test_store')
        self.store.delete_all_documents(confirm=True)

    def tearDown(self):
        self.store.drop_collection(confirm=True)

    def test_addcommand_findcommand(self):
        command_name = 'apt-get'
        tx_syntax = TX_SYNTAX
        concrete_specs= {
                'LongOption1': {
                    'after':  {'word2s': ['OptionalCollection_0'],
                               'one_must_present': ['LongOption_1', 'LongOption_0']},
                }
            }
        synop = 'hello'
        clsname_to_readabel_syntax = {}
        command = Command(command_name, tx_syntax, clsname_to_readabel_syntax, concrete_specs, synop)
        self.store.addcommand(command)

        command2 = self.store.findcommand(command_name)
        self.assertEqual(tx_syntax, command2.tx_syntax)
        self.assertEqual(command_name, command2.command_name)
        self.assertEqual(concrete_specs, command2.concrete_specs)
        self.assertEqual(synop, command2.synop)
