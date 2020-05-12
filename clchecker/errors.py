import re

    
def reverse_python_re_escape(m):
    string = m.group(1)
    return re.sub(r'\\(.)', r'\1', string)


class CLError(Exception):
    def __init__(self, message, start_line=None, start_col=None,
                 end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None, filename=None, severity=None):
        super().__init__(message.encode('utf-8'))
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        self.abs_start = abs_start
        self.abs_end = abs_end
        self.err_type = err_type
        self.filename = filename
        self.severity= severity

        # todo: make message more readable
        equal = "(?<!( |\t))=(?!( |\t))".encode().decode()
        pkg = "'[^=\\s]+'".encode().decode()
        path = "(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\-\.]+".encode().decode()
        dir = "(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\.\-]+(?:\/)?".encode().decode()
        message = message.replace(equal, '=(no space before or after)')
        message = message.replace(pkg, "VERSION")
        message = message.replace(path, "PATH")
        message = message.replace(dir, "DIR")

        # replace look-ahead and look-behind in regex
        # '(?<!(\\w|\\-))\\-\\-quiet(?!(\\w|\\-))' will become '--quiet'
        look_behide = re.escape('(?<!(\w|\-))')
        look_ahead = re.escape('(?!(\w|\-))')
        pattern = look_behide + r'(.*?)' + look_ahead
        message = re.sub(pattern, reverse_python_re_escape, message)

        message = re.sub(r'position \(([0-9]*), ([0-9]*)\)', f'the position of the star(*) in' , message)
        self.message = message


    def __str__(self):
        if self.start_line or self.start_col or self.filename:
            return f'File "{self.filename}", {"line:" + str(self.start_line) if self.start_line else ""}, {"col:" + str(self.start_col) if self.start_col else ""}\n{self.message}'
        else:
            return super.__str__()


class CLSyntaxError(CLError):
    def __init__(self, message, start_line=None, start_col=None, end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None,
                 expected_rules=None, filename=None, severity=None):
        super().__init__(
            message, start_line, start_col, end_line, end_col, err_type, filename, severity=severity)
        # Possible rules on this position
        self.expected_rules = expected_rules


class CLSemanticError(CLError):
    def __init__(self, message, start_line=None, start_col=None, end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None,
                 expected_obj_cls=None, filename=None, severity=None):
        super().__init__(
            message, start_line, start_col, end_line, end_col, err_type, filename, severity=severity)
        # Expected object of class
        self.expected_obj_cls = expected_obj_cls
