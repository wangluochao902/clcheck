from clchecker.errors import CLError
from clchecker.translate import Translator
import clchecker.config as config
from textx import metamodel_from_file
import bashlex
import re


class Visitor(bashlex.ast.nodevisitor):
    def __init__(self, clchecker, logger=None):
        self.clchecker = clchecker
        self.logger = logger

    def visitcommand(self, node, parts):
        index = bashlex.ast.findfirstkind(parts, 'word')
        if index != -1:
            commandnode = parts[index]
            if commandnode.parts:
                if self.logger:
                    self.logger.info(
                    'no way! we still can expend the a command node. Something is wrong')
            else:
                commandname = commandnode.word
                commandline = self.code[node.pos[0]:node.pos[1]]
                try:
                    self.clchecker.check(commandname, commandline)
                except CLError as e:
                    lines = self.code[:node.pos[0]].split('\n')
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
                    pkg = "[\w\*][\w\.\-\*]*".encode().decode()
                    message = e.message.replace(pkg, "<PKG>")
                    message = re.sub(r'position \(([1-9]*), ([1-9]*)\)', f'the position of the star(*) in' , message)
                    self.markers.append(self.create_marker(start_line, start_col, end_line, end_col, message, "Error"))

    def start(self, code):
        code = code.rstrip()
        
        self.code = code
        print(code)
        parts = bashlex.parse(code)
        self.markers = []
        for node in parts:
            self.visit(node)
        return self.markers

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


