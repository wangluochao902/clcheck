eman1 = """
e-synopsis:
    apt-get (<options>
    {
        install <options> <pkg-with-optional-version> |
        remove <options> <PKG>+  
    })#
e-end

e-options:
    -q: [-q | -q=<INT> | --quiet | --quiet=<INT> | -qq](mutex:[--print-urls, -s])
    -s: [-s | --simulate | --just-print | --just-run | --recon | --no-act]
    -y: [-y | --yes | --assume-yes]
    --assume-no: (mutex:[-y])
    --allow-downgrades: (warning:m1)
    --print-urls
    --reinstall
e-end

e-variables:
    pkg-with-optional-version = {<PKG> [= <VERSION>]}(noskipws)
    m1 = "dangerous option"
e-end

e-explanation:
    install
        install is followed by one or more packages desired for installation or upgrading. Each package is a package name, not a fully qualified

        A specific version of a package can be selected for installation by following the package name with an equals and the version of the

    remove
        remove is identical to install except that packages are removed instead of installed. Note that removing a package leaves its configuration
        files on the system. If a plus sign is appended to the package name (with no intervening space), the identified package will be installed
        instead of removed.
e-end"""


eman1_preprocessed = """
e-synopsis:
    apt-get (<options>
    {
        install <options> {<PKG> [= <VERSION>]}(noskipws) |
        remove <options> <PKG>+  
    })#
e-end

e-options:
	-q:[-q | -q=<INT> | --quiet | --quiet=<INT> | -qq](mutex:[--print-urls, -s])
	-s:[-s | --simulate | --just-print | --just-run | --recon | --no-act]
	-y:[-y | --yes | --assume-yes]
	--assume-no:[--assume-no](mutex:[-y])
	--allow-downgrades:[--allow-downgrades](warning:m1)
	--print-urls:[--print-urls]
	--reinstall:[--reinstall]
e-end

e-explanation:
    install
        install is followed by one or more packages desired for installation or upgrading. Each package is a package name, not a fully qualified

        A specific version of a package can be selected for installation by following the package name with an equals and the version of the

    remove
        remove is identical to install except that packages are removed instead of installed. Note that removing a package leaves its configuration
        files on the system. If a plus sign is appended to the package name (with no intervening space), the identified package will be installed
        instead of removed.
e-end"""

eman1_translated = """// DSL for command "apt-get"

Main_Rule:
	command="apt-get" statement=UnorderedStatement_0
;

ShortOption_0:
	option_key="-q"
;

SequentialStatement_0:
	element0=ShortOption_0
;

ShortOption_1:
	option_key="-q" ("=")? value=INT
;

SequentialStatement_1:
	element0=ShortOption_1
;

LongOption_0:
	option_key="--quiet"
;

SequentialStatement_2:
	element0=LongOption_0
;

LongOption_1:
	option_key="--quiet" ("=")? value=INT
;

SequentialStatement_3:
	element0=LongOption_1
;

ShortOption_2:
	option_key="-qq"
;

SequentialStatement_4:
	element0=ShortOption_2
;

OptionalCollection_0:
	statement0=SequentialStatement_0 | statement1=SequentialStatement_1 | statement2=SequentialStatement_2 | statement3=SequentialStatement_3 | statement4=SequentialStatement_4
;

ShortOption_3:
	option_key="-s"
;

SequentialStatement_5:
	element0=ShortOption_3
;

LongOption_2:
	option_key="--simulate"
;

SequentialStatement_6:
	element0=LongOption_2
;

LongOption_3:
	option_key="--just-print"
;

SequentialStatement_7:
	element0=LongOption_3
;

LongOption_4:
	option_key="--just-run"
;

SequentialStatement_8:
	element0=LongOption_4
;

LongOption_5:
	option_key="--recon"
;

SequentialStatement_9:
	element0=LongOption_5
;

LongOption_6:
	option_key="--no-act"
;

SequentialStatement_10:
	element0=LongOption_6
;

OptionalCollection_1:
	statement0=SequentialStatement_5 | statement1=SequentialStatement_6 | statement2=SequentialStatement_7 | statement3=SequentialStatement_8 | statement4=SequentialStatement_9 | statement5=SequentialStatement_10
;

ShortOption_4:
	option_key="-y"
;

SequentialStatement_11:
	element0=ShortOption_4
;

LongOption_7:
	option_key="--yes"
;

SequentialStatement_12:
	element0=LongOption_7
;

LongOption_8:
	option_key="--assume-yes"
;

SequentialStatement_13:
	element0=LongOption_8
;

OptionalCollection_2:
	statement0=SequentialStatement_11 | statement1=SequentialStatement_12 | statement2=SequentialStatement_13
;

LongOption_9:
	option_key="--assume-no"
;

SequentialStatement_14:
	element0=LongOption_9
;

OptionalCollection_3:
	statement0=SequentialStatement_14
;

LongOption_10:
	option_key="--allow-downgrades"
;

SequentialStatement_15:
	element0=LongOption_10
;

OptionalCollection_4:
	statement0=SequentialStatement_15
;

LongOption_11:
	option_key="--print-urls"
;

SequentialStatement_16:
	element0=LongOption_11
;

OptionalCollection_5:
	statement0=SequentialStatement_16
;

LongOption_12:
	option_key="--reinstall"
;

SequentialStatement_17:
	element0=LongOption_12
;

OptionalCollection_6:
	statement0=SequentialStatement_17
;

OptionSession:
	(OptionalCollection_0? | OptionalCollection_1? | OptionalCollection_2? | OptionalCollection_3? | OptionalCollection_4? | OptionalCollection_5? | OptionalCollection_6?)#
;

SubCommand_0:
	value="install"
;

SequentialStatement_20:
	element0="=" element1=VERSION
;

OptionalCollection_7:
	statement0=SequentialStatement_20
;

SequentialStatement_19:
	element0=PKG element1=OptionalCollection_7?
;

OneMustPresentCollection_1[noskipws]:
	/\s*/- statement0=SequentialStatement_19 /\s*/-
;

SequentialStatement_18:
	element0=SubCommand_0 element1=OptionSession? element2=OneMustPresentCollection_1
;

SubCommand_1:
	value="remove"
;

PKG_Multi:
	types+=PKG
;

SequentialStatement_21:
	element0=SubCommand_1 element1=OptionSession? element2=PKG_Multi
;

OneMustPresentCollection_0:
	statement0=SequentialStatement_18 | statement1=SequentialStatement_21
;

UnorderedStatement_0:
	(element0=OptionSession? element1=OneMustPresentCollection_0)#
;

// base type for the DSL
VERSION:
    content=/[\S]+/
;

NOTWHITESPACE:
    content=/[\S]+/
;

PATH:
    content=/(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\-\.]+/
;

DIR:
    content=/(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\.\-]+(?:\/)?/
;

PKG:
//    content=/[\w\*][:\w\.\-\*\+]*/
    content=/[\S]+/
;
"""