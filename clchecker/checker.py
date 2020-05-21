import re
from collections import defaultdict

import textx
from textx import metamodel_from_str

from clchecker.constants import BASETYPE
from clchecker.errors import CLSemanticError, CLSyntaxError
from clchecker.store import Store
from config import COMMON_COMMANDS


class CLchecker():

    def __init__(self, store):
        self.store = store
        self.metamodel_doc_cache = {}
        self.init_metamodel_doc_cache()
        self.new_lines_start = []
    
    def init_metamodel_doc_cache(self):
        for command_name in COMMON_COMMANDS:
            command_doc = self.store.findcommand(command_name)
            if command_doc:
                command_metamodel = metamodel_from_str(command_doc.tx_syntax +
                                                       BASETYPE,
                                                       autokwd=False)
                self.metamodel_doc_cache[command_name] = (command_metamodel,
                                                      command_doc)

    def assign_name_attr_to_actual_value(self, txobj):
        clsname = txobj.__class__.__name__
        if clsname == "str":
            return txobj
        if clsname == "list":
            name_attr = ''.join(
                [self.assign_name_attr_to_actual_value(obj) for obj in txobj])
            return name_attr
        if not hasattr(txobj, '_tx_attrs'):
            return ""

        name_attr = "".join([
            self.assign_name_attr_to_actual_value(getattr(txobj, att))
            for att in txobj._tx_attrs
        ])
        txobj.name = name_attr
        return name_attr

    def check_after_before_always_mutex(self, ref, specs):
        # if ref is an OptionPair_key, it is not clear enough
        if ref in self.occured_OptionPair_to_option_key:
            clearer_ref = self.occured_OptionPair_to_option_key[ref]
        else:
            clearer_ref = ref
        fired_obj = self.ref_to_txobj[clearer_ref]
        start_line, start_col = self.model._tx_parser.pos_to_linecol(
            fired_obj._tx_position)
        end_line, end_col = self.model._tx_parser.pos_to_linecol(
            fired_obj._tx_position_end)
        position = {
            "start_line": start_line,
            "start_col": start_col,
            "end_line": end_line,
            "end_col": end_col,
            "abs_start": fired_obj._tx_position,
            "abs_end": fired_obj._tx_position_end
        }
        for rule_type in ('after', 'before', 'always', 'mutex'):
            if rule_type in specs:
                rule_spec = specs[rule_type]
                if 'all_must_present' in rule_spec:
                    if rule_type == 'always':
                        excepted_but_not_occur_refs = [
                            r for r in rule_spec['all_must_present']
                            if r not in self.all_occured_refs
                        ]
                        if excepted_but_not_occur_refs:
                            # todo: if the not occured ref is a OptionPair_key, it is not clear enough.
                            expected_string = ",".join(
                                excepted_but_not_occur_refs)

                            raise CLSemanticError(
                                f'Expect `{expected_string}` when `{clearer_ref}` occurs',
                                **position,
                                severity="Error")
                    if rule_type == 'mutex':
                        not_excepted_but_occur_refs = [
                            r for r in rule_spec['all_must_present']
                            if r in self.all_occured_refs
                        ]

                        # make not_excepted_but_occur_refs more clear when a OptionPair_key is inside
                        if not_excepted_but_occur_refs:
                            for i in range(len(not_excepted_but_occur_refs)):
                                r = not_excepted_but_occur_refs[i]
                                if r in self.occured_OptionPair_to_option_key:
                                    not_excepted_but_occur_refs[
                                        i] = self.occured_OptionPair_to_option_key[
                                            r]

                            expected_string = ",".join(
                                not_excepted_but_occur_refs)
                            raise CLSemanticError(
                                f"`{expected_string}` and `{clearer_ref}` can't occur at the same time",
                                **position,
                                severity="Error")

                # todo: before, after
                if 'one_must_present' in rule_spec:
                    if rule_type == 'always':
                        has = False
                        for r in self.all_occured_refs:
                            if r in rule_spec['one_must_present']:
                                has = True
                                break
                        if not has:
                            raise CLSemanticError(
                                f'except one of `{" | ".join(rule_spec["one_must_present"])}` when `{clearer_ref}` occurs',
                                **position,
                                severity="Error")

                # todo before, mutex, after
    def get_abs_position(self, line_num, col_num):
        return self.new_lines_start[line_num - 1] + col_num - 1


    def get_abs_position_from_commandline(self, commandline, line_num, col_num):
        lines = commandline.split('\n')
        return sum([0]+[len(l)+1 for l in lines[:line_num-1]]) + col_num - 1

    def convert_pos_to_linecol(self, abs_pos):
        '''Use binary search to find the line number.
        don't `have to` use binary search since len(self.new_lines_start) is usually smaller than 10'''
        l, r = 0, len(self.new_lines_start) - 1
        while l <= r:
            if l == r:
                line = l
                break
            mid = l + (r - l) // 2
            if self.new_lines_start[mid] <= abs_pos and self.new_lines_start[
                    mid + 1] > abs_pos:
                line = mid
                break
            elif self.new_lines_start[mid] > abs_pos:
                r = mid - 1
            else:
                l = mid + 1
            # line number counts from 1
        return line + 1, abs_pos - self.new_lines_start[line] + 1

    def get_position_from_obj(self, obj):
        start_line, start_col = self.convert_pos_to_linecol(obj._tx_position)
        end_line, end_col = self.convert_pos_to_linecol(obj._tx_position_end)
        position = {
            "start_line": start_line,
            "start_col": start_col,
            "end_line": end_line,
            "end_col": end_col,
            "abs_start": obj._tx_position,
            "abs_end": obj._tx_position_end
        }
        return position

    def get_position_from_abs(self, abs_start, abs_end):
        start_line, start_col = self.convert_pos_to_linecol(abs_start)
        end_line, end_col = self.convert_pos_to_linecol(abs_end)
        position = {
            "start_line": start_line,
            "start_col": start_col,
            "end_line": end_line,
            "end_col": end_col,
            "abs_start": abs_start,
            "abs_end": abs_end
        }
        return position

    def update_ref_to_txobj(self, txobj):
        """
        recursively find the ref of any txobj in the model.
        ref can be an option_key or a sub_command's value
        """
        if hasattr(txobj, '_tx_attrs'):
            for name, attr in txobj._tx_attrs.items():
                if name != 'content' and attr.cont and getattr(txobj, name):
                    obj = getattr(txobj, name)
                    clsname = obj.__class__.__name__

                    # ShortOption_2:
                    #    option_key="-y"
                    # ;
                    # here clsname of option_key is "str" which means we hit the leaf.
                    # there is no tx_obj anymore and we also not interested in "str" class.
                    if clsname == "str":
                        continue

                    # OneMustPresentCollection_1_Multi:
                    #    statements+=OneMustPresentCollection_1
                    # ;
                    # todo: is the following correct? Now I change to check all elements in the list.
                    # here the clsname of `statements` is "list", all elements in the list belong to the same class
                    # so we only need to check the first element. Also, we are not interested in the "list" class itself.
                    if clsname == "list":
                        for ob in obj:
                            self.update_ref_to_txobj(ob)
                        continue

                    # if clsname is SubCommand or Option, we only allow it happen once
                    if clsname.startswith('SubCommand') or clsname.startswith(
                            'ShortOption') or clsname.startswith('LongOption'):
                        if clsname.startswith('SubCommand'):
                            ref = obj.value
                        # when obj is a ShortOption, we need to add '-' to its option_key
                        elif clsname.startswith('ShortOption'):
                            # there are 2 kinds of ShortOpiton:
                            # The first one doesn't have value attribute, but option_key. it's option_key doesn't start with '-'
                            # The second one has the value attribute. It's option_key usually start with '-'
                            # For example, in 'apt-get', 'y' is the first kind. '-t' is the second kind since it should followed by target release.
                            if not hasattr(obj, 'value'):
                                ref = '-' + obj.option_key
                            else:
                                ref = obj.option_key
                        # when obj is a LongOption, obj.option_key has already had "--" before it
                        else:
                            ref = obj.option_key
                        # the ref now happen multiple time, check whether we need to report it as error
                        if ref in self.ref_to_txobj:
                            need_to_report = True
                            # if it is an option and has value attribute
                            if (clsname.startswith('ShortOption') or clsname.startswith('LongOption')):
                                OptionPair_key = self.option_keys_to_OptionPair_key[
                                    ref]
                                for option_key, readable_syntax in self.OptionPair_key_to_option_keys_and_readable_syntax[
                                        OptionPair_key]:
                                    if option_key == ref and "+=" in readable_syntax:
                                        need_to_report = False
                                        break
                            if need_to_report:
                                position = self.get_position_from_obj(obj)
                                raise CLSyntaxError(
                                    f"{ref} has presented previous in the `{self.command_name}` command",
                                    **position,
                                    severity='Warning')
                        self.ref_to_txobj[ref] = obj
                    if clsname.startswith('ShortOption') or clsname.startswith(
                            'LongOption'):
                        # when obj is a ShortOption, we need to add '-' to its option_key
                        if clsname.startswith('ShortOption'):
                            if not hasattr(obj, 'value'):
                                # since obj doesn't have value attribute, it is the first kind. We should add "-" to its option_key
                                option_key = "-" + obj.option_key
                            else:
                                option_key = obj.option_key
                        else:
                            option_key = obj.option_key
                        OptionPair_key = self.option_keys_to_OptionPair_key[
                            option_key]
                        # the same OptionPair_key can only occur once except there is a '+=' in the option_key readable syntax
                        if OptionPair_key in self.occured_OptionPair_to_option_key:
                            need_to_report = True
                            for option_key_, readable_syntax in self.OptionPair_key_to_option_keys_and_readable_syntax[
                                    OptionPair_key]:
                                if option_key == option_key_ and "+=" in readable_syntax:
                                    need_to_report = False
                                    break
                            if need_to_report:
                                position = self.get_position_from_obj(obj)
                                same_option_keys_and_readable_syntaxes = self.OptionPair_key_to_option_keys_and_readable_syntax[
                                    OptionPair_key]
                                readable_syntaxes = [
                                    i[1] for i in
                                    same_option_keys_and_readable_syntaxes
                                ]
                                raise CLSyntaxError(
                                    F"Only one of `{' | '.join(readable_syntaxes)}` is enough, since they have the same meaning",
                                    **position,
                                    severity='Warning')
                        self.occured_OptionPair_to_option_key[
                            OptionPair_key] = option_key

                    self.update_ref_to_txobj(obj)

    def pre_process_commandline(self, commandline):

        # replace windows-style newline with unix-style newline
        commandline = commandline.replace('\r\n', ' \n')

        # handle escaped newline
        self.new_lines_start = [0] + [
            m.end() for m in re.finditer(r'\\?\n', commandline)
        ]
        commandline = commandline.replace('\\\n', '  ')
        return commandline

    def check(self, command_name, commandline, debug=False):
        # print(commandline.encode())
        commandline = self.pre_process_commandline(commandline)
        command_metamodel = None
        if command_name in self.metamodel_doc_cache:
            command_metamodel, command_doc = self.metamodel_doc_cache[command_name]
        else:
            command_doc = self.store.findcommand(command_name)
            if command_doc:
                command_metamodel = metamodel_from_str(command_doc.tx_syntax +
                                                       BASETYPE,
                                                       autokwd=False)
                self.metamodel_doc_cache[command_name] = (command_metamodel,
                                                      command_doc)
        if command_metamodel:
            try:
                model = command_metamodel.model_from_str(commandline)
            except textx.TextXSyntaxError as e:
                abs_start = self.get_abs_position_from_commandline(commandline, e.line, e.col)
                position = self.get_position_from_abs(abs_start, abs_start)
                raise CLSyntaxError(e.message,
                                    **position,
                                    expected_rules=e.expected_rules,
                                    severity="Error")
            except textx.TextXSemanticError as e:
                abs_start = self.get_abs_position_from_commandline(commandline, e.line,
                                                  e.col)
                position = self.get_position_from_abs(abs_start, abs_start)
                raise CLSemanticError(e.message,
                                      **position,
                                      err_type=e.err_type,
                                      expected_obj_cls=e.expected_obj_cls,
                                      severity="Error")
            if debug:
                self.assign_name_attr_to_actual_value(model)
            self.model = model
            self.command_name = command_name
            self.ref_to_txobj = {}
            self.clsname_to_readable_syntax = command_doc.clsname_to_readable_syntax

            self.concrete_specs = command_doc.concrete_specs
            self.OptionPair_key_to_option_keys_and_readable_syntax = self.concrete_specs[
                'OptionPair_key_to_option_keys_and_readable_syntax']
            self.option_keys_to_OptionPair_key = self.concrete_specs[
                'option_keys_to_OptionPair_key']

            self.occured_OptionPair_to_option_key = {}

            self.update_ref_to_txobj(model)
            self.all_occured_refs = list(self.ref_to_txobj.keys()) + list(
                self.occured_OptionPair_to_option_key.keys())
            #TODO: differentiate OptionPair_key and option_key in all_occured_refs
            for ref in self.all_occured_refs:
                if ref in self.concrete_specs:
                    self.check_after_before_always_mutex(
                        ref, self.concrete_specs[ref])

    def find_explanation(self, command_name, word):
        command_doc = self.store.findcommand(command_name)
        if command_doc:
            Pair_key = None
            found_key = word
            if word in command_doc.concrete_specs[
                    'explanation_key_to_ExplanationPair_key']:
                Pair_key = command_doc.concrete_specs[
                    'explanation_key_to_ExplanationPair_key'][word]
            elif word in command_doc.concrete_specs[
                    'option_keys_to_OptionPair_key']:
                Pair_key = command_doc.concrete_specs[
                    'option_keys_to_OptionPair_key'][word]
            elif ("-"+word) in command_doc.concrete_specs[
                    'option_keys_to_OptionPair_key']:
                found_key = "-" + word
                Pair_key = command_doc.concrete_specs[
                    'option_keys_to_OptionPair_key'][found_key]
            if Pair_key:
                return found_key, command_doc.explanation[Pair_key]
        return None, None
