APT_GET_SYNOP1 = """
apt-get
([-q | -q=<INT>](warning:m1)
[-y](tag:-y)
{install(always:[tag:-y]) {<PKG> [={<VERSION> | <RELEASE>}]}(noskipws)+})#

message m1 = "hello"
"""

APT_GET_SYNOP2 = """
apt-get
([--no-install-recommends]
[--install-suggests]
[-d | --download-only](tag:d)
[-f | --fix-broken](tag:f)
[-m | --ignore-missing | --fix-missing](tag:m)
[--no-download](mutex:[tag:d])
[-q | -q=<INT> | --quiet | --quiet=<INT> | -qq](mutex:{tag:d | tag:--print-urls | tag:s | tag:--show-progress})
[-s | --simulate | --just-print | --just-run | --recon | --no-act](tag:s)
[-y | --yes | --assume-yes](tag:-y)
[--assume-no](mutex:[tag:-y])
[--no-show-upgraded]
[-V | --verbose-VERSION]
[-a=<STRING> | --host-architecture=<STRING>](always:[tag:b, source])
[-P | --build-profiles](always:[tag:b], after:[source])
[-b | --compile | --build](tag:b)
[--ignore-hold](always:[dist-upgrade])
[--with-new-PKGs](always:[upgrade])
[--no-upgrade](mutex:[tag:--only-upgrade])
[--only-upgrade](tag:--only-upgrade)
[--allow-downgrades](warning:m1)
[--allow-remove-essential](warning:"dangerous option")
[--allow-change-held-packages](warning:"dangerous option")
[--force-yes](warning:"dangerous option")
[--print-urls](tag:--print-urls)
[--purge](after:[remove])
[--reinstall]
[--list-cleanup | --no-list-cleanup]
[-t=<RELEASE> | --target-RELEASE=<RELEASE> | --default-RELEASE=<RELEASE>]
[--trivial-only](mutex:[tag:-y])
[--no-remove | --auto-remove | autoremove](always:{install | remove})
[--only-source]
[--diff-only | --dsc-only | tar-only]
[--arch-only]
[--indep-only]
[--allow-unauthenticated]
[--no-allow-insecure-repositories]
[--allow-RELEASEinfo-change]
[--show-progess](tag:--show-progress)
[--with-source=<PATH>+]
[-c=<PATH> | --config-file=<PATH>]
[-o=<STRING> | --option=<STRING>]
{update | upgrade | dselect-upgrade | dist-upgrade | install {<PKG> [={<VERSION> | <RELEASE>}]}(noskipws)+ | remove {<PKG>}+  | 
purge {<PKG>}+ | source {<PKG> [={<VERSION> | <RELEASE>}]}(noskipws)+ | build-dep {<PKG> [={<VERSION> | <RELEASE>}]}(noskipws)+ | 
download {<PKG> [={<VERSION> | <RELEASE>}]}(noskipws)+  | check | clean | autoclean | autoremove | {-v | --version} | {-h | --help}})#


message m1 = "hello"
message m2 = "noo"
message m3 = "mde"
"""


COMMANDLINE = "apt-get install -y hello"