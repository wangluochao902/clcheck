from textx import metamodel_from_file
from textx.model import get_children_of_type
from collections import OrderedDict, defaultdict, namedtuple
from clchecker.constants import BASETYPE
from clchecker.store import Command, Store
import config
import os, re


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

    def __init__(self, metamodel, store=None):
        self.metamodel = metamodel
        self.store = store

    def reset(self):
        self.options_session = None
        self.options_session_readable_syntax = None

        self.sub_rules = OrderedDict()
        self.num_OptionalCollections = 0
        self.num_OneMustPresentCollections = 0
        self.num_SequentialStatements = 0
        self.num_UnorderedStatements = 0
        self.eman = None
        self.spec = Specification()
        self.num_SubCommands = 0
        self.ShortOption_clsnames = []
        self.LongOption_clsnames = []

        # OptionPair:
        #     key=Word2 (":" optional_collection=OptionalCollection? specification=Specification?)?
        # ;
        # 
        # this is an example of OptionPair `-d: [-d | --download-only]`. In the optional collection, 
        # only one of `-d` or `download-only can appear`
        # we collect OptionPair_key_to_clsnames to track whether an multiple option in the 
        # OptionalCollection appear at the same time.
        self.OptionPair_key_to_clsnames = defaultdict(list)

        # text that translated from the synop
        self.tx_syntax = ''

    @staticmethod
    def preprocess_options_sesstion(eman, options):
        '''create optional_collection if not present in a pair'''
        processed_pairs = []
        if options.pairs:
            for pair in options.pairs:
                processed_pair = ''
                if pair.optional_collection:
                    start = pair.optional_collection._tx_position
                    end = pair.optional_collection._tx_position_end
                    collection = eman[start:end]
                else:
                    collection = "[" + pair.key + "]"
                processed_pair = pair.key + ":" + collection
                if pair.specification and pair.optional_collection and pair.optional_collection.specification:
                    raise(f"{pair.key} has 2 specification for a option")
                if pair.specification:
                    start = pair.specification._tx_position
                    end = pair.specification._tx_position_end
                    processed_pair += eman[start:end]
                processed_pairs.append(processed_pair)
        return '\n\ne-options:\n\t' + '\n\t'.join(processed_pairs) + '\ne-end'

    def preprocess(self, eman):
        model = self.metamodel.model_from_str(eman)
        variables = dict()
        if model.variables.vars:
            for pair in model.variables.vars:
                variables[pair.varname] = pair.value
                self.spec.message_vars[pair.varname] = pair.value

        new_eman = ''
        placeholders = get_children_of_type("PlaceHolder", model)
        # replace the placeholder in synopsis with values in variables
        if placeholders:
            pre_position = 0
            for placeholder in placeholders:
                new_eman += eman[pre_position:placeholder._tx_position]
                if placeholder.value == "options":
                    new_eman += eman[placeholder._tx_position: placeholder._tx_position_end]
                else:
                    assert placeholder.value in variables, f"{placeholder.value} is not defined"
                    new_eman += variables[placeholder.value]
                pre_position = placeholder._tx_position_end
            new_eman += eman[pre_position:model.synopsis._tx_position_end]

        if model.options:
            new_options = self.preprocess_options_sesstion(eman, model.options)
            new_eman += new_options

        if model.explanation:
            new_eman += '\n\n' + \
                eman[model.explanation._tx_position:model.explanation._tx_position_end]
        return new_eman

    def process_options_session_util(self):
        """
        In linux, usually short options can be combined. For example apt-get -qqy install pkg.
        we need to create a rule to match this.
        """
        pass

    def process_options_session(self, options):
        if not self.options_session_readable_syntax:
            options_session_readable_syntax = []
            choices = []
            if options.pairs:
                for pair in options.pairs:
                    cls_name, readable_syntax = self.process_collection_util(
                        "OptionalCollection", pair.optional_collection.statements, pair.optional_collection.specification)
                    self.spec.ref_to_clsname[pair.key] = cls_name
                    options_session_readable_syntax.append(readable_syntax)
                    choices.append(cls_name+"?")
            self.options_session_readable_syntax = '\n'.join(
                options_session_readable_syntax)
            self.sub_rules["OptionSession"] = "(" + ' | '.join(choices) + ")#"
        return "OptionSession", self.options_session_readable_syntax

    @staticmethod
    def get_element_type(element):
        ''' get the tpye of the `element` in one of `types.keys()`'''
        types = {
            'sub_command': False,
            'single_option': False,
            'collection': False,
            'equal': False,
            'type': False,
            "unordered_statement": False,
            "placeholder": False
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
        clsname = f'SubCommand_{self.num_SubCommands}'
        readable_syntax = f"{sub_command.value}"
        self.num_SubCommands += 1
        self.sub_rules[clsname] = f'value="{sub_command.value}"'

        # each sub_command is a tag by default
        self.spec.ref_to_clsname[sub_command.value] = clsname

        specification = sub_command.specification
        if specification:
            # the clsname is the clsname for sub_command
            self.spec.textx_specs_and_clsname.append(
                (specification, clsname))

        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_type(self, type):
        clsname = f'{type.type_name.upper()}'
        return clsname, clsname

    def process_single_option(self, single_option):
        single_option_content = f'option_key="{single_option.dash + single_option.option}"'
        readable_syntax = f"{single_option.dash + single_option.option}"
        if single_option.dash == '-':
            clsname = f'ShortOption_{len(self.ShortOption_clsnames)}'
            self.ShortOption_clsnames.append(clsname)
        else:
            clsname = f'LongOption_{len(self.LongOption_clsnames)}'
            self.LongOption_clsnames.append(clsname)
        if single_option.type and single_option.multi:
            single_option_content += f' ("=")? value+={single_option.type.type_name.upper()}'
            readable_syntax += f' ("=")? ({single_option.type.type_name.upper()})+'
        elif single_option.type:
            single_option_content += f' ("=")? value={single_option.type.type_name.upper()}'
            readable_syntax += f' ("=")? {single_option.type.type_name.upper()}'

        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        self.sub_rules[clsname] = single_option_content
        return clsname, readable_syntax

    def process_placeholder(self, placeholder):
        assert placeholder.value == "options", "Non-options placeholder is still there, please check"
        return self.process_options_session(self.options_sesstion)

    def process_collection(self, collection):
        if collection.optional_collection:
            collection_type = 'OptionalCollection'
            lowercase_coll_type = 'optional_collection'
        else:
            collection_type = 'OneMustPresentCollection'
            lowercase_coll_type = 'one_must_present_collection'

        statements = getattr(collection, lowercase_coll_type).statements
        specification = getattr(collection, lowercase_coll_type).specification
        return self.process_collection_util(collection_type, statements, specification)

    def process_collection_util(self, collection_type, statements, specification=None):
        # construct the clsname of the collection
        num = getattr(self, "num_"+collection_type+'s')
        clsname = f"{collection_type}_{num}"
        setattr(self, "num_"+collection_type+'s', num+1)

        choices = []
        readable_syntax = []
        for i, statement in enumerate(statements):
            statement_clsname, statement_readable_syntax = self.process_statement(
                statement)
            choices.append(f"statement{i}={statement_clsname}")
            readable_syntax.append(statement_readable_syntax)

        content = ' | '.join(choices)
        self.sub_rules[clsname] = content
        readable_syntax = f"{' | '.join(readable_syntax)}"
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        if specification:
            self.spec.textx_specs_and_clsname.append(
                (specification, clsname))

        return clsname, readable_syntax

    def process_element(self, element):
        element_type = self.get_element_type(element)
        multi = element.multi
        clsname, readable_syntax = getattr(self, f"process_{element_type}")(
            getattr(element, element_type))

        if multi:
            clsname_multi = clsname + '_Multi'
            content = f"{element_type}s{multi}={clsname}"
            self.sub_rules[clsname_multi] = content
            readable_syntax = f"({readable_syntax}){multi}"
            self.spec.clsname_to_readable_syntax[clsname_multi] = readable_syntax
            clsname = clsname_multi
        return clsname, readable_syntax

    def process_statement(self, statement):
        if statement.sequential_statement:
            statement_type = 'SequentialStatement'
            elements = statement.sequential_statement.elements
        else:
            statement_type = 'UnorderedStatement'
            elements = statement.unordered_statement.elements
        return self.process_statement_util(statement_type, elements)

    def process_statement_util(self, statement_type, elements):
        num = getattr(self, "num_"+statement_type+'s')
        clsname = f'{statement_type}_{num}'
        setattr(self, "num_"+statement_type+'s', num+1)

        content = []
        readable_syntax = []
        for i, element in enumerate(elements):
            element_clsname, element_readable_syntax = self.process_element(
                element)
            # OptionalCollection or OptionSession
            if "OptionalCollection" in element_clsname or "OptionSession" in element_clsname:
                element_clsname_usage = element_clsname + "?"
            else:
                element_clsname_usage = element_clsname
            content.append(f"element{i}={element_clsname_usage}")
            readable_syntax.append(element_readable_syntax)
        content = ' '.join(content)
        readable_syntax = ' '.join(readable_syntax)

        if statement_type == 'UnorderedStatement':
            content = '(' + content + ')#'
            readable_syntax = '(' + readable_syntax + ')UnOrdered'
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_unordered_statement(self, unordered_statement):
        return self.process_statement_util("UnorderedStatement", unordered_statement.elements)

    def translate(self, eman, save_to_file=False, save_dir=None, save_to_db=False, overwrite_db_if_exsits=False):
        self.reset()
        self.eman = self.preprocess(eman)

        model = self.metamodel.model_from_str(self.eman)
        synopsis = model.synopsis
        self.options_sesstion = model.options

        if save_to_file:
            file_name = os.path.join(save_dir, f'{synopsis.command}.tx')

        self.tx_syntax += f'// DSL for command "{synopsis.command}"\n\n'
        self.tx_syntax += f'Main_Rule:\n\tcommand="{synopsis.command}" '
        statement = synopsis.statement
        statement_clsname, _ = self.process_statement(statement)
        self.tx_syntax += f"statement={statement_clsname}"
        self.tx_syntax += '\n;'

        # process specification and explanation
        self.spec.process_textx_specs()
        self.spec.process_explanation(model.explanation)

        # append each sub_rule
        while 1:
            try:
                clsname, content = self.sub_rules.popitem(last=False)
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
                self.tx_syntax += content
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
            command_name = synopsis.command
            concrete_specs = self.spec.concrete_specs
            explanation = self.spec.explanation
            clsname_to_readable_syntax = self.spec.clsname_to_readable_syntax
            command = Command(command_name, self.tx_syntax, clsname_to_readable_syntax,
                              concrete_specs, explanation, eman)
            self.store.addcommand(command, overwrite=overwrite_db_if_exsits)
        return self.tx_syntax + BASETYPE


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
            'after':  {'all_must_present': [], 'one_must_present': []},

            # when key and its values happen at the same time,
            # the key's position is before its values
            'before': {'all_must_present': [], 'one_must_present': []},

            # when key and its values happen at the same time,
            # the key's position is before its values
            'always': {'all_must_present': [], 'one_must_present': []},

            # when key happens, all of its values can happen
            'mutex': {'all_must_present': [], 'one_must_present': []},

            'info': {
                'warning': None,
                'error': None,
                'example': None
            }
        }'''
        self.message_vars = {}

        self.ref_to_clsname = {}
        self.textx_specs_and_clsname = []
        self.concrete_specs = defaultdict(dict)
        self.clsname_to_readable_syntax = {}
        self.explanation = {}

    @staticmethod
    def start_and_end_with_quotes(string):
        if string.startswith('"') or string.startswith("'") or string.endswith("'") or string.endswith('"'):
            return True
        return False

    def get_clsname(self, ref):
        if ref not in self.ref_to_clsname:
            raise ValueError(f'{ref} is not a valid ref')
        return self.ref_to_clsname[ref]

    # process 'after', 'before', 'always', 'mutex'
    # `tpy` is one of 'after', 'before', 'always', 'mutex'
    def process_after_before_always_must(self, spec, typ, clsname):
        item = getattr(spec, typ).item
        if typ not in self.concrete_specs[clsname]:
            self.concrete_specs[clsname][typ] = {}
        if item.all_must_present_item:
            for ref in item.all_must_present_item.refs:
                if 'all_must_present' not in self.concrete_specs[clsname][typ]:
                    self.concrete_specs[clsname][typ]['all_must_present'] = []
                ref_clsname = self.get_clsname(ref)
                self.concrete_specs[clsname][typ]['all_must_present'].append(
                    ref_clsname)
        else:
            for ref in item.one_must_present_item.refs:
                if 'one_must_present' not in self.concrete_specs[clsname][typ]:
                    self.concrete_specs[clsname][typ]['one_must_present'] = []
                ref_clsname = self.get_clsname(ref)
                self.concrete_specs[clsname][typ]['one_must_present'].append(
                    ref_clsname)

    def process_info(self, spec, clsname):
        for info_type in ('warning', 'error', 'example'):
            if getattr(spec.info, info_type):
                if getattr(spec.info, info_type).value.var:
                    var = getattr(spec.info, info_type).value.var
                    string = self.message_vars[var]
                else:
                    string = getattr(spec.info, info_type).value.string
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                    self.concrete_specs[clsname]['info'] = {}
                self.concrete_specs[clsname]['info'][info_type] = string

        # process other_key_values
        if spec.info.other_key_values:
            if clsname not in self.concrete_specs:
                self.concrete_specs[clsname] = {}
                self.concrete_specs[clsname]['info'] = {}
            for key_value in spec.info.other_key_values:
                if key_value.value.var:
                    var = key_value.value.var
                    assert self.start_and_end_with_quotes(
                        self.message_vars[var]), "Only variable enclosed by `'` or `\"` is allowed in options sesstion"
                    string = self.message_vars[var]
                else:
                    string = key_value.value.string
                self.concrete_specs[clsname]['info'][key_value.key] = string

    def process_textx_specs(self):
        for spec, clsname in self.textx_specs_and_clsname:
            for typ in ('after', 'before', 'always', 'mutex'):
                if getattr(spec, typ):
                    if clsname not in self.concrete_specs:
                        self.concrete_specs[clsname] = {}
                    self.process_after_before_always_must(spec, typ, clsname)
            if spec.info:
                self.process_info(spec, clsname)
            if spec.noskipws:
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                self.concrete_specs[clsname]['noskipws'] = True

    def process_explanation(self, explanation):
        if explanation.pairs:
            for pair in explanation.pairs:
                keys = pair.keys
                values = []
                for i in range(len(pair.values)):
                    v = pair.values[i].value
                    if v.endswith('<br/>'):
                        values.append(v[:-5])
                        values.append('\n')
                    elif v.endswith('<br />'):
                        values.append(v[:-6])
                        values.append('\n')
                    elif re.match(r'[\w-]', v[-1])  and i < len(pair.values)-1 and pair.values[i+1].value[0] not in '\t\n ':
                        values.append(v+' ')
                    else:
                        values.append(v)
                value = ''.join(values)
                for key in keys:
                    self.explanation[key] = value
