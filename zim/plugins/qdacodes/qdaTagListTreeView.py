# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>  
# Licence : GPL or same as Zim 

from __future__ import with_statement

import gtk
import pango

from zim.utils import natural_sorted
from zim.gui.widgets import SingleClickTreeView

from qdaSettings import  _NO_TAGS


class TagListTreeView(SingleClickTreeView):
    '''TreeView with a single column 'Tags' which shows all tags available
    in a QdaCodesTreeView. Selecting a tag will filter the qda codes to
    only show codes with that tag.
    '''

    _type_separator = 0
    _type_label = 1
    _type_tag = 2
    _type_untagged = 3

    def __init__(self, qda_codes):
        model = gtk.ListStore(str, int, int, int) # tag name, number of codes, type, weight
        SingleClickTreeView.__init__(self, model)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.qda_codes = qda_codes

        column = gtk.TreeViewColumn(_('Tags'))
        self.append_column(column)

        cr1 = gtk.CellRendererText()
        cr1.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cr1, True)
        column.set_attributes(cr1, text=0, weight=3) # tag name, weight

        cr2 = self.get_cell_renderer_number_of_items()
        column.pack_start(cr2, False)
        column.set_attributes(cr2, text=1) # number of codes

        self.set_row_separator_func(lambda m, i: m[i][2] == self._type_separator)

        self._block_selection_change = False
        self.get_selection().connect('changed', self.on_selection_changed)

        self.refresh(qda_codes)

    def get_tags(self):
        '''Returns current selected tags, or None for all tags'''
        tags = []
        for row in self._get_selected():
            if row[2] == self._type_tag:
                tags.append(row[0])
            elif row[2] == self._type_untagged:
                tags.append(_NO_TAGS)
        return tags or None

    def get_labels(self):
        '''Returns current selected labels'''
        labels = []
        for row in self._get_selected():
            if row[2] == self._type_label:
                labels.append(row[0])
        return labels or None

    def _get_selected(self):
        selection = self.get_selection()
        if selection:
            model, paths = selection.get_selected_rows()
            if not paths or (0,) in paths:
                return []
            else:
                return [model[path] for path in paths]
        else:
            return []

    def refresh(self, qda_codes):
        self._block_selection_change = True
        selected = [(row[0], row[2]) for row in self._get_selected()] # remember name and type

        # Rebuild model
        model = self.get_model()
        if model is None: return
        model.clear()

        n_all = self.qda_codes.get_n_codes()
        model.append((_('All Tasks'), n_all, self._type_label, pango.WEIGHT_BOLD)) # T: "tag" for showing all codes

        labels = self.qda_codes.get_labels()
        plugin = self.qda_codes.plugin
        for label in plugin.codes_labels: # explicitly keep sorting from preferences
            if label in labels :
                model.append((label, labels[label], self._type_label, pango.WEIGHT_BOLD))

        tags = self.qda_codes.get_tags()
        if _NO_TAGS in tags:
            n_untagged = tags.pop(_NO_TAGS)
            model.append((_('Untagged'), n_untagged, self._type_untagged, pango.WEIGHT_NORMAL))
            # T: label in qdacodes plugins for codes without a tag

        model.append(('', 0, self._type_separator, 0)) # separator

        for tag in natural_sorted(tags):
            model.append((tag, tags[tag], self._type_tag, pango.WEIGHT_NORMAL))

        # Restore selection
        def reselect(model, path, iter):
            row = model[path]
            name_type = (row[0], row[2])
            if name_type in selected:
                self.get_selection().select_iter(iter)

        if selected:
            model.foreach(reselect)
        self._block_selection_change = False

    def on_selection_changed(self, selection):
        if not self._block_selection_change:
            tags = self.get_tags()
            labels = self.get_labels()
            self.qda_codes.set_tag_filter(tags, labels)
