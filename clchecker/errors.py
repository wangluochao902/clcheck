class CLError(Exception):
    def __init__(self, message, start_line=None, start_col=None,
                 end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None, filename=None):
        super().__init__(message.encode('utf-8'))
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        self.abs_start = abs_start
        self.abs_end = abs_end
        self.err_type = err_type
        self.filename = filename
        self.message = message

    def __str__(self):
        if self.start_line or self.start_col or self.filename:
            return f'File "{self.filename}", {"line:" + str(self.start_line) if self.start_line else ""}, {"col:" + str(self.start_col) if self.start_col else ""}\n{self.message}'
        else:
            return super.__str__()


class CLSyntaxError(CLError):
    def __init__(self, message, start_line=None, start_col=None, end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None,
                 expected_rules=None, filename=None):
        super().__init__(
            message, start_line, start_col, end_line, end_col, err_type, filename)
        # Possible rules on this position
        self.expected_rules = expected_rules


class CLSemanticError(CLError):
    def __init__(self, message, start_line=None, start_col=None, end_line=None, end_col=None, abs_start=None, abs_end=None, err_type=None,
                 expected_obj_cls=None, filename=None):
        super().__init__(
            message, start_line, start_col, end_line, end_col, err_type, filename)
        # Expected object of class
        self.expected_obj_cls = expected_obj_cls
