﻿#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

# 2015-03-19 21:31:47
# <META http-equiv='Content-Type' content='text/html; charset=euc-kr'>

from __future__ import (unicode_literals, division, absolute_import, print_function)

import copy
from functools import partial

# 20141108 16:27:50
# from PyQt4 import QtGui
# from PyQt4.Qt import (QLabel,QTableWidgetItem, QVBoxLayout, Qt, QGroupBox, QTableWidget,
#                      QCheckBox, QAbstractItemView, QHBoxLayout, QIcon, QInputDialog)
try:
    from PyQt4 import QtGui
except ImportError:
    from PyQt5 import QtGui
try:
    from PyQt4.Qt import (QLabel, QTableWidgetItem, QVBoxLayout, Qt, QGroupBox, QTableWidget,
                          QCheckBox, QAbstractItemView, QHBoxLayout, QIcon, QInputDialog)
except ImportError:
    from PyQt5.Qt import (QLabel, QTableWidgetItem, QVBoxLayout, Qt, QGroupBox, QTableWidget,
                          QCheckBox, QAbstractItemView, QHBoxLayout, QIcon, QInputDialog)

try:
    from PyQt4.QtGui import (QSpinBox)
except ImportError:
    from PyQt5.Qt import (QSpinBox)
    
from calibre.gui2 import get_current_db, question_dialog, error_dialog

# 20141108
# from calibre.gui2.complete import MultiCompleteLineEdit
from calibre.gui2.complete2 import EditWithComplete

from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

from calibre_plugins.aladin_co_kr.common_utils import ReadOnlyTableWidgetItem

from six import text_type as unicode


__license__   = 'GPL v3'
__copyright__ = '2014, YongSeok Choi <sseeookk@gmail.com> based on the Goodreads work by Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

try:
    load_translations()
except NameError:
    pass

STORE_NAME = 'Aladin_co_kr'
KEY_CONVERT_TAG = 'convertTag'
KEY_GENRE_MAPPINGS = 'genreMappings'
KEY_GET_CATEGORY = 'getCategory'
KEY_CATEGORY_PREFIX = 'categoryPrefix'
KEY_SMALL_COVER = 'smallCover'
KEY_GET_ALL_AUTHORS = 'getAllAuthors'
KEY_APPEND_TOC = 'appendTOC'
KEY_COMMENTS_SUFFIX = 'commentsSuffix'
KEY_MAX_DOWNLOADS = 'maxDownloads'

DEFAULT_GENRE_MAPPINGS = {
    'Anthologies': ['Anthologies'],
    'Adventure': ['Adventure'],
    'Adult Fiction': ['Adult'],
    'Adult': ['Adult'],
    'Art': ['Art'],
    'Biography': ['Biography'],
    'Biography Memoir': ['Biography'],
    'Business': ['Business'],
    'Chick-lit': ['Chick-lit'],
    'Childrens': ['Childrens'],
    'Classics': ['Classics'],
    'Comics': ['Comics'],
    'Graphic Novels Comics': ['Comics'],
    'Contemporary': ['Contemporary'],
    'Cookbooks': ['Cookbooks'],
    'Crime': ['Crime'],
    'Fantasy': ['Fantasy'],
    'Feminism': ['Feminism'],
    'Gardening': ['Gardening'],
    'Gay': ['Gay'],
    'Glbt': ['Gay'],
    'Health': ['Health'],
    'History': ['History'],
    'Historical Fiction': ['Historical'],
    'Horror': ['Horror'],
    'Comedy': ['Humour'],
    'Humor': ['Humour'],
    'Inspirational': ['Inspirational'],
    'Sequential Art > Manga': ['Manga'],
    'Modern': ['Modern'],
    'Music': ['Music'],
    'Mystery': ['Mystery'],
    'Non Fiction': ['Non-Fiction'],
    'Paranormal': ['Paranormal'],
    'Religion': ['Religion'],
    'Philosophy': ['Philosophy'],
    'Politics': ['Politics'],
    'Poetry': ['Poetry'],
    'Psychology': ['Psychology'],
    'Reference': ['Reference'],
    'Romance': ['Romance'],
    'Science': ['Science'],
    'Science Fiction': ['Science Fiction'],
    'Science Fiction Fantasy': ['Science Fiction', 'Fantasy'],
    'Self Help': ['Self Help'],
    'Sociology': ['Sociology'],
    'Spirituality': ['Spirituality'],
    'Suspense': ['Suspense'],
    'Thriller': ['Thriller'],
    'Travel': ['Travel'],
    'Paranormal > Vampires': ['Vampires'],
    'War': ['War'],
    'Western': ['Western'],
    'Language > Writing': ['Writing'],
    'Writing > Essays': ['Writing'],
    'Young Adult': ['Young Adult'],
}

