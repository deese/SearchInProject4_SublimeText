import os
import re
import threading
import traceback
from collections import defaultdict
from typing import List, Optional, Tuple

import sublime
import sublime_plugin

from . import searchengines


class SearchInProjectCommand(sublime_plugin.WindowCommand):
    """Command that runs external search tools and displays results."""

    # Sublime Text hangs on very long lines (e.g. minified JS) unless trimmed.
    MAX_RESULT_LINE_LENGTH = 1000

    # Results above this threshold go straight to Find Results view.
    MAX_QUICK_PANEL_RESULTS = 500

    def __init__(self, window: sublime.Window) -> None:
        super().__init__(window)
        self.results: List[Tuple[str, ...]] = []
        self.last_search_string = ""
        self.last_selected_result_index = 0
        self.saved_view: Optional[sublime.View] = None
        self.engine = None
        self.engine_name = ""
        self._search_thread: Optional[threading.Thread] = None
        self._spinner_frame = 0

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    def run(self, type: str = "search") -> None:
        if type == "search":
            self.search()
        elif type == "clear":
            self.clear_markup()
        elif type == "next":
            self.goto_relative_result(1)
        elif type == "prev":
            self.goto_relative_result(-1)
        else:
            raise ValueError(f"unrecognized type {type!r}")

    # ------------------------------------------------------------------
    # Search orchestration
    # ------------------------------------------------------------------

    def load_search_engine(self) -> None:
        settings = sublime.load_settings("SearchInProject4.sublime-settings")
        platform_default = "findstr" if os.name == "nt" else "grep"
        self.engine_name = settings.get("search_in_project_engine") or platform_default
        self.engine = searchengines.get_engine(self.engine_name, settings)

    def search(self) -> None:
        self.load_search_engine()
        view = self.window.active_view()
        if view is None:
            return

        self.saved_view = view
        selection_text = ""
        if view.sel():
            first_sel = view.sel()[0]
            if not first_sel.empty():
                selection_text = view.substr(first_sel)

        initial_text = (
            selection_text
            if selection_text and "\n" not in selection_text
            else self.last_search_string
        )

        panel_view = self.window.show_input_panel(
            "Search in project:",
            initial_text,
            self.perform_search,
            None,
            None,
        )
        panel_view.run_command("select_all")

    def perform_search(self, text: str) -> None:
        if not text:
            return

        if self.last_search_string != text:
            self.last_selected_result_index = 0
        self.last_search_string = text

        # Cancel any running search.
        if self._search_thread and self._search_thread.is_alive():
            self._search_thread = None

        folders = self._search_folders()
        self.common_path = self.engine.commonpath(folders)

        self._spinner_frame = 0
        self._start_spinner(text)

        thread = threading.Thread(
            target=self._run_search_thread,
            args=(text, folders),
            daemon=True,
        )
        self._search_thread = thread
        thread.start()

    def _run_search_thread(self, text: str, folders: List[str]) -> None:
        thread = threading.current_thread()
        try:
            results = self.engine.run(text, folders)
        except Exception as exc:
            error_msg = "%s running search engine %s:\n%s" % (
                exc.__class__.__name__, self.engine_name, exc
            )
            self.dprint(traceback.format_exc())
            sublime.set_timeout(lambda: self._on_search_error(thread, error_msg), 0)
            return
        sublime.set_timeout(lambda: self._on_search_done(thread, results), 0)

    def _on_search_error(self, thread: threading.Thread, error_msg: str) -> None:
        if thread is not self._search_thread:
            return
        self._stop_spinner()
        self.results = []
        sublime.error_message(error_msg)

    def _on_search_done(self, thread: threading.Thread, results: List[Tuple[str, ...]]) -> None:
        if thread is not self._search_thread:
            return
        self._stop_spinner()

        if not results:
            self.results = []
            sublime.message_dialog("No results")
            return

        settings = sublime.load_settings("SearchInProject4.sublime-settings")
        show_list = settings.get("search_in_project_show_list_by_default") == "true"
        limit = settings.get("search_in_project_max_quick_panel_results", self.MAX_QUICK_PANEL_RESULTS)
        over_limit = len(results) > limit

        self.results = results
        if show_list or over_limit:
            if over_limit:
                self.window.status_message(
                    "Search In Project: %d results — opening Find Results view" % len(results)
                )
            self.list_in_view()
        else:
            self.results.append(("``` List results in view ```",))
            self.window.show_quick_panel(
                self._format_quick_panel(self.results),
                self.goto_result,
                0,
                self.last_selected_result_index,
                self.on_highlighted,
            )

    def _start_spinner(self, query: str) -> None:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def tick():
            if self._search_thread is None or not self._search_thread.is_alive():
                return
            frame = frames[self._spinner_frame % len(frames)]
            self._spinner_frame += 1
            self.window.status_message("Search In Project: %s searching for '%s'…" % (frame, query))
            sublime.set_timeout(tick, 100)

        sublime.set_timeout(tick, 0)

    def _stop_spinner(self) -> None:
        self._search_thread = None
        self.window.status_message("")

    # ------------------------------------------------------------------
    # Result navigation
    # ------------------------------------------------------------------

    def on_highlighted(self, file_no: int) -> None:
        self.last_selected_result_index = file_no
        # last result is "list in view"
        if file_no != -1 and file_no != len(self.results) - 1:
            self.open_and_highlight_file(file_no, transient=True)

    def open_and_highlight_file(self, file_no: int, transient: bool = False) -> None:
        result = self.results[file_no]
        file_name_and_col = self._make_file_path(result[0])
        flags = sublime.ENCODED_POSITION
        if transient:
            flags |= sublime.TRANSIENT
        view = self.window.open_file(file_name_and_col, flags)
        self._highlight_matches(view)

        position = result[1] if len(result) > 1 else None
        if position:
            self._navigate_when_ready(view, position)

    def goto_result(self, file_no: int) -> None:
        if file_no == -1:
            self.clear_markup()
            if self.saved_view:
                self.window.focus_view(self.saved_view)
            return

        if file_no == len(self.results) - 1:  # last result is "list in view"
            self.list_in_view()
        else:
            self.open_and_highlight_file(file_no)

    def goto_relative_result(self, offset: int) -> None:
        if not self.last_search_string:
            return
        new_index = self.last_selected_result_index + offset
        if 0 <= new_index < len(self.results) - 1:
            self.last_selected_result_index = new_index
            self.goto_result(new_index)

    # ------------------------------------------------------------------
    # Markup / cleanup
    # ------------------------------------------------------------------

    def clear_markup(self) -> None:
        # every result except the last one (the "list in view")
        for result in self.results[:-1]:
            file_name_and_col = self._make_file_path(result[0])
            file_name = file_name_and_col.split(":")[0]
            view = self.window.find_open_file(file_name)
            if view:  # if the view is no longer open, do nothing
                view.erase_regions("search_in_project")
        self.results = []

    def list_in_view(self) -> None:
        view = sublime.active_window().new_file()
        view.run_command(
            "search_in_project_results",
            {
                "query": self.last_search_string,
                "results": self.results,
                "common_path": self.common_path.replace('"', ""),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _search_folders(self) -> List[str]:
        folders = self.window.folders()
        if folders:
            return folders
        filename = self.window.active_view().file_name() if self.window.active_view() else None
        if filename:
            return [os.path.dirname(filename)]
        return [os.path.expanduser("~")]

    def _make_file_path(self, raw_path: str) -> str:
        """Build an absolute file path from an engine result path.

        Engines may emit absolute paths (e.g. ``D:\file.py``) or
        relative ones (e.g. ``\file.py`` or ``/file.py``).  Relative
        paths are joined against ``self.common_path``.
        """
        # Windows absolute path (e.g. D:\...)
        if len(raw_path) > 1 and raw_path[1] == ":":
            return raw_path
        # Unix absolute path
        if raw_path.startswith("/"):
            return raw_path
        # Relative – prepend common_path as the original code did
        return self.common_path.replace('"', "") + raw_path

    def _navigate_when_ready(self, view: sublime.View, position: str) -> None:
        def navigate():
            if view.is_loading():
                sublime.set_timeout(navigate, 50)
                return
            self._navigate_to_line(view, position)
        sublime.set_timeout(navigate, 0)

    def _navigate_to_line(self, view: sublime.View, position: str) -> None:
        if not view.is_valid() or not position:
            return
        parts = position.split(":")
        try:
            line_no = int(parts[0]) - 1
            col_no = int(parts[1]) - 1 if len(parts) > 1 else 0
        except ValueError:
            return
        pt = view.text_point(line_no, col_no)
        view.sel().clear()
        view.sel().add(sublime.Region(pt))
        view.show(pt)

    def _format_quick_panel(self, results: List[Tuple[str, ...]]) -> List[str]:
        """Trim lines for the quick panel to avoid hangs on long lines."""
        formatted = []
        for result in results:
            line = " ".join(str(item) for item in result)
            if len(line) > self.MAX_RESULT_LINE_LENGTH:
                line = line[: self.MAX_RESULT_LINE_LENGTH] + " …"
            formatted.append(line)
        return formatted

    def _highlight_matches(self, view: sublime.View) -> None:
        if not self.last_search_string:
            return
        regions = view.find_all(self.last_search_string, sublime.IGNORECASE)
        view.add_regions(
            "search_in_project",
            regions,
            "entity.name.filename.find-in-files",
            "circle",
            sublime.DRAW_OUTLINED,
        )

    def dprint(self, msg: str) -> None:
        settings = sublime.load_settings("SearchInProject4.sublime-settings")
        if settings.get("debug", False):
            print(msg)


class SearchInProjectResultsCommand(sublime_plugin.TextCommand):
    """Command that renders search results into a scratch buffer."""

    def format_result(self, common_path: str, filename: str, lines: List[Tuple[str, str]]) -> str:
        lines_text = "\n".join(
            "  %s: %s" % (location, text) for location, text in lines
        )
        return "%s:\n%s\n" % (os.path.abspath(os.path.join(common_path, filename)), lines_text)

    def format_results(self, common_path: str, results: List[Tuple[str, ...]], query: str) -> str:
        grouped_by_filename: defaultdict[str, List[Tuple[str, str]]] = defaultdict(list)

        for result in results:
            if len(result) < 3:
                continue
            filename, location, text = result[0], result[1], result[2]
            grouped_by_filename[filename].append((location, text))

        line_count = len(results)
        file_count = len(grouped_by_filename)

        file_results = [
            self.format_result(common_path, filename, grouped_by_filename[filename])
            for filename in grouped_by_filename
        ]

        header = 'Search In Project results for "%s" (%u lines in %u files):\n\n' % (
            query,
            line_count,
            file_count,
        )
        return header + "\n".join(file_results)

    def run(self, edit: sublime.Edit, common_path: str, results: List[Tuple[str, ...]], query: str) -> None:
        self.view.set_name("Find Results")
        self.view.set_scratch(True)
        self.view.settings().set("search_in_project_results", True)
        self.view.assign_syntax("Packages/Default/Find Results.hidden-tmLanguage")
        results_text = self.format_results(common_path, results, query)
        self.view.insert(edit, self.view.text_point(0, 0), results_text)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))


