from textx import metamodel_from_file
from collections import OrderedDict, defaultdict, namedtuple
from clchecker.constants import BASETYPE
from clchecker.store import Command, Store
from clchecker import config
import os


def text_of_obj_in_model(textx_obj, model):
    start = textx_obj._tx_position
    end = textx_obj._tx_position_end
    return model._tx_parser.input[start:end]


class Translator():
    """
    All methods whose name starts with "process_" are to process the lexer and 
    return the title of the lexar. 

    The `title` of `sub_command`, `equal`, `type` are the value of themselves. The
    `title`s of `Option` are `ShortOption_0` or `LongOption_0`, etc. The `title`s 
    of the `Collection` are `OptionalCollection_0` or `OneMustPresentCollection_0`, etc. 
    Each `Option`, `Collection` and `Statement` forms a `sub_rule` whose name is the `title`
    of the themselves.
    """

    def __init__(self, synopsis_metamodel, store=None):
        self.sub_rules = OrderedDict()
        self.synopsis_metamodel = synopsis_metamodel
        self.num_OptionalCollections = 0
        self.num_OneMustPresentCollections = 0
        self.num_ShortOptions = 0
        self.num_LongOptions = 0
        self.num_SequentialStatements = 0
        self.num_UnorderedStatements = 0
        self.synop = ''
        self.spec = Specification()
        self.num_SubCommands = 0

        # text that translated from the synop
        self.tx_syntax = ''
        self.store = store

    @staticmethod
    def get_element_type(element):
        ''' get the tpye of the `element` in one of `types.keys()`'''
        types = {
            'sub_command': False,
            'option': False,
            'collection': False,
            'equal': False,
            'type': False
        }
        for typ in types.keys():
            if getattr(element, typ):
                types[typ] = True

        # only one value in types can be True
        if sum(types.values()) != 1:
            raise ValueError(
                f'element {element} has more than one types {[typ for typ in types if types[typ]]}')
        for typ in types:
            if types[typ]:
                return typ

    def process_equal(self, equal):
        return '"="', '"="'

    def process_sub_command(self, sub_command):
        title = f'SubCommand_{self.num_SubCommands}'
        readable_syntax = f"{sub_command.content}"
        self.num_SubCommands += 1
        self.sub_rules[title] = f'content="{sub_command.content}"'

        # each sub_command is a tag by default
        self.spec.tag_to_clsname[sub_command.content] = title

        specification = sub_command.specification
        if specification:
            # the title is the clsname for sub_command
            self.spec.textx_specs_and_clsname.append(
                (specification, title))
            if specification.tag:
                self.spec.tag_to_clsname['tag:' +
                                         specification.tag.name] = title
        self.spec.clsname_to_readable_syntax[title] = readable_syntax
        return title, readable_syntax

    def process_type(self, type):
        clsname = f'{type.type_name.upper()}'
        return clsname, clsname

    def process_option(self, option):
        option_content = f'option_key="{option.dash + option.option}"'
        readable_syntax = f"{option.dash + option.option}"
        if option.dash == '-':
            title = f'ShortOption_{self.num_ShortOptions}?'
            self.num_ShortOptions += 1
        else:
            title = f'LongOption_{self.num_LongOptions}?'
            self.num_LongOptions += 1
        if option.type and option.multi:
            option_content += f' ("=")? value+={option.type.type_name.upper()}'
            readable_syntax += f' ("=")? ({option.type.type_name.upper()})+'
        elif option.type:
            option_content += f' ("=")? value={option.type.type_name.upper()}'
            readable_syntax += f' ("=")? {option.type.type_name.upper()}'

        # clsname of option doesnot include "?"
        self.spec.clsname_to_readable_syntax[title[:-1]] = readable_syntax
        self.sub_rules[title] = option_content
        return title, readable_syntax

    def process_collection(self, collection):
        if collection.optional_collection:
            collection_type = 'OptionalCollection'
            lowercase_coll_type = 'optional_collection'
        else:
            collection_type = 'OneMustPresentCollection'
            lowercase_coll_type = 'one_must_present_collection'

        statements = getattr(collection, lowercase_coll_type).statements
        multi = getattr(collection, lowercase_coll_type).multi

        # construct the clsname of the collection
        num = getattr(self, "num_"+collection_type+'s')
        clsname = f"{collection_type}_{num}"
        clsname_usage = f'{clsname}{"?" if collection_type=="OptionalCollection" else ""}'
        setattr(self, "num_"+collection_type+'s', num+1)

        choices = []
        readable_syntax = []
        for i, statement in enumerate(statements):
            statement_clsname_usage, statement_readable_syntax = self.process_statement(
                statement)
            choices.append(f"statement{i}={statement_clsname_usage}")
            readable_syntax.append(statement_readable_syntax)

        self.sub_rules[clsname] = choices
        readable_syntax = f"{' | '.join(readable_syntax)}"
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        if multi:
            clsname_multi = clsname + '_Multi'
            content = f"statements{multi}={clsname_usage}"
            self.sub_rules[clsname_multi] = content
            readable_syntax = f"({readable_syntax}){multi}"
            self.spec.clsname_to_readable_syntax[clsname_multi] = readable_syntax
            clsname = clsname_multi
            clsname_usage = clsname

        specification = getattr(collection, lowercase_coll_type).specification
        if specification:
            self.spec.textx_specs_and_clsname.append(
                (specification, clsname))
            if specification.tag:
                self.spec.tag_to_clsname['tag:' +
                                         specification.tag.name] = clsname

        return clsname_usage, readable_syntax

    def process_element(self, element):
        element_type = self.get_element_type(element)
        clsname_usage, readable_syntax = getattr(self, f"process_{element_type}")(
            getattr(element, element_type))
        return clsname_usage, readable_syntax

    def process_statement(self, statement):
        if statement.sequential_statement:
            statement_type = 'SequentialStatement'
            elements = statement.sequential_statement.elements
        else:
            statement_type = 'UnorderedStatement'
            elements = statement.unordered_statement.elements

        num = getattr(self, "num_"+statement_type+'s')
        clsname = f'{statement_type}_{num}'
        setattr(self, "num_"+statement_type+'s', num+1)

        content = []
        readable_syntax = []
        for i, element in enumerate(elements):
            clsname_usage, element_readable_syntax = self.process_element(element)
            content.append(f"element{i}={clsname_usage}")
            readable_syntax.append(element_readable_syntax)
        content = ' '.join(content)
        readable_syntax = ' '.join(readable_syntax)

        if statement_type == 'UnorderedStatement':
            content = '(' + content + ')#'
            readable_syntax = '(' + readable_syntax + ')UnOrdered'
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def translate(self, synop, save_to_file=False, save_dir=None, save_to_db=False):
        model = self.synopsis_metamodel.model_from_str(synop)
        if model.messages:
            for message in model.messages:
                self.spec.message_vars[message.var] = message.value

        if save_to_file:
            file_name = os.path.join(save_dir, f'{model.command}.tx')

        self.tx_syntax += f'// DSL for command "{model.command}"\n\n'
        self.tx_syntax += f'Main_Rule:\n\tcommand="{model.command}" '
        statement = model.statement
        statement_title, _ = self.process_statement(statement)
        self.tx_syntax += f"statement={statement_title}"
        self.tx_syntax += '\n;'

        self.spec.process_textx_specs()

        # append each sub_rule
        while 1:
            try:
                rule_name, content = self.sub_rules.popitem(last=False)
                clsname = rule_name[:-
                                    1] if rule_name.endswith("?") else rule_name
                # check whether there is a noskipws spec for the clsname
                noskipws = False
                if clsname in self.spec.concrete_specs and 'noskipws' in self.spec.concrete_specs[clsname]:
                    noskipws = True

                # if noskipws is True, then we can not skip the white space.
                # for example, tensorflow==0.1.19 is valid while
                # tensorflow== 0.1.19 is not. But we allow white space at the
                # beginning or at the end. So we need to add /\s*/- manually
                # check http://textx.github.io/textX/stable/grammar/#match-suppression
                if noskipws:
                    self.tx_syntax += f'\n\n{clsname}[noskipws]:\n\t/\s*/- '
                else:
                    self.tx_syntax += f'\n\n{clsname}:\n\t'

                if rule_name.startswith('LongOption') or rule_name.startswith('ShortOption'):
                    self.tx_syntax += content
                elif 'Statement' in rule_name or rule_name.endswith('Multi') or rule_name.startswith('SubCommand'):
                    self.tx_syntax += content
                else:
                    self.tx_syntax += ' | '.join(content)
                if noskipws:
                    self.tx_syntax += ' /\s*/-'
                self.tx_syntax += '\n;'
            except KeyError:
                break
        # process the Main_Rule first and write it to a file. add collections as sub_rules to self.sub_rules
        if save_to_file:
            with open(file_name, 'w') as f:
                f.write(self.tx_syntax)
                f.write(BASETYPE)

        if save_to_db:
            if self.store is None:
                raise ValueError('Mongodb is not passed to the translator')
            command_name = model.command
            concrete_specs = self.spec.concrete_specs
            clsname_to_readable_syntax = self.spec.clsname_to_readable_syntax
            command = Command(command_name, self.tx_syntax, clsname_to_readable_syntax,
                              concrete_specs, synop)
            self.store.addcommand(command)


