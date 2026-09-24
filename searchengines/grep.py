from . import base


class Grep(base.Base):
    ENGINE_NAME = "grep"

    def literal_flag(self):
        return ["-F"]


engine_class = Grep
