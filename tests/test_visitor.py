import os
from web.server.utils import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store, Command
from clchecker.checker import CLchecker
from clchecker.translate import Translator
from textx import metamodel_from_file
import tests.utils as utils
import clchecker.config as config
import pytest

@pytest.fixture
def visitor_setup():
    store = Store(db='clchecker_test_visitor')
    store.delete_all_documents(confirm=True)
    synopsis_metamodel = metamodel_from_file(config.SYNOPSIS)
    translator = Translator(synopsis_metamodel, store=store)
    clchecker = CLchecker(store)
    visitor = Visitor(clchecker)
    yield visitor, translator
    store.drop_collection(confirm=True)

def test_synop1_always(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.APT_GET_SYNOP1, save_to_db=True,
                    save_to_file=True, save_dir=config.SYNOPDIR)
    code = "apt-get install nodejs"
    markers = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 1
    assert markers[0]['startColumn'] == 9
    assert markers[0]['endLineNumber'] == 1
    assert markers[0]['endColumn'] == 16
    assert markers[0]['message'] == 'Expect `-y` when `install` occurs'
    assert markers[0]['severity'] == 'Error'

def test_synop2_mutex(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.APT_GET_SYNOP2, save_to_db=True,
                    save_to_file=True, save_dir=config.SYNOPDIR)
    code = "apt-get --no-upgrade --only-upgrade install hello=1.0.1"
    markers = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 1
    assert markers[0]['startColumn'] == 9
    assert markers[0]['endLineNumber'] == 1
    assert markers[0]['endColumn'] == 21
    assert markers[0]['message'] == "`--only-upgrade` and `--no-upgrade` can't occur at the same time"
    assert markers[0]['severity'] == 'Error'


def test_synop2_if(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.APT_GET_SYNOP2, save_to_db=True,
                    save_to_file=True, save_dir=config.SYNOPDIR)
    code = """if [ 3 -gt 2 ]; 
then 
    apt-get --no-upgrade --only-upgrade install hello=1.0.1;
fi;"""
    markers = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 3
    assert markers[0]['startColumn'] == 13
    assert markers[0]['endLineNumber'] == 3
    assert markers[0]['endColumn'] == 25
    assert markers[0]['message'] == "`--only-upgrade` and `--no-upgrade` can't occur at the same time"
    assert markers[0]['severity'] == 'Error'


def test_synop2_textxparsing_error2(visitor_setup):
    visitor, translator  = visitor_setup
    translator.translate(utils.APT_GET_SYNOP2, save_to_db=True,
                    save_to_file=True, save_dir=config.SYNOPDIR)
    code = """if [ 3 -gt 2 ]
then 
    apt-get -y install
fi;"""
    markers = visitor.start(code)
    assert len(markers) == 1
    assert markers[0]['startLineNumber'] == 3
    assert markers[0]['startColumn'] == 23
    assert markers[0]['endLineNumber'] == None
    assert markers[0]['endColumn'] == None
    assert markers[0]['message'] == "Expected '<PKG>' at the position of the star(*) in => '-y install*'."
    assert markers[0]['severity'] == 'Error'
