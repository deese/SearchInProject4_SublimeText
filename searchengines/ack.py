import os
from . import base


class Ack(base.Base):
    def __init__(self, settings):
        super().__init__(settings)
        # Ubuntu's ack from repos is called ack-grep by default
        if os.name != 'nt':  # no os.uname on Windows
            if 'Ubuntu' in os.uname()[3] and self.path_to_executable == 'ack' and os.system('which ack-grep') == 0:
                self.path_to_executable = 'ack-grep'


engine_class = Ack
