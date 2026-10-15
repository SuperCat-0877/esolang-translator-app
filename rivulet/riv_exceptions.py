"Exceptions used by the Rivulet parser and interpreter"

class RivuletSyntaxError(Exception):
    "An issue with strand- or glyph-level syntax"

    def __init__(self, message):
        super().__init__(f"SYNTAX ERROR: {message}")

class InternalError(Exception):
    "An internal issue with the interpreter"

    def __init__(self, message):
        super().__init__(f"INTERNAL ERROR: {message}")
