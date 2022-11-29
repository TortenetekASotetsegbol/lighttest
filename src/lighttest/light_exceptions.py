class NoneAction(Exception):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f'This method did nothing.'
