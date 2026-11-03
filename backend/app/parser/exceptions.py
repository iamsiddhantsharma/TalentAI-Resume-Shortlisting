class ResumeParserError(Exception):
    """
    Base exception for all resume parser errors.
    """

    pass


class UnsupportedFileTypeError(ResumeParserError):
    """
    Raised when a file extension is not supported
    by the resume parser.
    """

    pass


class ResumeTextExtractionError(ResumeParserError):
    """
    Raised when text cannot be extracted from a resume.
    """

    pass
