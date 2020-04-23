from clchecker.checker import CLchecker
from clchecker.store import Store, Command
from clchecker.translate import Translator
import config
import clchecker.errors as errors
from textx import metamodel_from_file
import pytest
import os
import tests.utils as utils

@pytest.fixture
def translator_clchecker():
    store = Store(db='test_clchecker')
    metamodel = metamodel_from_file(config.EMAN)
    translator = Translator(metamodel, store=store)
    clchecker = CLchecker(store) 
    yield translator, clchecker
    store.drop_collection(confirm=True)


def test_get_abs_position():
    clchecker = CLchecker(store=None)
    # both start_line and start_col start from 1
    commandline = """if [ $1 -gt 100 ]  
then 
apt-get --no-upgrade --only-upgrade install hello=1.2
fi"""
    abs_start = clchecker.get_abs_position(
        commandline, line_num=1, col_num=6)
    abs_end = clchecker.get_abs_position(
        commandline,
        line_num=1, col_num=7)
    start = commandline.find("$1") + 1
    assert abs_start == start
    assert abs_end == start+len("$1")-1

    abs_start = clchecker.get_abs_position(
        commandline, line_num=2, col_num=1)
    abs_end = clchecker.get_abs_position(
        commandline, line_num=2, col_num=4)
    start = commandline.find("then") + 1
    assert abs_start == start
    assert abs_end == start+len("then")-1

    abs_start = clchecker.get_abs_position(
        commandline, line_num=3, col_num=9)
    abs_end = clchecker.get_abs_position(
        commandline, line_num=3, col_num=20)
    start = commandline.find("--no-upgrade") + 1
    assert abs_start == start
    assert abs_end == start+len("--no-upgrade")-1

def test_check_CLSyntaxError(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get install hello= 1.2"
    command_name = "apt-get"
    with pytest.raises(errors.CLSyntaxError) as e_info:
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'all hello=* 1.2'." in e_info.value.message

    commandline = "apt-get -y install hello=1.2"
    clchecker.check(command_name, commandline)

def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get -q=2 install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)

def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get --quiet -qq install hello=1.2"
    command_name = "apt-get"
    with pytest.raises(errors.CLSyntaxError) as e_info:
        clchecker.check(command_name, commandline)
    assert "Only one of `-q=<INT> | -q | --quiet=<INT> | --quiet | -qq` can occur, since they have the same meaning" == e_info.value.message

def test_combined_short_option(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get -qqy install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)

def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get -q=2 install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)

def test_combined_short_option_with_long_option(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get -qqy install --allow-downgrades hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)

def test_combined_optionsession_multi(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = 'apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade'
    command_name = "apt-get"
    clchecker.check(command_name, commandline)

def test_CLSemanticError_combined_short_option_with_long_option(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get --assume-no install -qqy nodejs"
    command_name = "apt-get"
    with pytest.raises(errors.CLSemanticError) as e_info:
        clchecker.check(command_name, commandline)
    assert "`-y` and `--assume-no` can't occur at the same time" == e_info.value.message

def test_check_CLSemanticError(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get --assume-no install -y hello=1.2"
    command_name = "apt-get"
    with pytest.raises(errors.CLSemanticError) as e_info:
        clchecker.check(command_name, commandline)
    assert "`-y` and `--assume-no` can't occur at the same time" == e_info.value.message

def test_explanation(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1, save_to_db=True,
                                save_to_file=True, save_dir=config.EMANDIR)
    commandline = "apt-get install -y hello=1.2"
    command_name = "apt-get"
    key = "install"
    explanation = clchecker.find_explanation(command_name, key)
    assert "install is followed by one or more packages desired for installation or upgrading" in explanation