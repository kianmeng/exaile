# Copyright (C) 2008-2010 Adam Olsen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import logging
import gio
import gtk
import pango

from xl import event, settings
from xl.formatter import TrackFormatter
from xl.nls import gettext as _
from xlgui import icons
from xlgui.widgets import rating

logger = logging.getLogger(__name__)

"""
    If you want to add a column to the Playlist object, or to the view columns
    menu(s), you just define the class here and have it inherit from "Column".
    The rest will be done automatically
"""

# various column definitions
class Column(gtk.TreeViewColumn):
    id = ''
    display = ''
    renderer = gtk.CellRendererText
    size = 10 # default size
    autoexpand = False # whether to expand to fit space in Autosize mode
    datatype = str
    dataproperty = 'text'
    cellproperties = {}

    def __init__(self, container, index):
        self.container = container
        if self.__class__ == Column:
            raise NotImplementedError("Can't instantiate "
                "abstract class %s"%repr(self.__class__))
        cellr = self.renderer()
        self.extrasize = 0
        if index == 1:
            gtk.TreeViewColumn.__init__(self, self.display)
            icon_cellr = gtk.CellRendererPixbuf()
            # TODO: figure out why this returns the wrong value
            # and switch to it.
            #pbufsize = gtk.icon_size_lookup(gtk.ICON_SIZE_BUTTON)[0]
            pbufsize = icons.MANAGER.pixbuf_from_stock(gtk.STOCK_STOP).get_width()
            icon_cellr.set_fixed_size(pbufsize, pbufsize)
            icon_cellr.set_property('xalign', 0.0)
            self.extrasize = pbufsize
            self.pack_start(icon_cellr, False)
            self.pack_start(cellr, True)
            self.set_attributes(icon_cellr, pixbuf=0)
            self.set_attributes(cellr, **{self.dataproperty: index})
        else:
            gtk.TreeViewColumn.__init__(self, self.display, cellr,
                **{self.dataproperty: index})
        self.set_cell_data_func(cellr, self.data_func)
        for name, val in self.cellproperties.iteritems():
            cellr.set_property(name, val)
        try:
            cellr.set_property('ellipsize', pango.ELLIPSIZE_END)
        except TypeError: #cellr doesn't do ellipsize - eg. rating
            pass
        self.setup_sizing()

        event.add_callback(self.on_option_set, "gui_option_set")

    def on_option_set(self, typ, obj, data):
        if data in ("gui/resizable_cols", "gui/col_width_%s"%self.id):
            self.setup_sizing()

    def setup_sizing(self):
        if settings.get_option('gui/resizable_cols', False):
            self.set_resizable(True)
            self.set_expand(False)
            width = settings.get_option("gui/col_width_%s"%self.id,
                    self.size+self.extrasize)
            self.set_fixed_width(width)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        else:
            self.set_resizable(False)
            if self.autoexpand:
                self.set_expand(True)
                self.set_fixed_width(1)
                self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            else:
                self.set_expand(False)
                self.set_fixed_width(self.size+self.extrasize)
                self.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

    @classmethod
    def get_formatter(cls):
        return TrackFormatter('$%s'%cls.id)

    def data_func(self, col, cell, model, iter):
        if type(cell) == gtk.CellRendererText:
            self.container.set_cell_weight(cell, iter)

    def __repr__(self):
        return '%s(%s, %s, %s)' % (self.__class__.__name__,
            `self.id`, `self.display`, `self.size`)



class TrackNumberColumn(Column):
    size = 30
    #TRANSLATORS: Title of the track number column
    display = _('#')
    id = 'tracknumber'
    cellproperties = {'xalign': 1.0, 'width-chars': 4}

class TitleColumn(Column):
    size = 200
    display = _('Title')
    id = 'title'
    autoexpand = True

class ArtistColumn(Column):
    size = 150
    display = _('Artist')
    id = 'artist'
    autoexpand = True

class ComposerColumn(Column):
    size = 150
    display = _('Composer')
    id = 'composer'
    autoexpand = True

class AlbumColumn(Column):
    size = 150
    display = _('Album')
    id = 'album'
    autoexpand = True

class LengthColumn(Column):
    size = 50
    display = _('Length')
    id = '__length'
    cellproperties = {'xalign': 1.0}

class DiscNumberColumn(Column):
    size = 40
    display = _('Disc')
    id = 'discnumber'
    cellproperties = {'xalign': 1.0, 'width-chars': 2}

class RatingColumn(Column):
    display = _('Rating')
    renderer = rating.RatingCellRenderer
    id = '__rating'
    datatype = int
    dataproperty = 'rating'
    cellproperties = {'follow-state': False}

    def data_func(self, col, cell, model, iter):
        track = model.get_track(model.get_path(iter))
        cell.props.rating = track.get_rating()

    def get_column(self, index):
        """
            Connects to the signals of the rating cell renderer
        """
        column = Column.get_column(self, index)
        column.get_cell_renderers()[0].connect('rating-changed',
            self.on_rating_changed)

        return column

    def on_rating_changed(self, widget, path, rating):
        """
            Updates the rating of the selected track
        """
        track = self.container.model.get_track(path)
        oldrating = track.get_rating()

        if rating == oldrating:
            rating = 0

        track.set_rating(rating)
        maximum = settings.get_option('rating/maximum', 5)
        event.log_event('rating_changed', self, rating / maximum * 100)

class DateColumn(Column):
    size = 50
    display = _('Date')
    id = 'date'

class GenreColumn(Column):
    size = 100
    display = _('Genre')
    id = 'genre'
    autoexpand = True

class BitrateColumn(Column):
    size = 45
    display = _('Bitrate')
    id = '__bitrate'
    cellproperties = {'xalign': 1.0}

class IoLocColumn(Column):
    size = 200
    display = _('Location')
    id = '__loc'
    autoexpand = True

class FilenameColumn(Column):
    size = 200
    display = _('Filename')
    id = 'filename'
    autoexpand = True

class PlayCountColumn(Column):
    size = 50
    display = _('Playcount')
    id = '__playcount'
    cellproperties = {'xalign': 1.0}

class BPMColumn(Column):
    size = 50
    display = _('BPM')
    id = 'bpm'
    cellproperties = {'xalign': 1.0}

class LastPlayedColumn(Column):
    size = 10
    display = _('Last played')
    id = '__last_played'



# this is where everything gets set up, including the menu items
COLUMNS = {}
FORMATTERS = {}

items = globals()
keys = items.keys()
for key in keys:
    if 'Column' in key and key != 'Column':
        item = items[key]
        COLUMNS[item.id] = item
        FORMATTERS[item.id] = item.get_formatter()

print COLUMNS

COLUMNS_BY_DISPLAY = {}
for col in COLUMNS.values():
    COLUMNS_BY_DISPLAY[col.display] = col

def setup_menu(menu, menu_items):
    items = ['tracknumber', 'title', 'artist', 'album',
        '__length', 'genre', '__rating', 'date']

    for key in COLUMNS.keys():
        if not key in items:
            items.append(key)

    for item in items:
        col = COLUMNS[item]
        display = col.display
        if col.id == 'tracknumber':
            display = _('Track Number')
        elif col.id == 'discnumber':
            display = _('Disc Number')

        menu_item = gtk.CheckMenuItem(display)
        menu_item.set_name('%s_col' % col.id)
        menu.insert(menu_item, items.index(item))

        menu_items[col.id] = menu_item
