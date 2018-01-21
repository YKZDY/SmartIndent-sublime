#!/usr/bin/env python
# Copyright 2017 Calvin Gu

import os
import re
import sublime
import sublime_plugin


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
            tab_region = sublime.Region(region.begin()-1, region.begin())
            if self.view.substr(tab_region) == "\t":
                self.view.replace(edit, tab_region, " "*settings.indent_size)

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
                # Replace the first tab to spaces on each line.
                line_buffer = self.view.substr(line)[1:]
                line_buffer = line_buffer.replace(line_buffer.lstrip("\t"),
                    " "*settings.indent_size + line_buffer.lstrip("\t"))

                # Replace continuous spaces to tab.
                if settings.translate_spaces_to_tabs:
                    line_buffer = re.sub(" "*settings.tab_size, "\t", line_buffer)
                lines_buffer.append(line_buffer)

            self.view.replace(edit, region, "\n".join(lines_buffer))

            # Fix the unknown tab error on the beginning of every region.
            tab_region = sublime.Region(region.begin()-1, region.begin())
            if self.view.substr(tab_region) == "\t":
                self.view.erase(edit, tab_region)


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
        if self._trigger and cmd == "undo":
            if view.command_history(0)[0] in ("smart_indent_replace",
                "smart_indent_lines"):
                view.run_command("undo")

    def on_post_text_command(self, view, cmd, args):
        if self._trigger:
            if cmd in ("reindent", "insert_best_completion"):
                view.run_command("smart_indent_replace")

            if cmd == "run_macro_file" and args["file"] == \
                "res://Packages/Default/Add Line in Braces.sublime-macro":
                view.run_command("smart_indent_replace")

            if cmd == "insert" and args["characters"] == "\n":
                view.run_command("smart_indent_replace")

            if cmd == "indent":
                view.run_command("smart_indent_lines")
