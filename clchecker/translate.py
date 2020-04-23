from textx import metamodel_from_file
from textx.model import get_children_of_type
from collections import OrderedDict, defaultdict, namedtuple, deque
from clchecker.constants import BASETYPE
from clchecker.store import Command, Store
import config
import os
import re


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

    def reset(self,
              allow_CombinedShortOption=True,
              CombinedShortOption_required_dash=True):
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
        self.num_OptionSessionCollections = 0
        self.num_OptionSessions = 0
        self.OptionSession_name_to_clsnames = {}
        self.ShortOptionWithoutValue_clsnames = []
        self.ShortOptionWithValue_clsnames = []
        self.LongOptionWithValue_clsnames = []
        self.LongOptionWithoutValue_clsnames = []
        self.allow_CombinedShortOption = allow_CombinedShortOption
        self.CombinedShortOption_required_dash = CombinedShortOption_required_dash
        self.regex_to_clsname = {}

        self.all_short_option_with_value = []
        self.all_short_option_with_value_readable_syntax = []

        # OptionPair:
        #     key=Word2 (":" optional_collection=OptionalCollection? specification=Specification?)?
        # ;
        #
        # this is an example of OptionPair `-d: [-d | --download-only]`. In the optional collection,
        # only one of `-d` or `download-only can appear`
        # we collect OptionPair_key_to_option_keys_and_readable_syntax to track whether an multiple option in the
        # OptionalCollection appear at the same time.
        self.OptionPair_key_to_option_keys_and_readable_syntax = defaultdict(
            list)

        # text that translated from the synop
        self.tx_syntax = ''

    @staticmethod
    def pre_process_option_sesstion(eman, option):
        '''create optional_collection if not present in a pair'''
        processed_pairs = []
        if option.pairs:
            for pair in option.pairs:
                if pair.colon and not pair.option_session_collection.single_options and not pair.option_session_collection.specification:
                    raise (
                        f"{pair.key} is followed by a colon(:), but neither option_session_collection nor specification is followed"
                    )
                processed_pair = ''
                if pair.option_session_collection and pair.option_session_collection.single_options:
                    single_options = pair.option_session_collection.single_options
                    single_options = [
                        eman[so._tx_position:so._tx_position_end]
                        for so in single_options
                    ]
                else:
                    single_options = [pair.key]
                processed_pair = pair.key + ":" + '[' + ' | '.join(
                    single_options) + ']'
                if pair.option_session_collection and pair.option_session_collection.specification:
                    start = pair.option_session_collection.specification._tx_position
                    end = pair.option_session_collection.specification._tx_position_end
                    processed_pair += eman[start:end]
                processed_pairs.append(processed_pair)
        return f'\n\ne-options {option.name}:\n\t' + '\n\t'.join(
            processed_pairs) + '\ne-end'

    def pre_process(self, eman):
        model = self.metamodel.model_from_str(eman)
        variables = dict()
        if model.variables and model.variables.vars:
            for pair in model.variables.vars:
                variables[pair.varname] = pair.value
                self.spec.message_vars[pair.varname] = pair.value
        if model.options:
            OptionSession_name = [option.name for option in model.options]

        new_eman = ''
        placeholders = get_children_of_type("PlaceHolder", model.synopsis)
        # replace the placeholder in synopsis with values in variables
        pre_position = 0
        if placeholders:
            for placeholder in placeholders:
                new_eman += eman[pre_position:placeholder._tx_position]
                # only replace non option session placeholder
                if placeholder.value in OptionSession_name:
                    new_eman += eman[placeholder._tx_position:placeholder.
                                     _tx_position_end]
                else:
                    assert placeholder.value in variables, f"{placeholder.value} is not defined"
                    new_eman += variables[placeholder.value]
                pre_position = placeholder._tx_position_end
            new_eman += eman[pre_position:model.synopsis._tx_position_end]
        else:
            new_eman += eman[:model.synopsis._tx_position_end]

        if model.options:
            for option in model.options:
                new_options = self.pre_process_option_sesstion(eman, option)
                new_eman += new_options

        if model.explanation:
            new_eman += '\n\n' + \
                eman[model.explanation._tx_position:model.explanation._tx_position_end]
        return new_eman

    def process_combined_short_option(self):
        """
        In linux, usually short options can be combined. For example apt-get -qqy install pkg.
        we need to create a rule to match this.
        """
        # sort clsnames so that "-qq" will be matched before "-q"
        self.ShortOptionWithoutValue_clsnames.sort(key=lambda clsname: len(
            self.spec.clsname_to_readable_syntax[clsname]),
                                                   reverse=True)

        readable_syntax = ''.join([
            self.spec.clsname_to_readable_syntax[clsname]
            for clsname in self.ShortOptionWithoutValue_clsnames
        ])

        content = ' | '.join([
            f"short_option_without_dash{i}={clsname}"
            for i, clsname in enumerate(self.ShortOptionWithoutValue_clsnames)
        ])
        content = '(' + content + ')'
        clsname = "ShortOptionWithoutDash"
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        clsname_comb = "CombinedShortOption"
        if self.CombinedShortOption_required_dash:
            content = '"-" combined_short_options_without_dash+=ShortOptionWithoutDash'
            dash_or_not = '-'
        else:
            content = 'combined_short_options_without_dash+=ShortOptionWithoutDash'
            dash_or_not = ''
        readable_syntax_comb = dash_or_not + "(" + readable_syntax + ")+"
        self.spec.clsname_to_readable_syntax[
            clsname_comb] = readable_syntax_comb
        self.sub_rules[clsname_comb] = content
        self.spec.concrete_specs[clsname_comb]['nws'] = True

        clsname_multi = "CombinedShortOption_Multi"
        self.sub_rules[clsname_multi] = f"CombinedShortOptions+={clsname_comb}"
        readable_syntax_multi = "(" + readable_syntax_comb + ")+"
        self.spec.clsname_to_readable_syntax[
            clsname_multi] = readable_syntax_multi
        return clsname_multi, readable_syntax_multi

    def process_option_session_collection(self, option_session_collection,
                                          OptionPair_key):
        # construct the clsname of the collection
        clsname = f"OptionSessionCollection_{self.num_OptionSessionCollections}"
        self.num_OptionSessionCollections += 1
        choices = []
        readable_syntaxes = []
        for i, single_option in enumerate(
                option_session_collection.single_options):
            single_option_clsname, single_option_readable_syntax = self.process_single_option(
                single_option=single_option,
                OptionPair_key=OptionPair_key,
                add_option_to_OptionPair=True)

            if single_option_clsname is None:
                continue
            choices.append(f"single_option{i}={single_option_clsname}")
            readable_syntaxes.append(single_option_readable_syntax)

        if not choices:
            return None, None

        content = '(' + ' | '.join(choices) + ')'
        self.sub_rules[clsname] = content
        readable_syntax = f"{' | '.join(readable_syntaxes)}"
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        if option_session_collection.specification:
            self.spec.textx_specs_and_clsname_ref.append(
                (option_session_collection.specification, clsname,
                 OptionPair_key))

        return clsname, readable_syntax

    def process_short_option_with_value(self, option_session_index):
        clsname = f"AllShortOptionWithValueAtOptionSession{option_session_index}"
        # self.num_OptionSessions += 1
        content = ' | '.join([
            f'choice{i}={single_option}'
            for i, single_option in enumerate(self.all_short_option_with_value)
        ])
        readable_syntax = '|\n'.join(
            self.all_short_option_with_value_readable_syntax)
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_options_session(self, options):
        for option_session_index, option in enumerate(options):
            option_session_readable_syntax = []
            choices = []
            if option.pairs:
                i = 1
                for pair in option.pairs:
                    clsname_coll, readable_syntax = self.process_option_session_collection(
                        pair.option_session_collection, OptionPair_key=pair.key)
                    if clsname_coll is not None:
                        option_session_readable_syntax.append(readable_syntax)
                        choices.append(f"choice{i}={clsname_coll}")
                        i += 1

                pre_choices = []
                pre_readable_syntax = []
                # short option with value has the top priority, so it should put at the very beginning
                if self.all_short_option_with_value:
                    clsname_short_value, readable_syntax_short_value = self.process_short_option_with_value(
                        option_session_index)
                    pre_choices.append(f"choice{i}={clsname_short_value}")
                    pre_readable_syntax.append(readable_syntax_short_value)
                    i += 1

                # CombinedShortOption should be put after short option with value, but before others
                if self.allow_CombinedShortOption:
                    comb_clsname, comb_readable_syntax = self.process_combined_short_option(
                    )
                    pre_choices.append(f"choice{i}={comb_clsname}")
                    pre_readable_syntax.append(comb_readable_syntax)
                choices = pre_choices + choices
            clsname_choice = f"AllOptionChoice_{option_session_index}"
            readable_syntax = ' |\n'.join(option_session_readable_syntax)
            self.sub_rules[clsname_choice] = '(' + ' | '.join(choices) + ")"
            self.spec.clsname_to_readable_syntax[
                clsname_choice] = readable_syntax

            clsname = f"OptionSession_{option_session_index}"
            content = f"all_option_choices+={clsname_choice}"
            self.sub_rules[clsname] = content
            self.spec.clsname_to_readable_syntax[
                clsname] = '(' + readable_syntax + ')+'
            self.OptionSession_name_to_clsnames[option.name] = clsname

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
                f'element {element} has more than one types {[typ for typ in types if types[typ]]}'
            )
        for typ in types:
            if types[typ]:
                return typ

    def process_equal(self, equal):
        return '"="', '"="'

    def process_sub_command(self, sub_command):
        clsname = f'SubCommand_{self.num_SubCommands}'
        readable_syntax = f"{sub_command.value}"
        self.num_SubCommands += 1

        # treat it as a keyword, so we need to add word boundary. But we can't use
        # r'\b' since '-' does not belong to '\w'. So we use negative look-behind
        # r'(?<!(\w|\-))' and negative look-ahead r'(?!(\w|\-))'. That is we don't
        # allow have '\w' or '-' before or after the keyword
        value = r'/(?<!(\w|\-))' + re.escape(
            sub_command.value) + r'(?!(\w|\-))/'
        self.sub_rules[clsname] = f'value={value}'

        # each sub_command is a tag by default
        self.spec.sub_commands.append(sub_command.value)

        specification = sub_command.specification
        if specification:
            # the clsname is the clsname for sub_command
            self.spec.textx_specs_and_clsname_ref.append(
                (specification, clsname))

        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_type(self, type):
        type_name = type.type_name
        # check whether type_name is a REGEX
        if type_name.startswith('/') and type_name.endswith('/'):
            if type_name in self.regex_to_clsname:
                clsname = self.regex_to_clsname[type_name]
            else:
                clsname = f'REGEX_{len(self.regex_to_clsname)}'
                self.regex_to_clsname[type_name] = clsname
                self.sub_rules[clsname] = type_name
                self.spec.clsname_to_readable_syntax[clsname] = type_name
            readable_syntax = type_name
        else:
            clsname = f'{type.type_name.upper()}'
            readable_syntax = clsname
        return clsname, readable_syntax

    def process_short_option_without_value_when_combination_allowed(
        self,
        clsname,
        single_option,
        OptionPair_key,
        add_option_to_OptionPair=True):
        # In linux, ShortOptionWithoutValue can be combined with a single dash. -y -a can be combined as -ya
        # if allow_CombinedShortOption, short option is handle in self.process_combined_short_option()
        # no dash is need in the option_key. The dash is handle in self.process_combined_short_option()
        single_option_content = f'option_key="{single_option.option}"'
        readable_syntax = f"{single_option.option}"
        if add_option_to_OptionPair:
            if OptionPair_key is None:
                OptionPair_key = single_option.dash + single_option.option
            self.OptionPair_key_to_option_keys_and_readable_syntax[
                OptionPair_key].append(
                    (single_option.dash + single_option.option,
                     single_option.dash + single_option.option))
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        self.sub_rules[clsname] = single_option_content
        return None, None

    def process_single_option(self,
                              single_option,
                              OptionPair_key=None,
                              add_option_to_OptionPair=True):
        if single_option.dash == '-':
            if single_option.type:
                clsname = f'ShortOptionWithValue_{len(self.ShortOptionWithValue_clsnames)}'
                self.ShortOptionWithValue_clsnames.append(clsname)
            else:
                clsname = f'ShortOptionWithoutValue_{len(self.ShortOptionWithoutValue_clsnames)}'
                self.ShortOptionWithoutValue_clsnames.append(clsname)
        else:
            if single_option.type:
                clsname = f'LongOptionWithValue_{len(self.LongOptionWithValue_clsnames)}'
                self.LongOptionWithValue_clsnames.append(clsname)
            else:
                clsname = f'LongOptionWithoutValue_{len(self.LongOptionWithoutValue_clsnames)}'
                self.LongOptionWithoutValue_clsnames.append(clsname)

        # In linux, ShortOptionWithoutValue can be combined with a single dash. -y -a can be combined as -ya
        if clsname.startswith('ShortOptionWithoutValue'):
            # if allow_CombinedShortOption, short option is handle in self.process_combined_short_option()
            if self.allow_CombinedShortOption:
                return self.process_short_option_without_value_when_combination_allowed(
                    clsname, single_option, OptionPair_key)

        option_key = single_option.dash + single_option.option
        # treat it as a keyword, so we need to add word boundary. But we can't use
        # r'\b' since '-' does not belong to '\w'. So we use negative look-behind
        # r'(?<!(\w|\-))' and negative look-ahead r'(?!(\w|\-))'. That is we don't
        # allow have '\w' or '-' before or after the keyword
        option_key = r'/(?<!(\w|\-))' + re.escape(option_key) + r'(?!(\w|\-))/'
        single_option_content = f'option_key={option_key}'
        readable_syntax = f"{single_option.dash + single_option.option}"

        # when the single option has value and/or multi_values
        if single_option.type:
            clsname_type, readable_syntax_type = self.process_type(
                single_option.type)
            if single_option.multi_values:
                # the multi "+" is enough since it is already "optional"
                single_option_content += f' ("=" | /[ \t]+/) value+={clsname_type}'
                if single_option.multi_times:
                    readable_syntax += f'+=<{readable_syntax_type}>+'
                else:
                    readable_syntax += f'=<{readable_syntax_type}>+'
            else:
                single_option_content += f' ("=" | /[ \t]+/) value={clsname_type}'
                if single_option.multi_times:
                    readable_syntax += f'+=<{readable_syntax_type}>'
                else:
                    readable_syntax += f'=<{readable_syntax_type}>'

        if add_option_to_OptionPair:
            if OptionPair_key is None:
                OptionPair_key = single_option.dash + single_option.option
            self.OptionPair_key_to_option_keys_and_readable_syntax[
                OptionPair_key].append(
                    (single_option.dash + single_option.option,
                     readable_syntax))

        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        self.spec.concrete_specs[clsname] = 'nws'
        self.sub_rules[clsname] = single_option_content

        # if it is a ShortOptionWithoutValue, we will handle it in option session since it should be matched before combined short options
        if clsname.startswith('ShortOptionWithValue'):
            self.all_short_option_with_value.append(clsname)
            self.all_short_option_with_value_readable_syntax.append(
                readable_syntax)
            return None, None

        return clsname, readable_syntax

    def process_placeholder(self, placeholder):
        assert placeholder.value in self.OptionSession_name_to_clsnames, "Non-options placeholder is still there, please check"
        clsname = self.OptionSession_name_to_clsnames[placeholder.value]
        return clsname, self.spec.clsname_to_readable_syntax[clsname]

    def process_collection(self, collection):
        if collection.optional_collection:
            collection_type = 'OptionalCollection'
            lowercase_coll_type = 'optional_collection'
        else:
            collection_type = 'OneMustPresentCollection'
            lowercase_coll_type = 'one_must_present_collection'

        statements = getattr(collection, lowercase_coll_type).statements
        specification = getattr(collection, lowercase_coll_type).specification
        return self.process_collection_util(collection_type, statements,
                                            specification)

    def process_collection_util(self,
                                collection_type,
                                statements,
                                specification=None,
                                OptionPair_key=None,
                                add_option_to_OptionPair=True):
        # construct the clsname of the collection
        num = getattr(self, "num_" + collection_type + 's')
        clsname = f"{collection_type}_{num}"
        setattr(self, "num_" + collection_type + 's', num + 1)
        choices = []
        readable_syntax = []
        for i, statement in enumerate(statements):
            statement_clsname, statement_readable_syntax = self.process_statement(
                statement=statement,
                OptionPair_key=OptionPair_key,
                add_option_to_OptionPair=add_option_to_OptionPair)

            if statement_clsname is None:
                continue
            choices.append(f"statement{i}={statement_clsname}")
            readable_syntax.append(statement_readable_syntax)

        if not choices:
            return None, None

        content = '(' + ' | '.join(choices) + ')'
        self.sub_rules[clsname] = content
        readable_syntax = f"{' | '.join(readable_syntax)}"
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        if specification:
            self.spec.textx_specs_and_clsname_ref.append(
                (specification, clsname, None))

        return clsname, readable_syntax

    def process_element(self,
                        element,
                        OptionPair_key=None,
                        add_option_to_OptionPair=True):
        element_type = self.get_element_type(element)
        multi = element.multi
        if element_type == 'single_option':
            clsname, readable_syntax = getattr(self, f"process_{element_type}")(
                getattr(element,
                        element_type), OptionPair_key, add_option_to_OptionPair)
        else:
            clsname, readable_syntax = getattr(self, f"process_{element_type}")(
                getattr(element, element_type))
        if not clsname:
            return None, None

        if multi:
            # when element_type is type, the return clsname is always the same for the same type. So we
            # need to differentiate them
            if element_type == 'type':
                if not hasattr(self, f"num_{clsname}"):
                    setattr(self, f"num_{clsname}", 0)
                num = getattr(self, f"num_{clsname}")
                clsname_multi = f'{clsname}_{num}_Multi'
                setattr(self, f"num_{clsname}", num + 1)
            else:
                clsname_multi = clsname + '_Multi'
            content = f"{element_type}s{multi}={clsname}"
            self.sub_rules[clsname_multi] = content
            readable_syntax = f"({readable_syntax}){multi}"
            self.spec.clsname_to_readable_syntax[
                clsname_multi] = readable_syntax
            clsname = clsname_multi
        return clsname, readable_syntax

    def process_statement(self,
                          statement,
                          OptionPair_key=None,
                          add_option_to_OptionPair=True):
        if statement.sequential_statement:
            statement_type = 'SequentialStatement'
            elements = statement.sequential_statement.elements
        else:
            statement_type = 'UnorderedStatement'
            elements = statement.unordered_statement.elements
        return self.process_statement_util(statement_type, elements,
                                           OptionPair_key,
                                           add_option_to_OptionPair)

    def process_statement_util(self,
                               statement_type,
                               elements,
                               OptionPair_key=None,
                               add_option_to_OptionPair=True):
        num = getattr(self, "num_" + statement_type + 's')
        clsname = f'{statement_type}_{num}'
        setattr(self, "num_" + statement_type + 's', num + 1)

        content = []
        readable_syntax = []
        for i, element in enumerate(elements):
            element_clsname, element_readable_syntax = self.process_element(
                element, OptionPair_key, add_option_to_OptionPair)
            if not element_clsname:
                continue
            # OptionalCollection or OptionSession
            if "OptionalCollection" in element_clsname or "OptionSession" in element_clsname:
                element_clsname_usage = element_clsname + "?"
            else:
                element_clsname_usage = element_clsname
            content.append(f"element{i}={element_clsname_usage}")
            readable_syntax.append(element_readable_syntax)

        if not content:
            return None, None

        content = ' '.join(content)
        readable_syntax = ' '.join(readable_syntax)

        if statement_type == 'UnorderedStatement':
            content = '(' + content + ')#'
            readable_syntax = '(' + readable_syntax + ')UnOrdered'
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_unordered_statement(self, unordered_statement):
        return self.process_statement_util("UnorderedStatement",
                                           unordered_statement.elements)

    def translate(self,
                  eman,
                  save_to_file=False,
                  save_dir=None,
                  save_to_db=False,
                  overwrite_db_if_exsits=False,
                  allow_CombinedShortOption=True,
                  CombinedShortOption_required_dash=True):
        self.reset(allow_CombinedShortOption, CombinedShortOption_required_dash)
        self.eman = self.pre_process(eman)

        model = self.metamodel.model_from_str(self.eman)
        synopsis = model.synopsis
        if model.options:
            self.process_options_session(model.options)

        if save_to_file:
            file_name = os.path.join(save_dir, f'{synopsis.command}.tx')

        self.tx_syntax += f'//AUTO GENERATED FILE\n// DSL for command "{synopsis.command}"\n\n'

        # treat it as a keyword, so we need to add word boundary. But we can't use
        # r'\b' since '-' does not belong to '\w'. So we use negative look-behind
        # r'(?<!(\w|\-))' and negative look-ahead r'(?!(\w|\-))'. That is we don't
        # allow have '\w' or '-' before or after the keyword
        command = r'/(?<!(\w|\-))' + re.escape(
            synopsis.command) + r'(?!(\w|\-))/'
        self.tx_syntax += f'Main_Rule:\n\tcommand={command} '
        statement = synopsis.statement
        statement_clsname, _ = self.process_statement(statement)
        self.tx_syntax += f"statement={statement_clsname}"
        self.tx_syntax += '\n;'

        self.spec.concrete_specs[
            'OptionPair_key_to_option_keys_and_readable_syntax'] = self.OptionPair_key_to_option_keys_and_readable_syntax
        # process specification and explanation
        self.spec.process_textx_specs()
        if model.explanation:
            self.spec.process_explanation(model.explanation)

        # append each sub_rule
        while 1:
            try:
                clsname, content = self.sub_rules.popitem(last=False)
                # check whether there is a nws spec for the clsname
                nws = False
                if clsname in self.spec.concrete_specs and 'nws' in self.spec.concrete_specs[
                        clsname]:
                    nws = True

                # if nws is True, then we can not skip the white space.
                # for example, tensorflow==0.1.19 is valid while
                # tensorflow== 0.1.19 is not. But we allow white space at the
                # beginning or at the end. So we need to add /[ \t]*/- manually
                # check http://textx.github.io/textX/stable/grammar/#match-suppression
                if nws:
                    self.tx_syntax += f'\n\n{clsname}[noskipws]:\n\t/[ \t]*/- '
                else:
                    self.tx_syntax += f'\n\n{clsname}:\n\t'
                self.tx_syntax += content
                if nws:
                    self.tx_syntax += ' /[ \t]*/-'
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
            command = Command(command_name, self.tx_syntax,
                              clsname_to_readable_syntax, concrete_specs,
                              explanation, eman)
            self.store.addcommand(command, overwrite=overwrite_db_if_exsits)
        return self.tx_syntax + BASETYPE


