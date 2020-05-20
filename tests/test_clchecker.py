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


def test_get_abs_position_from_commandline():
    clchecker = CLchecker(store=None)
    # both start_line and start_col start from 1
    commandline = """here is a fake newline
    apt-get install \\
    nodejs\\
    python\\
    ruby && \\
    apt-get clean"""
    commandline = clchecker.pre_process_commandline(commandline)
    abs_start = clchecker.get_abs_position_from_commandline(commandline, line_num=1, col_num=6)
    abs_end = clchecker.get_abs_position_from_commandline(commandline, line_num=1, col_num=7)
    commandline[abs_start:abs_end+1] == 'is'
    abs_start = clchecker.get_abs_position_from_commandline(commandline, line_num=2, col_num=40)
    abs_end = clchecker.get_abs_position_from_commandline(commandline, line_num=2, col_num=43)
    commandline[abs_start:abs_end+1] == 'ytho'

def test_get_abs_position():
    clchecker = CLchecker(store=None)
    # both start_line and start_col start from 1
    commandline = """if [ $1 -gt 100 ]  
then 
apt-get --no-upgrade --only-upgrade install hello=1.2
fi
apt-get install \\
    nodejs\\
    python\\
    ruby && \\
    apt-get clean"""
    commandline = clchecker.pre_process_commandline(commandline)
    abs_start = clchecker.get_abs_position(line_num=1, col_num=6)
    abs_end = clchecker.get_abs_position(line_num=1, col_num=8)
    assert clchecker.convert_pos_to_linecol(abs_start) == (1, 6)
    assert clchecker.convert_pos_to_linecol(abs_end) == (1, 8)
    start = commandline.find("$1")
    assert abs_start == start
    assert abs_end == start + len("$1")

    abs_start = clchecker.get_abs_position(line_num=2, col_num=1)
    abs_end = clchecker.get_abs_position(line_num=2, col_num=5)
    assert clchecker.convert_pos_to_linecol(abs_start) == (2, 1)
    assert clchecker.convert_pos_to_linecol(abs_end) == (2, 5)
    start = commandline.find("then")
    assert abs_start == start
    assert abs_end == start + len("then")

    abs_start = clchecker.get_abs_position(line_num=3, col_num=9)
    abs_end = clchecker.get_abs_position(line_num=3, col_num=21)
    assert clchecker.convert_pos_to_linecol(abs_start) == (3, 9)
    assert clchecker.convert_pos_to_linecol(abs_end) == (3, 21)
    start = commandline.find("--no-upgrade")
    assert abs_start == start
    assert abs_end == start + len("--no-upgrade")

    abs_start = clchecker.get_abs_position(line_num=7, col_num=5)
    abs_end = clchecker.get_abs_position(line_num=7, col_num=11)
    assert clchecker.convert_pos_to_linecol(abs_start) == (7, 5)
    assert clchecker.convert_pos_to_linecol(abs_end) == (7, 11)
    start = commandline.find("python")
    assert abs_start == start
    assert abs_end == start + len("python")

