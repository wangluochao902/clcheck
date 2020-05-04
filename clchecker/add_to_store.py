from clchecker.checker import CLchecker
from clchecker.store import Store, Command
from clchecker.translate import Translator
from textx import metamodel_from_file
import config
import argparse

parser = argparse.ArgumentParser(
    description='translate the eman and add it to the database')
parser.add_argument('--eman_path', nargs='+', type=str, help='paths of eman')
parser.add_argument('--overwrite',
                    action='store_true',
                    help='overwrite if exists')
parser.add_argument(
    '--allow_end',
    action='store_true',
    help='allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption')
args = parser.parse_args()

if __name__ == "__main__":
    store = Store(db='clchecker')
    metamodel = metamodel_from_file(config.EMAN)
    translator = Translator(metamodel, store)
    if not args.eman_path:
        raise ("--eman_path can't be empty")
    for path in args.eman_path:
        with open(path, 'r') as f:
            eman = f.read()
        translator.translate(
            eman,
            save_to_file=True,
            save_dir=config.EMANDIR,
            save_to_db=True,
            overwrite_db_if_exsits=args.overwrite,
            allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=args.
            allow_end)
