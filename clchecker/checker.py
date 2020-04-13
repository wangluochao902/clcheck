from clchecker.store import Store
from clchecker.errors import CLSemanticError, CLSyntaxError
from textx import metamodel_from_str
from clchecker.constants import BASETYPE
import textx


def update_clsname_to_txobj(txobj, clsname_to_txobj):
    """recursively add find the classname of any txobj in the model"""
    if hasattr(txobj, '_tx_attrs'):
        for name, attr in txobj._tx_attrs.items():
            if name != 'command' and name != 'content' and attr.cont and getattr(txobj, name):
                obj = getattr(txobj, name)
                clsname = obj.__class__.__name__

                # ShortOption_2:
                #    option_key="-y"
                # ;
                # here clsname of option_key is "str" which means we hit the leaf.
                # there is no tx_obj anymore and we also not interested in "str" class
                if clsname == "str":
                    continue

                # OneMustPresentCollection_1_Multi:
                #    statements+=OneMustPresentCollection_1
                # ;
                # here the clsname of `statements` is "list", all elements in the list belong to the same class
                # so we only need to check the first element. Also, we are not interested in the "list" class itself.
                if clsname == "list":
                    if obj:
                        update_clsname_to_txobj(obj[0], clsname_to_txobj)
                    continue

                assert clsname not in clsname_to_txobj, f"{clsname} exists"
                clsname_to_txobj[clsname] = obj
                update_clsname_to_txobj(obj, clsname_to_txobj)


class CLchecker():
    def __init__(self, store):
        self.store = store

    def check_after_before_always_mutex(self, clsname, specs, clsname_to_txobj, clsname_to_readable_syntax):
        fired_obj = clsname_to_txobj[clsname]
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
                        excepted_but_not_occur_names = [
                            name for name in rule_spec['all_must_present'] if name not in clsname_to_txobj]
                        if excepted_but_not_occur_names:
                            expected_string = ",".join(
                                [clsname_to_readable_syntax[name] for name in excepted_but_not_occur_names])

                            raise CLSemanticError(
                                f'Expect `{expected_string}` when `{clsname_to_readable_syntax[clsname]}` occurs', **position)
                    if rule_type == 'mutex':
                        not_excepted_but_occur_names = [
                            name for name in rule_spec['all_must_present'] if name in clsname_to_txobj]
                        if not_excepted_but_occur_names:
                            expected_string = ",".join(
                                [clsname_to_readable_syntax[name] for name in not_excepted_but_occur_names])
                            raise CLSemanticError(
                                f"`{expected_string}` and `{clsname_to_readable_syntax[clsname]}` can't occur at the same time", **position)

                # todo: before, after
                if 'one_must_present' in rule_spec:
                    num_occurs = sum(
                        [1 for name in clsname_to_txobj if name in rule_spec['one_must_present']])
                    if num_occurs == 0:
                        error_string = f"one of {[clsname_to_readable_syntax[name] for  name in rule_spec['one_must_present']]} to present"
                        raise CLSemanticError(
                            f"{clsname} expect {error_string}", **position)

    @staticmethod
    def get_abs_position(commandline, line_num, col_num):
        lines = commandline.split('\n')
        abs_position = sum(
            [len(line)+1 for line in lines[:line_num-1]]) + col_num
        return abs_position

    def check_semantics(self, command_name, commandline):
        command_doc = self.store.findcommand(command_name)
        if command_doc:
            command_metamodel = metamodel_from_str(
                command_doc.tx_syntax+BASETYPE)
            try:
                model = command_metamodel.model_from_str(commandline)
            except textx.TextXSyntaxError as e:
                abs_start = self.get_abs_position(
                    commandline, e.line, e.col)
                raise CLSyntaxError(e.message, start_line=e.line, start_col=e.col, abs_start=abs_start,
                                    err_type=e.err_type, expected_rules=e.expected_rules)
            except textx.TextXSemanticError as e:
                abs_start = self.get_abs_position(commandline, e.start_line, e.end_line)
                raise CLSemanticError(e.message, start_line=e.line, start_col=e.col, abs_start=abs_start,
                                      err_type=e.err_type, expected_obj_cls=e.expected_obj_cls)

            self.model = model
            clsname_to_txobj = {}
            clsname_to_readable_syntax = command_doc.clsname_to_readable_syntax
            update_clsname_to_txobj(model, clsname_to_txobj)
            concrete_specs = command_doc.concrete_specs
            for clsname in clsname_to_txobj:
                if clsname in concrete_specs:
                    self.check_after_before_always_mutex(
                        clsname, concrete_specs[clsname], clsname_to_txobj, clsname_to_readable_syntax)

    def find_explanation(self, command_name, key):
        command_doc = self.store.findcommand(command_name)
        if command_doc:
            if key in command_doc.explanation:
                return command_doc.explanation[key]