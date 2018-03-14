#!/usr/bin/env python
# Copyright 2017 Calvin Gu

import os
import re
import sublime
import sublime_plugin


def SetLinesAtRegion(edit, view, region, lines):
    is_empty = region.empty()
    is_endswithline = view.substr(sublime.Region(region.end()-1, region.end())) == "\n"
    is_startswithline = view.substr(sublime.Region(region.begin()-1, region.begin())) == "\n"

    if is_endswithline:
        region = sublime.Region(region.begin(), region.end()-1)
    if is_startswithline:
        region = sublime.Region(region.begin()+1, region.end())

    region = view.full_line(region)

    if not is_empty:
        view.sel().add(region)

    view.replace(edit, region, "\n".join(lines) + "\n")


class SmartIndentSettings(object):
    def __init__(self):
        super(SmartIndentSettings, self).__init__()
        self.settings = sublime.load_settings("SmartIndent.sublime-settings")

    @property
    def extensions(self):
        default_exts = [".cpp", ".hpp", ".c", ".h", ".C", ".H"]
        return self.settings.get("extensions") or default_exts
    @property
    def indent_size(self):
        return self.settings.get("indent_size", 4)
    @property
    def tab_size(self):
        return self.settings.get("tab_size", 8)
    @property
    def translate_spaces_to_tabs(self):
        return self.settings.get("translate_spaces_to_tabs", True)


class SmartIndentReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = SmartIndentSettings()

        for region in self.view.sel():
            # Replace inputted tab to spaces
            point = region.begin()
            input_region = sublime.Region(region.begin()-1, region.begin())
            if self.view.substr(input_region) == "\t":
                self.view.replace(edit, input_region, " "*settings.indent_size)

            # Replace continuous spaces to tab
            if settings.translate_spaces_to_tabs:
                line = self.view.line(point)
                line_buffer = self.view.substr(line)
                line_buffer = re.sub(r" "*settings.tab_size, "\t", line_buffer)
                self.view.replace(edit, line, line_buffer)


class SmartIndentLinesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = SmartIndentSettings()

        for region in self.view.sel():
            lines_buffer = list()
            for line in self.view.lines(region):
                line_buffer = self.view.substr(line)[1:]
                if not line_buffer.strip():
                    lines_buffer.append(line_buffer)
                    continue

                # Replace the first tab to spaces on each line.
                line_buffer = line_buffer.replace(line_buffer.lstrip("\t"),
                    " "*settings.indent_size + line_buffer.lstrip("\t"))

                # Replace continuous spaces to tab.
                if settings.translate_spaces_to_tabs:
                    line_buffer = re.sub(" "*settings.tab_size, "\t", line_buffer)
                lines_buffer.append(line_buffer)

            SetLinesAtRegion(edit, self.view, region, lines_buffer)


class PreSmartUnindentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            lines_buffer = list()
            for line in self.view.lines(region):
                # Disable default unindent command by adding a tab.
                line_buffer = "\t" + self.view.substr(line)
                lines_buffer.append(line_buffer)

            SetLinesAtRegion(edit, self.view, region, lines_buffer)


class PostSmartUnindentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        def _unindent(src, tabSize, indentSize):
            if indentSize == 0:
                return src
            elif indentSize > 0:
                if src.startswith(" "):
                    return _unindent(src[1:], tabSize, indentSize-1)
                elif src.startswith("\t"):
                    return _unindent(src[1:], tabSize, indentSize-tabSize)
                else:
                    return src
            elif indentSize < 0:
                if not src.strip():
                    return src + " "*abs(indentSize)
                return src.replace(src.lstrip("\t"), " "*abs(indentSize) + src.lstrip("\t"))

        settings = SmartIndentSettings()

        for region in self.view.sel():
            lines_buffer = list()
            for line in self.view.lines(region):
                line_buffer = self.view.substr(line)
                line_buffer = _unindent(line_buffer, settings.tab_size, settings.indent_size)

                # Replace continuous spaces to tab.
                if settings.translate_spaces_to_tabs:
                    line_buffer = re.sub(" "*settings.tab_size, "\t", line_buffer)
                lines_buffer.append(line_buffer)

            SetLinesAtRegion(edit, self.view, region, lines_buffer)


class SmartIndentListener(sublime_plugin.EventListener):

    _trigger = False

    def initialize(self, view):
        settings = SmartIndentSettings()

        file_name = view.file_name() or "untitled"
        ext = os.path.splitext(file_name)[-1]
        self._trigger = ext in settings.extensions

        if self._trigger:
            view.settings().set("tab_size", settings.tab_size)
            view.settings().set("translate_tabs_to_spaces", False)

    def on_new(self, view):
        self.initialize(view)

    def on_clone(self, view):
        self.initialize(view)

    def on_load(self, view):
        self.initialize(view)
        
    def on_activated(self, view):
        self.initialize(view)

    def on_text_command(self, view, cmd, args):
        if self._trigger:
            if cmd == "undo":
                if view.command_history(0)[0] in ("smart_indent_replace",
                    "smart_indent_lines"):
                    view.run_command("undo")

                elif view.command_history(0)[0] == "post_smart_unindent":
                    view.run_command("undo")
                    view.run_command("undo")

            elif cmd == "unindent":
                view.run_command("pre_smart_unindent")

    def on_post_text_command(self, view, cmd, args):
        if self._trigger:
            if cmd in ("reindent", "insert_best_completion"):
                view.run_command("smart_indent_replace")

            elif cmd == "run_macro_file" and args["file"] == \
                "res://Packages/Default/Add Line in Braces.sublime-macro":
                view.run_command("smart_indent_replace")

            elif cmd == "insert" and args["characters"] == "\n":
                view.run_command("smart_indent_replace")

            elif cmd == "indent":
                view.run_command("smart_indent_lines")

            elif cmd == "unindent":
                view.run_command("post_smart_unindent")
