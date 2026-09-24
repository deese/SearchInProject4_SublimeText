Just in case you found this project by accident you have to know that.. 


# Search in Project 4

![Search in Project screencast](https://raw.githubusercontent.com/deese/SearchInProject4_SublimeText/screencast/screencast.gif)

This plugin for [Sublime Text 4 Build 4500 or higher](http://www.sublimetext.com/) lets you use your favorite search tool (`grep`, `ack`, `ag`, `pt`, `rg`, `git grep`, or `findstr`) to find strings across your entire current Sublime Text project.

It opens a quick selection panel to browse results, highlights matches inside files, and supports double-clicking results to jump directly to the matching line.

## Usage

1. Call **Search in Project 4: Search** from the command palette, or use a key binding (see [Key Bindings](#key-bindings) below).
2. An options panel appears first, letting you toggle **Case sensitive** and **Use regex** before searching. Select **→ Search...** to proceed.
3. Enter the search query and hit `Enter`.
4. A quick panel lists the results. Select any entry to open the file at the matching line. The search string is highlighted with an outline and a circle symbol in the gutter.
5. The first item in the quick panel is **— List all results in view —**. Select it to open all results in a dedicated editor view. From that view, press `Enter` or double-click any result line to navigate to it.

If you select text before running Search in Project, the selection is pre-filled as the search query. For example, to search for a word project-wide: `⌘D, ⌘⌥⇧F, ↩`.

If you run Search in Project again, the last search string is remembered, so repeating a search is just `↩` away.

### Search options

By default the search runs immediately after you enter the query. You can enable an options panel that appears before each search by setting `search_in_project_show_options_panel` to `true` in your user settings:

```json
{
  "search_in_project_show_options_panel": true
}
```

When enabled, the options panel lets you toggle search options before entering the query:

| Option | Description |
|---|---|
| Case sensitive | Match exact casing. Off by default. |
| Use regex | Treat the query as a regular expression. Off by default. |

Options are persisted between searches. They can also be set directly in user settings via `search_in_project_case_sensitive` and `search_in_project_use_regex`.

## Installation

[Package Control](http://sublime.wbond.net): add `https://raw.githubusercontent.com/deese/SearchInProject4_SublimeText/master/repository.json` as a repository, then install package **Search in Project 4**.

Manual installation: download an [archive of the repository](https://github.com/deese/SearchInProject4_SublimeText/archive/master.zip) and unzip into the Sublime Text Packages folder.

### Search engines

| Name | Description | Key |
|---|---|---|
| **[ripgrep](https://github.com/BurntSushi/ripgrep)** | **Extremely fast, recommended.** | `ripgrep` |
| **[pt (The Platinum Searcher)](https://github.com/monochromegane/the_platinum_searcher)** | **Fast, binaries for every platform.** | `the_platinum_searcher` |
| **[ag (The Silver Searcher)](http://geoff.greer.fm/ag/)** | **Equally fast, 3rd party binaries on Windows.** | `the_silver_searcher` |
| [ack](http://beyondgrep.com/) | Requires Perl, not ideal on Windows. | `ack` |
| [git grep](http://git-scm.com/docs/git-grep) | Bundled with Git, only works in Git repos. | `git_grep` |
| [grep](https://en.wikipedia.org/wiki/Grep) | Available on Linux/macOS. | `grep` |
| [findstr](https://technet.microsoft.com/en-us/library/Bb490907.aspx) | Built-in on Windows. Default on Windows if no engine is set. | `findstr` |

Set the engine in settings via `search_in_project_engine`. Leave empty to use the platform default (`findstr` on Windows, `grep` on Linux/macOS).

## Configuration

Open `Preferences → Package Settings → Search in Project 4 → Settings` to edit your user configuration. The left panel shows all available options with their defaults.

Key settings:

| Setting | Default | Description |
|---|---|---|
| `search_in_project_engine` | `""` | Engine to use. Empty = platform default. |
| `search_in_project_show_options_panel` | `false` | Show the options panel before each search. |
| `search_in_project_case_sensitive` | `false` | Case-sensitive search. |
| `search_in_project_use_regex` | `false` | Treat query as a regular expression. |
| `search_in_project_show_list_by_default` | `false` | Always open results in a view instead of quick panel. |
| `search_in_project_max_quick_panel_results` | `100` | Switch to results view automatically above this count. |

Per-engine paths and options are configured under `search_in_project_engines`:

```json
{
  "search_in_project_engines": {
    "ripgrep": {
      "path": "rg",
      "mandatory_options": "--column --no-heading --color never",
      "common_options": ""
    }
  }
}
```

## Issues with locating executables

On macOS, if Search in Project cannot find an executable, install the [Fix Mac Path plugin](https://github.com/int3h/SublimeFixMacPath).

You can always set the full path in `search_in_project_engines.<engine>.path` as a fallback.

## Key Bindings

No key bindings are active by default to avoid conflicts with other packages.

Suggested bindings are included in [`Example.sublime-keymap`](Example.sublime-keymap):

- **Windows/Linux:** `Ctrl+Alt+Shift+F`
- **macOS:** `⌥⌘⇧F`

To activate one, open `Preferences → Package Settings → Search in Project 4 → Key Bindings`, copy the matching line for your platform from the left panel to your user keymap on the right.

---

Originally made by [Leonid Shevtsov](http://leonid.shevtsov.me)

ST4 version by Javi/DeeSe
