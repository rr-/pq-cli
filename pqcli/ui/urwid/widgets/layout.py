# Copyright (c) 2013-2016 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import typing as T

import urwid


class SupportsNext:
    """
    Classes inheriting from SupportsNext must implement the following methods:
    _select_first_selectable
    _select_last_selectable
    """

    def __init__(self, *args, **kwargs):
        self.outermost = kwargs.get("outermost", False)
        if "outermost" in kwargs:
            kwargs.pop("outermost")
        super().__init__(*args, **kwargs)


class NextMixin(SupportsNext):
    """Implements SupportsNext for urwid.Pile and urwid.Columns"""

    def _select_first_selectable(self):
        """
        select our first selectable item
        (recursively if that item SupportsNext)
        """
        i = self._first_selectable()
        self.set_focus(i)
        if isinstance(self.contents[i][0], SupportsNext):
            self.contents[i][0]._select_first_selectable()

    def _select_last_selectable(self):
        """
        select our last selectable item
        (recursively if that item SupportsNext)
        """
        i = self._last_selectable()
        self.set_focus(i)
        if isinstance(self._contents[i][0], SupportsNext):
            self.contents[i][0]._select_last_selectable()

    def _first_selectable(self):
        """return sequence number of self.contents last selectable item"""
        for j in range(0, len(self._contents)):
            if self._contents[j][0].selectable():
                return j
        return False

    def _last_selectable(self):
        """return sequence number of self._contents last selectable item"""
        for j in range(len(self._contents) - 1, -1, -1):
            if self._contents[j][0].selectable():
                return j
        return False

    def keypress(self, size, key) -> T.Optional[str]:
        key = super().keypress(size, key)

        if key == "tab":
            if (
                self.outermost
                and self.focus_position == self._last_selectable()
            ):
                self._select_first_selectable()
                return None

            for i in range(self.focus_position + 1, len(self._contents)):
                if self._contents[i][0].selectable():
                    self.set_focus(i)
                    if isinstance(self._contents[i][0], SupportsNext):
                        self._contents[i][0]._select_first_selectable()
                    return None

        elif key == "shift tab":
            if (
                self.outermost
                and self.focus_position == self._first_selectable()
            ):
                self._select_last_selectable()
                return None

            for i in range(self.focus_position - 1, 0 - 1, -1):
                if self._contents[i][0].selectable():
                    self.set_focus(i)
                    if isinstance(self._contents[i][0], SupportsNext):
                        self._contents[i][0]._select_last_selectable()
                    return None

        return key


class NPile(NextMixin, urwid.Pile):
    pass


class NColumns(NextMixin, urwid.Columns):
    pass
