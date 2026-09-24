import os
import shutil
from . import base


class Ack(base.Base):
    ENGINE_NAME = "ack"

    def __init__(self, settings):
        super().__init__(settings)
        if os.name != 'nt':
            if 'Ubuntu' in os.uname()[3] and self.path_to_executable == 'ack' and shutil.which('ack-grep'):
                self.path_to_executable = 'ack-grep'

    def literal_flag(self):
        return ["--literal"]


engine_class = Ack