DEFAULT_STORE_VALUES = {
    KEY_CONVERT_TAG: False,
    KEY_GET_CATEGORY: True,
    KEY_GET_ALL_AUTHORS: False,
    KEY_GENRE_MAPPINGS: copy.deepcopy(DEFAULT_GENRE_MAPPINGS),
    KEY_SMALL_COVER: False,
    KEY_CATEGORY_PREFIX: '☞',  # ▣
    KEY_APPEND_TOC: True,
    KEY_COMMENTS_SUFFIX: '<hr /><div><div style="float:right">[aladin.co.kr]</div></div>',
    KEY_MAX_DOWNLOADS: 5
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Aladin')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


class GenreTagMappingsTableWidget(QTableWidget):
    def __init__(self, parent, all_tags):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tags_values = all_tags
    
    def populate_table(self, tag_mappings):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(tag_mappings))
        header_labels = [_('Aladin Tag'), _('Maps to Calibre Tag(s)')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)
        
        for row, genre in enumerate(sorted(tag_mappings.keys(), key=lambda s: (s.lower(), s))):
            self.populate_table_row(row, genre, sorted(tag_mappings[genre]))
        
        self.resizeColumnToContents(0)
        self.set_minimum_column_width(0, 200)
        self.setSortingEnabled(False)
        if len(tag_mappings) > 0:
            self.selectRow(0)
    
    def set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)
    
    def populate_table_row(self, row, genre, tags):
        self.setItem(row, 0, ReadOnlyTableWidgetItem(genre))
        tags_value = ', '.join(tags)
        # Add a widget under the cell just for sorting purposes
        self.setItem(row, 1, QTableWidgetItem(tags_value))
        self.setCellWidget(row, 1, self.create_tags_edit(tags_value, row))
    
    def create_tags_edit(self, value, row):
        tags_edit = EditWithComplete(self)
        tags_edit.set_add_separator(False)
        tags_edit.update_items_cache(self.tags_values)
        tags_edit.setText(value)
        # tags_edit.editingFinished.connect(partial(self.tags_editing_finished, row, tags_edit))
        return tags_edit
    
    def tags_editing_finished(self, row, tags_edit):
        # Update our underlying widget for sorting
        self.item(row, 1).setText(tags_edit.text())
    
    def get_data(self):
        tag_mappings = {}
        for row in range(self.rowCount()):
            genre = unicode(self.item(row, 0).text()).strip()
            tags_text = unicode(self.cellWidget(row, 1).text()).strip()
            tag_values = tags_text.split(',')
            tags_list = []
            for tag in tag_values:
                if len(tag.strip()) > 0:
                    tags_list.append(tag.strip())
            tag_mappings[genre] = tags_list
        return tag_mappings
    
    def select_genre(self, genre_name):
        for row in range(self.rowCount()):
            if unicode(self.item(row, 0).text()) == genre_name:
                self.setCurrentCell(row, 1)
                return
    
    def get_selected_genre(self):
        if self.currentRow() >= 0:
            return unicode(self.item(self.currentRow(), 0).text())