class Specification:

    def __init__(self):
        '''
        // Word2 is Word that can start with 'tag:' which may followed by dash or double dashes
        Word2:
            /(tag:)?(-(-)?)?[^\d\W][\w-]*/
        ;

        //complete format of the concrete_spec:
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

        self.sub_commands = []
        self.textx_specs_and_clsname_ref = []
        self.concrete_specs = defaultdict(dict)
        self.clsname_to_readable_syntax = {}
        self.explanation = {}

    @staticmethod
    def start_and_end_with_quotes(string):
        if string.startswith('"') or string.startswith("'") or string.endswith(
                "'") or string.endswith('"'):
            return True
        return False

    # process 'after', 'before', 'always', 'mutex'
    # `tpy` is one of 'after', 'before', 'always', 'mutex'
    def process_after_before_always_must(self, spec, typ, fired_ref):
        item = getattr(spec, typ).item
        if typ not in self.concrete_specs[fired_ref]:
            self.concrete_specs[fired_ref][typ] = {}
        if item.all_must_present_item:
            for ref in item.all_must_present_item.refs:
                if 'all_must_present' not in self.concrete_specs[fired_ref][
                        typ]:
                    self.concrete_specs[fired_ref][typ]['all_must_present'] = []
                assert ref in self.sub_commands or ref in self.concrete_specs[
                    'OptionPair_key_to_option_keys_and_readable_syntax'], \
                        "reference in Specification has to be either a subcommand or a OptionPair key"
                self.concrete_specs[fired_ref][typ]['all_must_present'].append(
                    ref)
        else:
            for ref in item.one_must_present_item.refs:
                if 'one_must_present' not in self.concrete_specs[fired_ref][
                        typ]:
                    self.concrete_specs[fired_ref][typ]['one_must_present'] = []
                assert ref in self.sub_commands or ref in self.concrete_specs[
                    'OptionPair_key_to_option_keys_and_readable_syntax'], \
                        "reference in Specification has to be either a subcommand or a OptionPair key"
                self.concrete_specs[fired_ref][typ]['one_must_present'].append(
                    ref)

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
                        self.message_vars[var]
                    ), "Only variable enclosed by `'` or `\"` is allowed in options sesstion"
                    string = self.message_vars[var]
                else:
                    string = key_value.value.string
                self.concrete_specs[clsname]['info'][key_value.key] = string

    def process_textx_specs(self):
        for spec, clsname, ref in self.textx_specs_and_clsname_ref:
            # when ref is not None, it means we are precessing the specification in the e-option session
            if ref is not None:
                assert ref not in self.concrete_specs, f"{ref} already exists, please use a different OptionPair_key"
                for typ in ('after', 'before', 'always', 'mutex'):
                    if getattr(spec, typ):
                        if ref not in self.concrete_specs:
                            self.concrete_specs[ref] = {}
                        self.process_after_before_always_must(spec, typ, ref)
            if spec.info:
                self.process_info(spec, clsname)
            if spec.nws:
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                self.concrete_specs[clsname]['nws'] = True

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
                    elif re.match(
                            r'[\w-]',
                            v[-1]) and i < len(pair.values) - 1 and pair.values[
                                i + 1].value[0] not in '\t\n ':
                        values.append(v + ' ')
                    else:
                        values.append(v)
                value = ''.join(values)
                for key in keys:
                    self.explanation[key] = value
