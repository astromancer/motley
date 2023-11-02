

class InvalidStyle(Exception):
    """
    Raised when a user input object cannot be resolved to a code for colour or
    effect.
    """

    def __init__(self, obj, fg_or_bg):
        super().__init__(
            (f'Could not interpret object {obj!r} of type {type(obj)!r} as a '
             f'valid {fg_or_bg!r} colour or effect.')
        )
