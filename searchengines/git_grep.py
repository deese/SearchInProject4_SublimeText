from . import base


class GitGrep(base.Base):
    ENGINE_NAME = "git_grep"

    def literal_flag(self):
        return ["-F"]


engine_class = GitGrep
