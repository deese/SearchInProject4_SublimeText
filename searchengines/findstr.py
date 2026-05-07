import os
import re
import shlex
from . import base

# Matches the directory header lines findstr emits when using /d:
# e.g. "  D:\some\path:" or "D:\some\path:"
DIR_HEADER_RE = re.compile(r'^\s*([A-Za-z]:[^:]+):\s*$')
# Matches result lines: filename:lineno:text
RESULT_RE = re.compile(r'^([^:]+):(\d+):(.*)$')


class FindStr(base.Base):
    """Uses Windows built-in findstr command."""

    def _arguments(self, query, folders):
        return (
            [self.path_to_executable] +
            shlex.split(self.mandatory_options) +
            shlex.split(self.common_options) +
            ["/d:%s" % ";".join(folders), query, "*.*"])

    def _parse_output_with_base(self, output, common_path):
        results = []
        current_dir = ""
        common_path_lower = common_path.lower()
        for line in output.split("\n"):
            if not line.strip():
                continue
            dir_match = DIR_HEADER_RE.match(line)
            if dir_match:
                current_dir = dir_match.group(1).strip()
                continue
            result_match = RESULT_RE.match(line)
            if result_match:
                filename, lineno, text = result_match.groups()
                abs_path = os.path.join(current_dir, filename) if current_dir else filename
                # Strip common_path prefix case-insensitively (findstr may differ in case)
                if abs_path.lower().startswith(common_path_lower):
                    rel_path = abs_path[len(common_path):]
                else:
                    rel_path = os.sep + abs_path
                if not rel_path.startswith(os.sep):
                    rel_path = os.sep + rel_path
                results.append((rel_path + ":" + lineno, lineno, text.strip()))
        return results

    def run(self, query, folders):
        self._common_path = self.commonpath(folders)
        return super().run(query, folders)

    def _parse_output(self, output):
        return self._parse_output_with_base(output, self._common_path)

    def _is_search_error(self, returncode, output, error):
        return self._sanitize_output(error) != ""


engine_class = FindStr
