import pytest

from clchecker.store import Store, Command

TX_SYNTAX = '''
Main_Rule:
	command="apt-get" statement=UnorderedStatement_0
;

ShortOption_0:
	option_key="-q"
;
'''


@pytest.fixture
def store():
    store = Store(db='test_store')
    yield store
    store.drop_collection(confirm=True)


def test_addcommand_findcommand(store):
    command_name = 'apt-get'

    tx_syntax = TX_SYNTAX
    concrete_specs = {
        "after": ['hello']
    }
    eman = 'hello'
    clsname_to_readabel_syntax = {}
    explanation = {}
    command = Command(command_name, tx_syntax,
                      clsname_to_readabel_syntax, concrete_specs, explanation, eman)
    store.addcommand(command)

    command2 = store.findcommand(command_name)
    assert tx_syntax == command2.tx_syntax
    assert command_name == command2.command_name
    assert concrete_specs == command2.concrete_specs
    assert eman == command2.eman