class ConfigWidget(DefaultConfigWidget):
    
    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        c = plugin_prefs[STORE_NAME]
        all_tags = get_current_db().all_tags()
        
        self.gb.setMaximumHeight(80)
        genre_group_box = QGroupBox(_('Aladin tag to Calibre tag mappings'), self)
        self.l.addWidget(genre_group_box, self.l.rowCount(), 0, 1, 2)
        genre_group_box_layout = QVBoxLayout()
        genre_group_box.setLayout(genre_group_box_layout)
        
        # Aladin tag convert to calibre tag 20140312
        self.get_convert_tag_checkbox = QCheckBox(_('Convert Aladin tag to Calibre tag'), self)
        self.get_convert_tag_checkbox.setToolTip(_('Convert Aladin tag(korean tag) to Calibre tag.'))
        self.get_convert_tag_checkbox.setChecked(c.get(KEY_CONVERT_TAG, DEFAULT_STORE_VALUES[KEY_CONVERT_TAG]))
        genre_group_box_layout.addWidget(self.get_convert_tag_checkbox)
        
        tags_layout = QHBoxLayout()
        genre_group_box_layout.addLayout(tags_layout)
        
        self.edit_table = GenreTagMappingsTableWidget(self, all_tags)
        tags_layout.addWidget(self.edit_table)
        button_layout = QVBoxLayout()
        tags_layout.addLayout(button_layout)
        add_mapping_button = QtGui.QToolButton(self)
        add_mapping_button.setToolTip(_('Add genre mapping'))
        add_mapping_button.setIcon(QIcon(I('plus.png')))
        add_mapping_button.clicked.connect(self.add_mapping)
        button_layout.addWidget(add_mapping_button)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem1)
        remove_mapping_button = QtGui.QToolButton(self)
        remove_mapping_button.setToolTip(_('Delete genre mapping'))
        remove_mapping_button.setIcon(QIcon(I('minus.png')))
        remove_mapping_button.clicked.connect(self.delete_mapping)
        button_layout.addWidget(remove_mapping_button)
        spacerItem3 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem3)
        rename_genre_button = QtGui.QToolButton(self)
        rename_genre_button.setToolTip(_('Rename Aladin genre'))
        rename_genre_button.setIcon(QIcon(I('edit-undo.png')))
        rename_genre_button.clicked.connect(self.rename_genre)
        button_layout.addWidget(rename_genre_button)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem2)
        reset_defaults_button = QtGui.QToolButton(self)
        reset_defaults_button.setToolTip(_('Reset to plugin default mappings'))
        reset_defaults_button.setIcon(QIcon(I('clear_left.png')))
        reset_defaults_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_defaults_button)
        self.l.setRowStretch(self.l.rowCount() - 1, 2)
        
        other_group_box = QGroupBox(_('Other options'), self)
        self.l.addWidget(other_group_box, self.l.rowCount(), 0, 1, 2)
        other_group_box_layout = QVBoxLayout()
        other_group_box.setLayout(other_group_box_layout)
        
        # DID: category | v0.1.0 20140315
        self.get_category_checkbox = QCheckBox(_('Add Aladin Categories to Calibre tags'), self)
        self.get_category_checkbox.setToolTip(
            _('Add Aladin Categories to Calibre tags.\n'
              'This Plugin will change delimiter ">" to delimiter "." for Category Hierarchy.\n '
              '(ex, "Category Prefix"History.Korea Culture.History Journey)\n '))
        self.get_category_checkbox.stateChanged.connect(self.get_category_checkbox_changed)
        other_group_box_layout.addWidget(self.get_category_checkbox)
        
        self.category_group_box = QGroupBox(self)
        category_group_box_layout = QtGui.QGridLayout()
        self.category_group_box.setLayout(category_group_box_layout)
        other_group_box_layout.addWidget(self.category_group_box)
        
        # DID: 주제분류 category - 머리글  | v0.2.0 20140330
        category_prefix_label = QtGui.QLabel(_('Category Prefix'), self)
        category_prefix_label.setToolTip(_('Set strings before categories to distinguish other tags.\n'
                                           '(예, ☞History.Korea Culture.History Journey)\n '))
        category_group_box_layout.addWidget(category_prefix_label, 0, 0, 1, 1)
        self.category_prefix_edit = QtGui.QLineEdit(self)
        self.category_prefix_edit.setText(c.get(KEY_CATEGORY_PREFIX, DEFAULT_STORE_VALUES[KEY_CATEGORY_PREFIX]))
        category_group_box_layout.addWidget(self.category_prefix_edit, 0, 1, 1, 1)
        
        self.get_category_checkbox.setChecked(c.get(KEY_GET_CATEGORY, DEFAULT_STORE_VALUES[KEY_GET_CATEGORY]))
        
        # DID: 책표지(cover)를 큰것/작은것(big/small) 선택할 수 있도록 하자. | v0.2.0 20140330
        self.small_cover_checkbox = QCheckBox(_('Download small cover.'), self)
        self.small_cover_checkbox.setToolTip(_('Download small cover from aladin.'))
        self.small_cover_checkbox.setChecked(c.get(KEY_SMALL_COVER, DEFAULT_STORE_VALUES[KEY_SMALL_COVER]))
        other_group_box_layout.addWidget(self.small_cover_checkbox)
        
        self.all_authors_checkbox = QCheckBox(_('Get all contributing authors (e.g. illustrators, series editors etc)'),
                                              self)
        self.all_authors_checkbox.setToolTip(
            _('Aladin for some books will list all of the contributing authors and\n'
              'the type of contribution like (Editor), (Illustrator) etc.\n\n'
              'When this option is checked, all contributing authors are retrieved.\n\n'
              'When unchecked (default) only the primary author(s) are returned which\n'
              'are those that either have no contribution type specified, or have the\n'
              'value of (Aladin Author).\n\n'
              'If there is no primary author then only those with the same contribution\n'
              'type as the first author are returned.\n'
              'e.g. "A, B (Illustrator)" will return author A\n'
              'e.g. "A (Aladin Author)" will return author A\n'
              'e.g. "A (Editor), B (Editor), C (Illustrator)" will return authors A & B\n'
              'e.g. "A (Editor), B (Series Editor)" will return author A\n '))
        self.all_authors_checkbox.setChecked(c.get(KEY_GET_ALL_AUTHORS, DEFAULT_STORE_VALUES[KEY_GET_ALL_AUTHORS]))
        other_group_box_layout.addWidget(self.all_authors_checkbox)
        
        # Add by sseeookk, 20140315
        self.toc_checkbox = QCheckBox(
            _('Append TOC from Aladin TOC if available to comments'), self)
        self.toc_checkbox.setToolTip(
            _('Aladin for textbooks on their website have a Features which\n'
              'contains a table of contents for the book. Checking this option will\n'
              'append the TOC to the bottom of the Synopsis in the comments field'))
        self.toc_checkbox.setChecked(c.get(KEY_APPEND_TOC, DEFAULT_STORE_VALUES[KEY_APPEND_TOC]))
        other_group_box_layout.addWidget(self.toc_checkbox)
        
        # DID: 책소개(comment) 끝에 출처를 적으면 어떨까? | v0.2.0 20140330
        #       코멘트 뒤에 붙을 내용 (예, aladin.co.kr{날짜}) 
        comments_suffix_label = QLabel(_('Append comments suffix:'), self)
        comments_suffix_label.setToolTip(_('Append comments source after comments.\n'
                                           '(ex, <hr /><div><div style="float:right">[aladin.co.kr]</div></div>)\n '))
        other_group_box_layout.addWidget(comments_suffix_label)
        self.comments_suffix_edit = QtGui.QLineEdit(self)
        self.comments_suffix_edit.setText(c.get(KEY_COMMENTS_SUFFIX, DEFAULT_STORE_VALUES[KEY_COMMENTS_SUFFIX]))
        other_group_box_layout.addWidget(self.comments_suffix_edit)
        
        max_label = QLabel(_('Maximum title/author search matches to evaluate (1 = fastest):'), self)
        max_label.setToolTip(_('Increasing this value will take effect when doing\n'
                               'title/author searches to consider more books.\n '))
        other_group_box_layout.addWidget(max_label)
        self.max_downloads_spin = QtGui.QSpinBox(self)
        self.max_downloads_spin.setMinimum(1)
        self.max_downloads_spin.setMaximum(20)
        self.max_downloads_spin.setProperty('value', c.get(KEY_MAX_DOWNLOADS, DEFAULT_STORE_VALUES[KEY_MAX_DOWNLOADS]))
        other_group_box_layout.addWidget(self.max_downloads_spin)
        
        self.edit_table.populate_table(c[KEY_GENRE_MAPPINGS])
    
    def commit(self):
        DefaultConfigWidget.commit(self)
        new_prefs = {}
        new_prefs[KEY_CONVERT_TAG] = self.get_convert_tag_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_GENRE_MAPPINGS] = self.edit_table.get_data()
        new_prefs[KEY_GET_CATEGORY] = self.get_category_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_CATEGORY_PREFIX] = unicode(self.category_prefix_edit.text())
        new_prefs[KEY_SMALL_COVER] = self.small_cover_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_GET_ALL_AUTHORS] = self.all_authors_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_APPEND_TOC] = self.toc_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_COMMENTS_SUFFIX] = str(self.comments_suffix_edit.text())
        new_prefs[KEY_MAX_DOWNLOADS] = int(unicode(self.max_downloads_spin.value()))
        plugin_prefs[STORE_NAME] = new_prefs
    
    def get_category_checkbox_changed(self):
        if self.get_category_checkbox.checkState() == Qt.Checked:
            self.category_prefix_edit.setEnabled(True)
        else:
            self.category_prefix_edit.setEnabled(False)
    
    def add_mapping(self):
        new_genre_name, ok = QInputDialog.getText(self, 'Add new mapping',
                                                  'Enter a Aladin tag name to create a mapping for:', text='')
        if not ok:
            # Operation cancelled
            return
        new_genre_name = unicode(new_genre_name).strip()
        if not new_genre_name:
            return
        # Verify it does not clash with any other mappings in the list
        data = self.edit_table.get_data()
        for genre_name in data.keys():
            if genre_name.lower() == new_genre_name.lower():
                return error_dialog(self, 'Add Failed', 'A genre with the same name already exists', show=True)
        data[new_genre_name] = []
        self.edit_table.populate_table(data)
        self.edit_table.select_genre(new_genre_name)
    
    def delete_mapping(self):
        if not self.edit_table.selectionModel().hasSelection():
            return
        if not question_dialog(self,
                               _('Are you sure?'),
                               '<p>Are you sure you want to delete the selected genre mappings?',
                               show_copy_button=False):
            return
        for row in reversed(sorted(self.edit_table.selectionModel().selectedRows())):
            self.edit_table.removeRow(row.row())
    
    def rename_genre(self):
        selected_genre = self.edit_table.get_selected_genre()
        if not selected_genre:
            return
        new_genre_name, ok = QInputDialog.getText(self, 'Add new mapping',
                                                  'Enter a Aladin genre name to create a mapping for:',
                                                  text=selected_genre)
        if not ok:
            # Operation cancelled
            return
        new_genre_name = unicode(new_genre_name).strip()
        if not new_genre_name or new_genre_name == selected_genre:
            return
        data = self.edit_table.get_data()
        if new_genre_name.lower() != selected_genre.lower():
            # Verify it does not clash with any other mappings in the list
            for genre_name in data.keys():
                if genre_name.lower() == new_genre_name.lower():
                    return error_dialog(self, 'Rename Failed', 'A genre with the same name already exists', show=True)
        data[new_genre_name] = data[selected_genre]
        del data[selected_genre]
        self.edit_table.populate_table(data)
        self.edit_table.select_genre(new_genre_name)
    
    def reset_to_defaults(self):
        if not question_dialog(self,
                               _('Are you sure?'),
                               '<p>Are you sure you want to reset to the plugin default genre mappings?',
                               show_copy_button=False):
            return
        self.edit_table.populate_table(DEFAULT_GENRE_MAPPINGS)