def test_check_apt_get(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    command_name = "apt-get"
    commandline = "apt-get -h"
    clchecker.check(command_name, commandline)
    commandline = "apt-get -y update"
    clchecker.check(command_name, commandline)
    commandline = "apt-get -y \\\ninstall hello=1.2"
    clchecker.check(command_name, commandline)
    commandline = "apt-get install -y"
    clchecker.check(command_name, commandline)
    commandline = "apt-get -y install \\\n hello=1.2\\\n nodejs"
    clchecker.check(command_name, commandline)
    commandline = "apt-get --assume-no install -qq"
    clchecker.check(command_name, commandline, debug=True)

def test_check_rm(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman3_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    command_name = "rm"
    commandline = "rm -rf /bazel"
    clchecker.check(command_name, commandline)

def test_check_groupadd(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman_groupadd,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    command_name = "groupadd"
    commandline = 'groupadd -K GID_MIN=2\tb'
    clchecker.check(command_name, commandline)


def test_check_CLSyntaxError(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    command_name = "apt-get"
    commandline = "apt-get -y install hello=1.2"
    clchecker.check(command_name, commandline)
    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "apt-get install hello= 1.2"
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'all hello=* 1.2'." in e_info.value.message
    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "apt-get autoclean -"
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'utoclean -*'." in e_info.value.message
    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "apt-get install -y \\\n --"
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'll -y    -*-'." in e_info.value.message
    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "apt-get update \\\n"
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'll -y    -*-'." in e_info.value.message


def test_tar(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(
        utils.eman2_full,
        save_to_db=True,
        save_to_file=True,
        save_dir=config.EMANDIR,
        allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=True)
    command_name = "tar"
    # commandline = "tar -cvf tecmint-14-09-12.tar /home/tecmint/"
    # clchecker.check(command_name, commandline, debug=True)

    commandline = 'tar --extract --file "openssl.tar.gz" --directory "/tmp/openssl/"  --strip-components="3"'
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar xvf dockerbins.tgz docker/docker --strip-components 1"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar -xf freemarker.tgz freemarker"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar xf -"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar fx clang+llvm-5.0.0-linux-x86_64-ubuntu14.04.tar.xz"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar -xvf public_html-14-09-12.tar -C /home/public_html/videos/"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar xvf public_html-14-09-12.tar -C /home/public_html/videos/"
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar -xvf public_html-14-09-12.tar"
    clchecker.check(command_name, commandline, debug=True)

    commandline = 'tar -xvf tecmint-14-09-12.tar "file 1" "file 2"'
    clchecker.check(command_name, commandline, debug=True)

    commandline = "tar zxv --no-same-owner -C /opt --exclude='freesurfer/average' --exclude='freesurfer/diffusion'"
    clchecker.check(command_name, commandline, debug=True)


def test_tar_CLSyntaxError(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(
        utils.eman2,
        save_to_db=True,
        save_to_file=True,
        save_dir=config.EMANDIR,
        allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=True)
    command_name = "tar"
    commandline = "tar --create --verbose --file=/dev/rmt0"
    clchecker.check(command_name, commandline, debug=True)
    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "tar --create --verbose --file= /dev/rmt0"
        clchecker.check(command_name, commandline)
    assert "Expected '=(no space before or after)' or '[ \t]+' at the position of the star(*) in => 'ose --file*= /dev/rmt'." in e_info.value.message

    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "tar -cv/home/tecmint/"
        clchecker.check(command_name, commandline)
    assert "at the position of the star(*) in => 'tar -cv*/home/tecm'." in e_info.value.message

    with pytest.raises(errors.CLSyntaxError) as e_info:
        commandline = "tar -cvf"
        clchecker.check(command_name, commandline)
    assert "Expected '=(no space before or after)' or '[ \t]+' at the position of the star(*) in => 'tar -cvf*'." in e_info.value.message

def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get -q=2 install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)


def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get --quiet -q install hello=1.2"
    command_name = "apt-get"
    with pytest.raises(errors.CLSyntaxError) as e_info:
        clchecker.check(command_name, commandline)
    assert "Only one of `-q=<INT> | -q | --quiet=<INT> | --quiet | -qq` can occur, since they have the same meaning" == e_info.value.message


def test_combined_short_option(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get -qqy install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)


def test_combined_short_option_with_value(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get -q=2 install hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)


def test_combined_short_option_with_long_option(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get -qqy install --allow-downgrades hello=1.2"
    command_name = "apt-get"
    clchecker.check(command_name, commandline)


def test_combined_quiet(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    command_name = "apt-get"
    commandline = 'apt-get -qqy upgrade'
    clchecker.check(command_name, commandline)
    commandline = 'apt-get -q -qy upgrade'
    clchecker.check(command_name, commandline)
    commandline = 'apt-get -q=1 -qy upgrade'
    clchecker.check(command_name, commandline)
    commandline = 'apt-get --quiet=1 -qy upgrade'
    clchecker.check(command_name, commandline)

def test_combined_optionsession_multi(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = 'apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade'
    command_name = "apt-get"
    clchecker.check(command_name, commandline)


def test_CLSemanticError_combined_short_option_with_long_option(
    translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get --assume-no install -qqy nodejs"
    command_name = "apt-get"
    with pytest.raises(errors.CLSemanticError) as e_info:
        clchecker.check(command_name, commandline)
    assert "`-y` and `--assume-no` can't occur at the same time" == e_info.value.message


def test_check_CLSemanticError(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get --assume-no install -y hello=1.2"
    command_name = "apt-get"
    with pytest.raises(errors.CLSemanticError) as e_info:
        clchecker.check(command_name, commandline)
    assert "`-y` and `--assume-no` can't occur at the same time" == e_info.value.message


def test_explanation(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman1_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    commandline = "apt-get install -y hello=1.2"
    command_name = "apt-get"
    word = "install"
    found_key, explanation = clchecker.find_explanation(command_name, word)
    assert found_key == word
    assert "install is followed by one or more packages desired for installation or upgrading" in explanation

    word = "q"
    found_key, explanation = clchecker.find_explanation(command_name, word)
    assert "Quiet" in explanation

    word = "--assume-no"
    found_key, explanation = clchecker.find_explanation(command_name, word)
    assert 'Automatic "no"' in explanation

def test_explanation2(translator_clchecker):
    translator, clchecker = translator_clchecker
    translator.translate(utils.eman2_full,
                         save_to_db=True,
                         save_to_file=True,
                         save_dir=config.EMANDIR)
    word = "-f"
    command_name = 'tar'
    found_key, explanation = clchecker.find_explanation(command_name, word)
    assert "Use  archive  file  or device ARCHIVE." in explanation