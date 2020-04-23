import os
from clchecker.visitor import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store, Command
from clchecker.checker import CLchecker
from clchecker.translate import Translator
from textx import metamodel_from_file
import tests.utils as utils
import config as config
import pytest

@pytest.fixture
def visitor_setup():
    store = Store(db='clchecker_test_visitor')
    store.delete_all_documents(confirm=True)
    metamodel = metamodel_from_file(config.EMAN)
    translator = Translator(metamodel, store=store)
    clchecker = CLchecker(store)
    visitor = Visitor(clchecker)
    yield visitor, translator
    store.drop_collection(confirm=True)

def test_synop1_mutex1(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.eman1, save_to_db=True,
                    save_to_file=True, save_dir=config.EMANDIR)
    code = "apt-get --assume-no install -y nodejs"
    markers, command_range = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 1
    assert markers[0]['startColumn'] == 9
    assert markers[0]['endLineNumber'] == 1
    assert markers[0]['endColumn'] == 20
    assert markers[0]['message'] == "`-y` and `--assume-no` can't occur at the same time"
    assert markers[0]['severity'] == 'Error'

    assert 'apt-get' in command_range
    assert command_range['apt-get']["startLine"] == 1
    assert command_range['apt-get']["endLine"] == 1
    assert command_range['apt-get']["startColumn"] == 1
    assert command_range['apt-get']["endColumn"] == 37


def test_synop2_if(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.eman1, save_to_db=True,
                    save_to_file=True, save_dir=config.EMANDIR)
    code = """if [ 3 -gt 2 ]; 
then 
    apt-get --assume-no install -y nodejs;
fi;"""
    markers, command_range = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 3
    assert markers[0]['startColumn'] == 13
    assert markers[0]['endLineNumber'] == 3
    assert markers[0]['endColumn'] == 24
    assert markers[0]['message'] == "`-y` and `--assume-no` can't occur at the same time"
    assert markers[0]['severity'] == 'Error'

    assert 'apt-get' in command_range
    assert command_range['apt-get']["startLine"] == 3
    assert command_range['apt-get']["endLine"] == 3
    assert command_range['apt-get']["startColumn"] == 5
    assert command_range['apt-get']["endColumn"] == 42


def test_textxparsing_error(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.eman1, save_to_db=True,
                    save_to_file=True, save_dir=config.EMANDIR)
    code = """if [ 3 -gt 2 ]
then 
    apt-get -y install
fi;"""
    markers, command_range = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 3
    assert markers[0]['startColumn'] == 23
    assert markers[0]['endLineNumber'] == None
    assert markers[0]['endColumn'] == None
    message = markers[0]['message'] 
    assert "Expected" in message and "PKG" in message and "at the position of the star(*) in => '-y install*'." in message
    assert "'--quiet'" in message
    assert "'--just-print'" in message
    assert "'--simulate'" in message
    assert markers[0]['severity'] == 'Error'


def test_redirect(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.eman1, save_to_db=True,
                    save_to_file=True, save_dir=config.EMANDIR)
    code = "apt-get -yqq update > /dev/null"""
    markers, command_range = visitor.start(code)