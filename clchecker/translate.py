from textx import metamodel_from_file
from textx.model import get_children_of_type
from collections import OrderedDict, defaultdict, namedtuple, deque
from clchecker.constants import BASETYPE
from clchecker.store import Command, Store
import config
import os
import re

ExplanationItem = namedtuple(
    "ExplanationItem",
    ["plaintext", "plain_option_syntax", "explanation_values"])


class Translator():
    """
    translate an eman file to textx grammer. Each eman file defines a DSL which guides how a command should be used.
    """

    def __init__(self, metamodel, store=None):
        self.metamodel = metamodel
        self.store = store

    def reset(
        self,
        allow_CombinedShortOption=True,
        allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=False):
        self.options_session = None
        self.options_session_readable_syntax = None
        self.synop_variables = dict()

        self.sub_rules = OrderedDict()
        self.num_OptionalCollections = 0
        self.num_OneMustPresentCollections = 0
        self.num_SequentialStatements = 0
        self.num_UnorderedStatements = 0
        self.eman = None
        self.spec = Specification()
        self.num_SubCommands = 0
        self.num_String = 0
        self.num_Value = 0
        self.num_OptionSessionCollections = 0
        self.num_OptionSessions = 0
        self.num_OptionItem = 0
        self.num_OptionSyntax = 0
        self.OptionSession_name_to_clsnames = {}
        self.OptionSession_name_to_var_clsnames = {}

        self.allow_CombinedShortOption = allow_CombinedShortOption
        self.allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption = allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption
        self.regex_to_clsname = {}

        self.num_ShortOptionWithoutValue = 0
        self.num_ShortOptionWithValue = 0
        self.num_ShortOptionWithValueNoLeftBoundary = 0
        self.num_LongOptionWithValue = 0
        self.num_LongOptionWithoutValue = 0

        # list of clsname list. The first index is option_session_index
        self.all_Sessions_ShortOptionWithoutValue_clsnames = []
        self.all_Sessions_ShortOptionWithoutValue_no_dash_option_key_clsnames = []
        self.all_Sessions_ShortOptionWithValue_clsnames = []
        self.all_Sessions_ShortOptionWithValue_no_dash_option_key_clsnames = []
        self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames = []
        self.all_Sessions_LongOptionWithValue_clsnames = []
        self.all_Sessions_LongOptionWithValue_no_dash_option_key_clsnames = []
        self.all_Sessions_LongOptionWithoutValue_clsnames = []
        self.all_Sessions_LongOptionWithoutValue_no_dash_option_key_clsnames = []
        self.all_Sessions_all_short_option_with_value = []
        self.all_Sessions_all_short_option_with_value_readable_syntax = []

        # OptionPair:
        #     key=Word2 (":" optional_collection=OptionalCollection? specification=Specification?)?
        # ;
        # this is an example of OptionPair `-d: [-d | --download-only]`. In the optional collection,
        # only one of `-d` or `download-only can appear`
        # we collect OptionPair_key_to_option_keys_and_readable_syntax to track whether an multiple option in the
        # OptionalCollection appear at the same time.
        self.OptionPair_key_to_option_keys_and_readable_syntax = defaultdict(
            list)

        # text that translated from the synop
        self.tx_syntax = ''

    def prepare_option_session(self):
        self.all_Sessions_ShortOptionWithoutValue_clsnames.append([])
        self.all_Sessions_ShortOptionWithoutValue_no_dash_option_key_clsnames.append([])
        self.all_Sessions_ShortOptionWithValue_clsnames.append([])
        self.all_Sessions_ShortOptionWithValue_no_dash_option_key_clsnames.append([])
        self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames.append([])
        self.all_Sessions_LongOptionWithValue_clsnames.append([])
        self.all_Sessions_LongOptionWithValue_no_dash_option_key_clsnames.append([])
        self.all_Sessions_LongOptionWithoutValue_clsnames.append([])
        self.all_Sessions_LongOptionWithoutValue_no_dash_option_key_clsnames.append([])
        self.all_Sessions_all_short_option_with_value.append([])
        self.all_Sessions_all_short_option_with_value_readable_syntax.append([])

    def process_allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption(
        self, option_session_index):
        assert self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames[option_session_index]
        readable_syntax = ' |\n'.join([
            self.spec.clsname_to_readable_syntax[clsname]
            for clsname in self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames[option_session_index]
        ])
        content = ' | '.join([
            f"choice{i}={clsname}" for i, clsname in enumerate(
                self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames[option_session_index])
        ])
        content = "(" + content + ")"
        clsname = f"AllShortOptionWithValueNoLeftBoundary{option_session_index}"
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_combined_short_option(self, option_session_index):
        """
        In linux, usually short options can be combined. For example apt-get -qqy install pkg.
        we need to create a rule to match this.
        """
        # sort clsnames so that "-qq" will be matched before "-q"
        self.all_Sessions_ShortOptionWithoutValue_clsnames[
            option_session_index].sort(key=lambda clsname: len(
                self.spec.clsname_to_readable_syntax[clsname]),
                                       reverse=True)

        readable_syntax = ''.join([
            self.spec.clsname_to_readable_syntax[clsname] for clsname in self.
            all_Sessions_ShortOptionWithoutValue_clsnames[option_session_index]
        ])

        content = ' | '.join([
            f"short_option_without_dash{i}={clsname}" for i, clsname in
            enumerate(self.all_Sessions_ShortOptionWithoutValue_clsnames[
                option_session_index])
        ])
        content = '(' + content + ')'
        clsname = f"ShortOptionWithoutDash_{option_session_index}"
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        clsname_at_the_end_content, readable_syntax_at_the_end = "", ""
        if self.allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption and self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames[option_session_index]:
            clsname_at_the_end, readable_syntax_at_the_end = self.process_allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption(
                option_session_index)
            clsname_at_the_end_content = f"short_option_with_value={clsname_at_the_end}?"
        clsname_comb = f"CombinedShortOption_{option_session_index}"

        content = f'"-" combined_short_options_without_dash+={clsname} {clsname_at_the_end_content}'
        readable_syntax_comb = "-(" + readable_syntax + f")+{readable_syntax_at_the_end}"
        self.spec.clsname_to_readable_syntax[
            clsname_comb] = readable_syntax_comb
        self.sub_rules[clsname_comb] = content
        self.spec.concrete_specs[clsname_comb]['nws'] = True

        clsname_multi = f"CombinedShortOption_Multi_{option_session_index}"
        self.sub_rules[clsname_multi] = f"CombinedShortOptions+={clsname_comb}"
        readable_syntax_multi = "(" + readable_syntax_comb + ")+"
        self.spec.clsname_to_readable_syntax[
            clsname_multi] = readable_syntax_multi
        return clsname_multi, readable_syntax_multi

    def process_traditional_usage(self):
        # kind of specical for "tar" command(old style). Used when specifying the "TRADITIONAL" keyword
        # tar [<TRADITIONAL>] [<options>] <bANY>*
        # https://www.gnu.org/software/tar/manual/tar.html
        short_options = [
            i for s in self.all_Sessions_ShortOptionWithValue_no_dash_option_key_clsnames
            for i in s
        ] + [
            i for s in self.all_Sessions_ShortOptionWithoutValue_no_dash_option_key_clsnames
            for i in s
        ]
        readable_syntax = ''.join([
            self.spec.clsname_to_readable_syntax[clsname]
            for clsname in short_options
        ])

        content = ' | '.join([
            f"short_option{i}={clsname}"
            for i, clsname in enumerate(short_options)
        ])
        clsname = f"TraditionalUsage"
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax

        clsname_arguments = 'TraditionalUsageArgument'
        if clsname_arguments not in self.sub_rules:
            # bANY or a-dash surrounded by whitespace or endofline
            content_arguments = 'bANY | /(?<=( |=|\t))\-(?=( |\t|$))/'
            self.sub_rules[clsname_arguments] = content_arguments
            self.spec.concrete_specs[clsname_arguments]['skipws'] = True

        clsname_multi = f'{clsname}_Muilt'
        content = f"short_options+={clsname} /[ \t]+|$/ arguments*={clsname_arguments}"
        readable_syntax_multi = f"({readable_syntax})+ argumements*"
        self.sub_rules[clsname_multi] = content
        self.spec.clsname_to_readable_syntax[clsname_multi] = readable_syntax_multi
        self.spec.concrete_specs[clsname_multi]['nws'] = True
        return clsname_multi, readable_syntax_multi

    def process_short_option_with_value(self, option_session_index):
        clsname = f"AllShortOptionWithValueAtOptionSession_{option_session_index}"
        # self.num_OptionSessions += 1
        content = ' | '.join([
            f'choice{i}={single_option}' for i, single_option in enumerate(
                self.
                all_Sessions_all_short_option_with_value[option_session_index])
        ])
        readable_syntax = '|\n'.join(
            self.all_Sessions_all_short_option_with_value_readable_syntax[option_session_index])
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

    def process_option_syntax(self, OptionPair_key, single_options,
                              option_variables):
        clsname = f'OptionSyntax_{self.num_OptionSyntax}'
        self.num_OptionSyntax += 1
        choices = []
        readable_syntax = []
        for i, single_option in enumerate(single_options):
            clsname_so, readable_syntax_so, option_key = self.process_single_option(
                single_option, OptionPair_key, option_variables)
            if not OptionPair_key:
                OptionPair_key = option_key
            if not clsname_so:
                continue
            choices.append(f"choice{i}={clsname_so}")
            readable_syntax.append(readable_syntax_so)
        if not choices:
            return None, None, OptionPair_key
        content = ' | '.join(choices)
        readable_syntax = '|\n'.join(readable_syntax)
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        assert OptionPair_key is not None, "OptionPair_key is None"
        return clsname, readable_syntax, OptionPair_key

    def process_option_item(self, OptionPair_key, option_item,
                            option_variables):
        clsname = f"OptionItem_{self.num_OptionItem}"
        self.num_OptionItem += 1
        if option_item.option_syntax and option_item.option_syntax.single_options:
            clsname_os, readable_syntax_os, OptionPair_key = self.process_option_syntax(
                OptionPair_key, option_item.option_syntax.single_options,
                option_variables)
        else:
            if not option_item.option_text.single_options:
                raise ValueError(
                    f'"{option_item.option_text.plaintext}" is not a valid option syntax. You probably need to have an e-syntax'
                )
            clsname_os, readable_syntax_os, OptionPair_key = self.process_option_syntax(
                OptionPair_key, option_item.option_text.single_options,
                option_variables)

        start = option_item.option_text._tx_position
        end = option_item.option_text._tx_position_end
        plaintext = self.eman[start:end]

        if option_item.option_syntax and option_item.option_syntax.single_options:
            start = option_item.option_syntax._tx_position
            end = option_item.option_syntax._tx_position_end
            plain_option_syntax = self.eman[start:end]
        else:
            plain_option_syntax = None

        if option_item.option_specification and option_item.option_specification.specification:
            self.spec.textx_specs_and_clsname_and_ref.append(
                (option_item.option_specification.specification, clsname,
                 OptionPair_key))

        self.spec.explanation[OptionPair_key] = ExplanationItem(
            plaintext, plain_option_syntax, option_item.explanation_values)

        if not clsname_os:
            return None, None, OptionPair_key
        self.sub_rules[clsname] = f"item={clsname_os}"
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax_os
        return clsname, readable_syntax_os, OptionPair_key

    def process_option_session_variables(self, variables):
        option_variables = {}
        if variables and variables.vars:
            for pair in variables.vars:
                clsname_var, readable_syntax_var = self.process_statement(
                    pair.statement,
                    session='Option',
                    variables=option_variables)
                option_variables[pair.varname] = clsname_var
        return option_variables

    def process_options_session(self, options):
        for option_session_index, option in enumerate(options):
            self.prepare_option_session()
            clsname = f"OptionSession_{option_session_index}"
            option_variables = self.process_option_session_variables(
                option.variables)
            readable_syntax = []
            choices = []
            if option.pairs:
                for i, pair in enumerate(option.pairs):
                    clsname_oi, readable_syntax_oi, readable_syntax_oi = self.process_option_item(
                        pair.key, pair.option_item, option_variables)
                    if clsname_oi is not None and readable_syntax_oi is not None:
                        readable_syntax.append(readable_syntax_oi)
                        choices.append(f"choice{i}={clsname_oi}")

                pre_choices = []
                pre_readable_syntax = []
                i += 1

                # short option with value has the top priority, so it should put at the very beginning
                if self.all_Sessions_all_short_option_with_value[
                        option_session_index]:
                    clsname_short_value, readable_syntax_short_value = self.process_short_option_with_value(
                        option_session_index)
                    pre_choices.append(f"choice{i}={clsname_short_value}")
                    pre_readable_syntax.append(readable_syntax_short_value)
                    i += 1

                # CombinedShortOption should be put after short option with value, but before others
                if self.allow_CombinedShortOption and self.all_Sessions_ShortOptionWithoutValue_clsnames[
            option_session_index]:
                    comb_clsname, comb_readable_syntax = self.process_combined_short_option(
                        option_session_index)
                    pre_choices.append(f"choice{i}={comb_clsname}")
                    pre_readable_syntax.append(comb_readable_syntax)
                choices = pre_choices + choices
                readable_syntax = pre_readable_syntax + readable_syntax
            assert len(
                choices) > 0, f"No choice in option session {option.name}"
            clsname_choice = f"AllOptionChoice_{option_session_index}"
            readable_syntax = ' |\n'.join(readable_syntax)
            self.sub_rules[clsname_choice] = '(' + ' | '.join(choices) + ")"
            self.spec.clsname_to_readable_syntax[
                clsname_choice] = readable_syntax

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
            'collection': False,
            'string': False,
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

    def process_string(self, string):
        clsname = f'String_{self.num_String}'
        self.num_String += 1
        content = f'"{string}"'
        self.sub_rules[clsname] = content
        self.spec.clsname_to_readable_syntax[clsname] = content
        return clsname, content

    def process_value(self, sub_command):
        clsname = f'Value_{self.num_Value}'
        readable_syntax = f"{sub_command.value}"
        self.num_Value += 1
        self.sub_rules[clsname] = f'value="{sub_command.value}"'
        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        return clsname, readable_syntax

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
        self.spec.sub_commands_to_clsname[sub_command.value] = clsname

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
            clsname = f'{type.type_name}'
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

    def process_single_option(self, single_option, OptionPair_key, variables):
        if single_option.dash == '-':
            if single_option.statement:
                clsname = f'ShortOptionWithValue_{self.num_ShortOptionWithValue}'
                clsname_no_dash_option_key = f'ShortOptionWithValue_option_key_{self.num_ShortOptionWithValue}'
                self.num_ShortOptionWithValue += 1
                self.all_Sessions_ShortOptionWithValue_clsnames[-1].append(
                    clsname)
                self.all_Sessions_ShortOptionWithValue_no_dash_option_key_clsnames[-1].append(
                    clsname_no_dash_option_key)
            else:
                clsname = f'ShortOptionWithoutValue_{self.num_ShortOptionWithoutValue}'
                clsname_no_dash_option_key = f'ShortOptionWithoutValue_option_key_{self.num_ShortOptionWithoutValue}'
                self.num_ShortOptionWithoutValue += 1
                self.all_Sessions_ShortOptionWithoutValue_clsnames[-1].append(
                    clsname)
                self.all_Sessions_ShortOptionWithoutValue_no_dash_option_key_clsnames[-1].append(
                    clsname_no_dash_option_key)
        else:
            if single_option.statement:
                clsname = f'LongOptionWithValue_{self.num_LongOptionWithValue}'
                clsname_no_dash_option_key = f'LongOptionWithValue_option_key_{self.num_LongOptionWithValue}'
                self.num_LongOptionWithValue += 1
                self.all_Sessions_LongOptionWithValue_clsnames[-1].append(
                    clsname)
                self.all_Sessions_LongOptionWithValue_no_dash_option_key_clsnames[-1].append(
                    clsname_no_dash_option_key)
            else:
                clsname = f'LongOptionWithoutValue_{self.num_LongOptionWithoutValue}'
                clsname_no_dash_option_key = f'LongOptionWithoutValue_option_key_{self.num_LongOptionWithoutValue}'
                self.num_LongOptionWithoutValue += 1
                self.all_Sessions_LongOptionWithoutValue_clsnames[-1].append(
                    clsname)
                self.all_Sessions_LongOptionWithoutValue_no_dash_option_key_clsnames[-1].append(
                    clsname_no_dash_option_key)

        # kind of special for traditional usage
        self.sub_rules[clsname_no_dash_option_key] = f'option_key="{single_option.option}"'
        self.spec.clsname_to_readable_syntax[clsname_no_dash_option_key] = single_option.option
        self.spec.clsname_to_readable_syntax[clsname_no_dash_option_key] = single_option.option
        self.spec.concrete_specs[clsname_no_dash_option_key]['nws'] = True
        self.spec.concrete_specs[clsname_no_dash_option_key]['leftspace'] = False
        self.spec.concrete_specs[clsname_no_dash_option_key]['rightspace'] = False

        if OptionPair_key is None:
            OptionPair_key = f"OPK_{single_option.dash + single_option.option}"
        # In linux, ShortOptionWithoutValue can be combined with a single dash. -y -a can be combined as -ya
        if clsname.startswith('ShortOptionWithoutValue'):
            # if allow_CombinedShortOption, short option is handle in self.process_combined_short_option()
            if self.allow_CombinedShortOption:
                clsname, readable_syntax = self.process_short_option_without_value_when_combination_allowed(
                    clsname, single_option, OptionPair_key)
                return clsname, readable_syntax, OptionPair_key

        option_key = single_option.dash + single_option.option
        # treat it as a keyword, so we need to add word boundary. But we can't use
        # r'\b' since '-' does not belong to '\w'. So we use negative look-behind
        # r'(?<!(\w|\-))' and negative look-ahead r'(?!(\w|\-))'. That is we don't
        # allow having '\w' or '-' before or after the keyword
        option_key_boundary = r'/(?<!(\w|\-))' + re.escape(
            option_key) + r'(?!(\w|\-))/'
        single_option_content = f'option_key={option_key_boundary}'
        readable_syntax = f"{single_option.dash + single_option.option}"

        # when the single option has value and/or multi_values
        readable_syntax_statement=''
        if single_option.statement:
            clsname_statement, readable_syntax_statement = self.process_statement(
                single_option.statement, 'Option', variables, nws=False)

            single_option_content += f' (/(?<!( |\t))=(?!( |\t))/ | /[ \t]+/) value={clsname_statement}'
            readable_syntax_statement = "=<" + readable_syntax_statement + ">"
        if single_option.multi_times:
            readable_syntax += '+' + readable_syntax_statement
        else:
            readable_syntax += readable_syntax_statement

        self.OptionPair_key_to_option_keys_and_readable_syntax[
            OptionPair_key].append(
                (single_option.dash + single_option.option, readable_syntax))

        self.spec.clsname_to_readable_syntax[clsname] = readable_syntax
        self.spec.concrete_specs[clsname] = 'nws'
        self.sub_rules[clsname] = single_option_content

        # if it is a ShortOptionWithValue, we will handle it in option session since it should be matched before combined short options
        if clsname.startswith('ShortOptionWithValue'):
            self.all_Sessions_all_short_option_with_value[-1].append(clsname)
            self.all_Sessions_all_short_option_with_value_readable_syntax[-1].append(
                readable_syntax)

            # it is special for "tar"-like command.
            # `tar -cvf tecmint-14-09-12.tar /home/tecmint/`
            # Here -f=<PATH> is a shortoption with value option. But it can be put at the end of combined short options
            if self.allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption:
                start = len(r'option_key=/(?<!(\w|\-))')
                assert single_option_content[:
                                             start] == r'option_key=/(?<!(\w|\-))'
                # don't include option.dash in the option_key
                if single_option.dash:
                    start += len(re.escape(single_option.dash))
                content_no_left_boundary = 'option_key=/' + single_option_content[
                    start:]
                clsname_no_left_boundary = "NoLeftBoundary" + clsname
                self.sub_rules[
                    clsname_no_left_boundary] = content_no_left_boundary
                self.spec.clsname_to_readable_syntax[
                    clsname_no_left_boundary] = readable_syntax
                self.all_Sessions_ShortOptionWithValueNoLeftBoundary_clsnames[-1].append(
                    clsname_no_left_boundary)
                self.spec.concrete_specs[clsname_no_left_boundary]['nws'] = True
                self.spec.concrete_specs[clsname_no_left_boundary][
                    'leftspace'] = False

            return None, None, OptionPair_key

        return clsname, readable_syntax, OptionPair_key

    def process_placeholder(self, placeholder, variables):
        if placeholder.value in self.OptionSession_name_to_clsnames:
            clsname = self.OptionSession_name_to_clsnames[placeholder.value]
        elif placeholder.value == 'TRADITIONAL':
            return self.process_traditional_usage()
        elif placeholder.value in variables:
            clsname = variables[placeholder.value]
        else:
            raise ValueError(f"variable '{placeholder.value}' is not defined")
        return clsname, self.spec.clsname_to_readable_syntax[clsname]

    def process_collection(self, collection, session, variables):
        if collection.optional_collection:
            collection_type = 'OptionalCollection'
            lowercase_coll_type = 'optional_collection'
        else:
            collection_type = 'OneMustPresentCollection'
            lowercase_coll_type = 'one_must_present_collection'

        statements = getattr(collection, lowercase_coll_type).statements
        specification = getattr(collection, lowercase_coll_type).specification
        return self.process_collection_util(collection_type, statements,
                                            session, variables, specification)

    def process_collection_util(self, collection_type, statements, session,
                                variables, specification):
        # construct the clsname of the collection
        num = getattr(self, "num_" + collection_type + 's')
        clsname = f"{collection_type}_{num}"
        setattr(self, "num_" + collection_type + 's', num + 1)
        choices = []
        readable_syntax = []
        for i, statement in enumerate(statements):
            statement_clsname, statement_readable_syntax = self.process_statement(
                statement, session, variables)

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
            self.spec.textx_specs_and_clsname_and_ref.append(
                (specification, clsname, None))

        return clsname, readable_syntax

    def process_element(self, element, session, variables):
        element_type = self.get_element_type(element)
        assert session in (
            'Option',
            'Synopsis'), '"Session" can only be "Option" or "Synopsis"'

        multi = element.multi
        if element_type == "placeholder":
            clsname, readable_syntax = self.process_placeholder(
                getattr(element, element_type), variables)
        elif element_type in ("collection", "unordered_statement"):
            clsname, readable_syntax = getattr(self, f"process_{element_type}")(
                getattr(element, element_type), session, variables)
        elif element_type == 'sub_command':
            if session == "Option":
                # in Option Session, we don't allow sub_command as element type. We use value instead
                clsname, readable_syntax = self.process_value(
                    element.sub_command)
            else:
                clsname, readable_syntax = self.process_sub_command(
                    element.sub_command)
        else:
            clsname, readable_syntax = getattr(self, f"process_{element_type}")(
                getattr(element, element_type))

        if multi:
            # when element_type is type, the return clsname is always the same for the same type. So we
            # need to differentiate them
            if element_type in ('type', 'placeholder'):
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

    def process_statement(self, statement, session, variables, nws=None):
        if statement.sequential_statement:
            statement_type = 'SequentialStatement'
            elements = statement.sequential_statement.elements
        else:
            statement_type = 'UnorderedStatement'
            elements = statement.unordered_statement.elements
        return self.process_statement_util(statement_type, elements, session,
                                           variables, nws)

    def process_statement_util(self, statement_type, elements, session,
                               variables, nws=None):
        num = getattr(self, "num_" + statement_type + 's')
        clsname = f'{statement_type}_{num}'
        setattr(self, "num_" + statement_type + 's', num + 1)

        content = []
        readable_syntax = []
        for i, element in enumerate(elements):
            element_clsname, element_readable_syntax = self.process_element(
                element, session, variables)
            element_clsname_usage = element_clsname
            if "OptionalCollection" in element_clsname:
                element_clsname_usage = element_clsname + "?"
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
        if nws is not None:
            if nws:
                self.spec.concrete_specs[clsname]['nws'] = True
            else:
                self.spec.concrete_specs[clsname]['skipws'] = True

        return clsname, readable_syntax

    def process_unordered_statement(self, unordered_statement):
        return self.process_statement_util("UnorderedStatement",
                                           unordered_statement.elements)
    def process_rules(self, rules):
        for rule_pair in rules:
            key, specification = rule_pair.key, rule_pair.specification
            self.spec.textx_specs_and_clsname_and_ref.append((specification, None, key))

    def translate(
        self,
        eman,
        save_to_file=False,
        save_dir=None,
        save_to_db=False,
        overwrite_db_if_exsits=False,
        allow_CombinedShortOption=True,
        allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption=False):
        self.reset(
            allow_CombinedShortOption,
            allow_ShortOptionWithValue_at_the_end_of_CombinedShortOption)
        self.eman = eman

        model = self.metamodel.model_from_str(self.eman)
        synopsis = model.synopsis
        if model.options:
            self.process_options_session(model.options)

        if synopsis.variables and synopsis.variables.vars:
            for pair in synopsis.variables.vars:
                clsname_var, readable_syntax_var = self.process_statement(
                    pair.statement, "Synopsis", self.synop_variables)
                self.synop_variables[pair.varname] = clsname_var

        if save_to_file:
            file_name = os.path.join(save_dir, f'{synopsis.command.value}.tx')

        self.tx_syntax += f'//AUTO GENERATED FILE\n// DSL for command "{synopsis.command.value}"\n\n'

        command_clsname, _ = self.process_sub_command(synopsis.command)
        self.tx_syntax += f'Main_Rule:\n\tcommand={command_clsname} '
        statement = synopsis.statement
        statement_clsname, _ = self.process_statement(statement, "Synopsis",
                                                      self.synop_variables)
        self.tx_syntax += f"statement={statement_clsname}"
        self.tx_syntax += '\n;'

        if model.rules:
            self.process_rules(model.rules.rules)

        self.spec.concrete_specs[
            'OptionPair_key_to_option_keys_and_readable_syntax'] = self.OptionPair_key_to_option_keys_and_readable_syntax
        # process specification and explanation
        self.spec.process_textx_specs()
        self.spec.process_explanation_item()
        if model.explanation:
            self.spec.process_explanation_session(model.explanation)

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
                    leftspace = "/[ \t]*/- "
                    if 'leftspace' in self.spec.concrete_specs[
                            clsname] and self.spec.concrete_specs[clsname][
                                'leftspace'] is False:
                        leftspace = ''
                    self.tx_syntax += f'\n\n{clsname}[noskipws]:\n\t{leftspace}'
                # TODO: add skipws or noskipws to each rule
                elif clsname in self.spec.concrete_specs and 'skipws' in self.spec.concrete_specs[
                        clsname]:
                    self.tx_syntax += f'\n\n{clsname}[skipws]:\n\t'
                else:
                    self.tx_syntax += f'\n\n{clsname}:\n\t'
                self.tx_syntax += content
                if nws:
                    rightspace = ' /[ \t]*/-'
                    if 'rightspace' in self.spec.concrete_specs[
                            clsname] and self.spec.concrete_specs[clsname][
                                'rightspace'] is False:
                        rightspace = ''
                    self.tx_syntax += rightspace
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
            command_name = synopsis.command.value
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

        self.sub_commands_to_clsname = {}
        self.textx_specs_and_clsname_and_ref = []
        self.concrete_specs = defaultdict(dict)
        self.clsname_to_readable_syntax = {}
        self.explanation = {}
        self.concrete_specs['explanation_key_to_ExplanationPair_key'] = {}

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
                if ref not in self.sub_commands_to_clsname.keys():
                    if f"OPK_{ref}" in self.concrete_specs[
                            'OptionPair_key_to_option_keys_and_readable_syntax']:
                        ref = f"OPK_{ref}"
                    else:
                        raise ValueError(
                            f"reference in Specification '{ref}' has to be either a subcommand or the first option in a option_syntax"
                        )
                self.concrete_specs[fired_ref][typ]['all_must_present'].append(
                    ref)
        else:
            for ref in item.one_must_present_item.refs:
                if 'one_must_present' not in self.concrete_specs[fired_ref][
                        typ]:
                    self.concrete_specs[fired_ref][typ]['one_must_present'] = []
                if ref not in self.sub_commands_to_clsname.keys():
                    if f"OPK_{ref}" in self.concrete_specs[
                            'OptionPair_key_to_option_keys_and_readable_syntax']:
                        ref = f"OPK_{ref}"
                    else:
                        raise ValueError(
                            f"reference in Specification '{ref}' has to be either a subcommand or the first option in a option_syntax"
                        )
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
        self.concrete_specs['option_keys_to_OptionPair_key'] = {}
        for OptionPair_key, option_keys_readable_syntaxes in self.concrete_specs[
                "OptionPair_key_to_option_keys_and_readable_syntax"].items():
            for option_key, _ in option_keys_readable_syntaxes:
                self.concrete_specs['option_keys_to_OptionPair_key'][
                    option_key] = OptionPair_key

        for spec, clsname, ref in self.textx_specs_and_clsname_and_ref:
            # when ref is not None, it means we are precessing the specification in the e-option session
            if ref is not None:
                assert ref not in self.concrete_specs, f"{ref} already exists, please use a different OptionPair_key"
                for typ in ('after', 'before', 'always', 'mutex'):
                    if getattr(spec, typ):
                        if ref not in self.concrete_specs:
                            self.concrete_specs[ref] = {}
                        self.process_after_before_always_must(spec, typ, ref)
            if ref is None:
                assert clsname is not None, f"clsname can't be None when ref is None"
            if spec.info:
                self.process_info(spec, clsname)
            if spec.nws:
                if clsname not in self.concrete_specs:
                    self.concrete_specs[clsname] = {}
                self.concrete_specs[clsname]['nws'] = True

    @staticmethod
    def process_explanation_values(explanation_values):
        values = []
        for i in range(len(explanation_values)):
            v = explanation_values[i].value
            if v.endswith('<br/>'):
                values.append(v[:-5])
                values.append('\n')
            elif v.endswith('<br />'):
                values.append(v[:-6])
                values.append('\n')
            elif re.match(
                    r'[\w-]', v[-1]
            ) and i < len(explanation_values) - 1 and explanation_values[
                    i + 1].value[0] not in '\t\n ':
                values.append(v + ' ')
            else:
                values.append(v)
        return ''.join(values)

    def process_explanation_session(self, explanation):
        if explanation.pairs:
            for pair in explanation.pairs:
                value = self.process_explanation_values(pair.explanation_values)
                ExplanationPair_key = f'EPK_{pair.keys[0]}'
                for key in pair.keys:
                    self.concrete_specs[
                        'explanation_key_to_ExplanationPair_key'][
                            key] = ExplanationPair_key
                self.explanation[ExplanationPair_key] = value

    def process_explanation_item(self):
        new_explanation = {}
        for key, value in self.explanation.items():
            new_explanation[key] = {}
            if isinstance(value, ExplanationItem):
                if value.plaintext:
                    new_explanation[key]['plaintext'] = value.plaintext
                if value.plain_option_syntax:
                    new_explanation[key][
                        'plain_option_syntax'] = value.plain_option_syntax
                processed_value = self.process_explanation_values(
                    value.explanation_values)
                new_explanation[key] = processed_value
            else:
                new_explanation[key] = value
        self.explanation = new_explanation