class Specification:
    def __init__(self):
        '''
        // Word2 is Word that can start with 'tag:' which may followed by dash or double dashes
        Word2:
            /(tag:)?(-(-)?)?[^\d\W][\w-]*/
        ;

        //complete format of the concrete_spect:
        `clsname`: {
            # when key happens, its values always happen
            'after':  {'word2s': [], 'one_must_present': []},

            # when key and its values happen at the same time,
            # the key's position is before its values
            'before': {'word2s': [], 'one_must_present': []},

            # when key and its values happen at the same time,
            # the key's position is before its values
            'always': {'word2s': [], 'one_must_present': []},

            # when key happens, all of its values can happen
            'mutex': {'word2s': [], 'one_must_present': []},

            'info': {
                'warning': None,
                'error': None,
                'example': None
            }
        }'''
        self.message_vars = {}

        self.tag_to_clsname = {}
        self.textx_specs_and_clsname = []
        self.concrete_specs = defaultdict(dict)
        self.clsname_to_readable_syntax = {}

    def get_clsname(self, word2):
        if word2 not in self.tag_to_clsname:
            raise ValueError(f'{word2} is not a valid word2')
        return self.tag_to_clsname[word2]

    # process 'after', 'before', 'always', 'mutex'
    # `tpy` is one of 'after', 'before', 'always', 'mutex'
    def process_a_b_a_m(self, spec, typ, clsname):
        item = getattr(spec, typ).item
        if typ not in self.concrete_specs[clsname]:
            self.concrete_specs[clsname][typ] = {}
        if item.list_of_word2s:
            for word2 in item.list_of_word2s.word2s:
                if 'word2s' not in self.concrete_specs[clsname][typ]:
                    self.concrete_specs[clsname][typ]['word2s'] = []
                word2_clsname = self.get_clsname(word2)
                self.concrete_specs[clsname][typ]['word2s'].append(
                    word2_clsname)
        else:
            for word2 in item.one_must_present_item.word2s:
                if 'one_must_present' not in self.concrete_specs[clsname][typ]:
                    self.concrete_specs[clsname][typ]['one_must_present'] = []
                word2_clsname = self.get_clsname(word2)
                self.concrete_specs[clsname][typ]['one_must_present'].append(
                    word2_clsname)

    def process_info(self, spec, clsname):
        for info_type in ('warning', 'error', 'example'):
            if getattr(spec.info, info_type):
                if getattr(spec.info, info_type).msg.var:
                    var = getattr(spec.info, info_type).msg.var
                    string = self.message_vars[var]
                else:
                    string = getattr(spec.info, info_type).msg.string
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                    self.concrete_specs[clsname]['info'] = {}
                self.concrete_specs[clsname]['info'][info_type] = string

    def process_textx_specs(self):
        for spec, clsname in self.textx_specs_and_clsname:
            for typ in ('after', 'before', 'always', 'mutex'):
                if getattr(spec, typ):
                    if clsname not in self.concrete_specs:
                        self.concrete_specs[clsname] = {}
                    self.process_a_b_a_m(spec, typ, clsname)
            if spec.info:
                self.process_info(spec, clsname)
            if spec.noskipws:
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                self.concrete_specs[clsname]['noskipws'] = True


if __name__ == "__main__":
    meta = metamodel_from_file('clchecker/synopsis.tx', autokwd=True)
    with open(os.path.join(config.SYNOPDIR, 'apt-get-test.synop'), 'r') as f:
        synop = f.read()
    store = Store(db='clchecker_test')
    translator = Translator(synopsis_metamodel=meta)
    translator.translate(synop, save_to_file=True,
                         save_dir=config.SYNOPDIR)
    import json
    with open(os.path.join(config.SYNOPDIR, 'apt-get.json'), 'w') as f:
        json.dump(translator.spec.concrete_specs, f)
