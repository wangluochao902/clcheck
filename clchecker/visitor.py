from clchecker.errors import CLError
from clchecker.translate import Translator
import config
from textx import metamodel_from_file
import bashlex
import re


class Visitor(bashlex.ast.nodevisitor):
    def __init__(self, clchecker, logger=None):
        self.clchecker = clchecker
        self.logger = logger
        self.command_range = {}

    def has_parameter(self, parts):
        for part in parts:
            if part.kind == 'parameter':
                return True
            if hasattr(part, 'parts') and part.parts:
                if self.has_parameter(part.parts):
                    return True
        return False

    def visitcommand(self, node, parts):
        index = bashlex.ast.findfirstkind(parts, 'word')
        if self.has_parameter(parts):
            return
        if index != -1:
            wordnode = parts[index]
            if wordnode.parts:
                if self.logger:
                    self.logger.info(
                    'no way! we still can expend the a command node. Something is wrong')
            else:
                commandname = wordnode.word
                start = wordnode.pos[0]
                end = node.pos[1]
                commandline = self.code[start:end]
                self.command_range[commandname] = {
                    "startLine": len(self.code[:start+1].split('\n')),
                    "endLine": len(self.code[:end+1].split('\n')),
                    "startColumn": len(self.code[:start+1].rsplit('\n', 1)[-1]),
                    "endColumn": len(self.code[:end+1].rsplit('\n', 1)[-1])
                }
                try:
                    self.clchecker.check_semantics(commandname, commandline)
                except CLError as e:
                    print(f"this has error: {commandline}")
                    lines = self.code[:start].split('\n')
                    if lines:
                        start_line = len(lines)-1 + e.start_line
                        end_line = len(lines)-1 + e.end_line if e.end_line else None
                        if e.start_line == 1:
                            start_col = len(lines[-1]) + e.start_col
                        else:
                            start_col = e.start_col
                        if e.end_line == 1:
                            end_col = len(lines[-1]) + e.end_col if e.end_col else None
                        else:
                            end_col = e.end_col
                    else:
                        start_line = e.start_line
                        start_col = e.start_col
                        end_line = e.end_line
                        end_col = e.end_col
                    # todo: make message more readable
                    pkg = "[\S]+".encode().decode()
                    message = e.message.replace(pkg, "<PKG>")
                    message = re.sub(r'position \(([1-9]*), ([1-9]*)\)', f'the position of the star(*) in' , message)
                    self.markers.append(self.create_marker(start_line, start_col, end_line, end_col, message, "Error"))

    def start(self, code):
        self.command_range = {}
        self.markers = []
        code = code.rstrip()
        
        self.code = code
        try:
            parts = bashlex.parse(code)
        except:
            # todo: handle bash parsing error
            # raise ValueError('Error parsing the bash script')
            return self.markers, self.command_range
        for node in parts:
            self.visit(node)

        return self.markers, self.command_range

    def find_explanation(self, command_name, key):
        return self.clchecker.find_explanation(command_name, key)

    @staticmethod
    def create_marker(startLineNumber, startColumn, endLineNumber, endColumn, message, severity='Warning'):
    # severity: Warning | Error | Info | Hint
        return {
            'startLineNumber': startLineNumber,
            'startColumn': startColumn,
            'endLineNumber': endLineNumber,
            'endColumn': endColumn,
            'message': message,
            'severity': severity,
        }


