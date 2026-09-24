from . import base


class TheSilverSearcher(base.Base):
    ENGINE_NAME = "the_silver_searcher"

    def literal_flag(self):
        return ["-Q"]

    def _is_search_error(self, returncode, output, error):
        return (returncode != 0) and self._sanitize_output(error) != ""


engine_class = TheSilverSearcher