class SearchInProjectGoToResultCommand(sublime_plugin.TextCommand):
    """Navigate to the file/line under the cursor in the Find Results buffer."""

    FILE_LINE_RE = re.compile(r"^(\S.*?):$")

    def run(self, edit):
        view = self.view
        window = view.window()
        if not window or not view.sel():
            return

        pt = view.sel()[0].begin()
        row, _ = view.rowcol(pt)
        line = view.substr(view.line(pt)).rstrip("\n")

        # Case 1: cursor is on a file path line
        match = self.FILE_LINE_RE.match(line)
        if match:
            file_path = match.group(1)
            if os.path.exists(file_path):
                window.open_file(file_path + ":1", sublime.ENCODED_POSITION)
            return

        # Case 2: cursor is on a result line, find the owning file
        file_path = self._find_file_path(view, row)
        if not file_path or not os.path.exists(file_path):
            return

        location = self._parse_location(line)
        if location:
            window.open_file(file_path + ":" + location, sublime.ENCODED_POSITION)

    def _find_file_path(self, view, start_row):
        for r in range(start_row - 1, -1, -1):
            line = view.substr(view.line(view.text_point(r, 0))).rstrip("\n")
            match = self.FILE_LINE_RE.match(line)
            if match:
                return match.group(1)
        return None

    def _parse_location(self, line):
        stripped = line.lstrip()
        parts = stripped.split(":", 2)
        if len(parts) >= 2:
            try:
                int(parts[0])
                int(parts[1])
                return ":".join(parts[:2])
            except ValueError:
                pass
        return None


class SearchInProjectResultsEventListener(sublime_plugin.EventListener):
    """Intercept Enter and double-click inside the Find Results buffer."""

    def on_text_command(self, view, command_name, args):
        if not view.settings().get("search_in_project_results"):
            return None
        if command_name == "insert" and args and args.get("characters") == "\n":
            return ("search_in_project_go_to_result", {})
        return None

    def on_post_text_command(self, view, command_name, args):
        if not view.settings().get("search_in_project_results"):
            return
        if command_name == "drag_select" and args and args.get("by") == "words":
            view.run_command("search_in_project_go_to_result")
