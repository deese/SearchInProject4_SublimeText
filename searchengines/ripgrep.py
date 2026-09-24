from . import base


class Ripgrep(base.Base):
    ENGINE_NAME = "ripgrep"

    def literal_flag(self):
        return ["-F"]

    def _is_search_error(self, returncode, output, error):
        return (returncode != 0) and self._sanitize_output(error) != ""


engine_class = Ripgrep
