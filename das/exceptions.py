class ParseError(Exception):
    pass


class EndOfTokens(ParseError):
    pass


class DasSyntaxError(ParseError):
    pass
