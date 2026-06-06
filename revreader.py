#!/usr/bin/env python3
import sys, os, zipfile, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from shutil import get_terminal_size
from textwrap import wrap
import argparse
import json
import hashlib
import time
from pathlib import Path

class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._in_heading = False
    def handle_starttag(self, tag, attrs):
        if tag in ("h1","h2","h3","h4","h5","h6"):
            self._in_heading = True
            self.parts.append("\n")
        if tag == "p":
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("h1","h2","h3","h4","h5","h6"):
            self._in_heading = False
            self.parts.append("\n")
    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_heading:
            self.parts.append(text.upper())
        else:
            self.parts.append(text)
    def get_text(self):
        return " ".join(self.parts).replace(" \n ", "\n").strip()

class EPUBBook:
    def __init__(self, path):
        self.path = path
        self.z = zipfile.ZipFile(path)
        self.rootfile = self._find_rootfile()
        self.opf = self._read(self.rootfile)
        self.manifest, self.spine = self._parse_opf(self.opf)
        self.base = os.path.dirname(self.rootfile)
        self.title = self._extract_title()
        self.author = self._extract_author()
        self.fonts = self._collect_fonts()
    def _read(self, name):
        return self.z.read(name)
    def _find_rootfile(self):
        data = self._read('META-INF/container.xml')
        tree = ET.fromstring(data)
        ns = {'c':'urn:oasis:names:tc:opendocument:xmlns:container'}
        rootfile = tree.find('.//c:rootfile', ns)
        return rootfile.get('full-path')
    def _parse_opf(self, data):
        tree = ET.fromstring(data)
        manifest = {}
        for item in tree.findall('.//{http://www.idpf.org/2007/opf}item'):
            manifest[item.get('id')] = item.attrib
        spine = []
        for itemref in tree.findall('.//{http://www.idpf.org/2007/opf}itemref'):
            ref = itemref.get('idref')
            if ref in manifest:
                spine.append(manifest[ref]['href'])
        return manifest, spine
    def _resolve(self, href):
        return os.path.normpath(os.path.join(self.base, href)).replace('\\','/')
    def iter_html(self):
        for href in self.spine:
            path = self._resolve(href)
            try:
                data = self._read(path).decode('utf-8',errors='ignore')
            except KeyError:
                continue
            yield path, data
    def _extract_title(self):
        try:
            tree = ET.fromstring(self.opf)
            title = tree.find('.//{http://purl.org/dc/elements/1.1/}title')
            if title is not None and title.text:
                return title.text.strip()
        except Exception:
            pass
        return os.path.splitext(os.path.basename(self.path))[0]
    def _extract_author(self):
        try:
            tree = ET.fromstring(self.opf)
            creator = tree.find('.//{http://purl.org/dc/elements/1.1/}creator')
            if creator is not None and creator.text:
                return creator.text.strip()
        except Exception:
            pass
        return None

    def _collect_fonts(self):
        fonts = []
        for name in self.z.namelist():
            if name.lower().endswith(('.ttf','.otf')):
                fonts.append(name)
        return fonts

    def get_cover_bytes(self):
        """Try to locate a cover image in the EPUB and return (bytes, mime, filename) or (None, None, None)."""
        # prefer manifest property 'cover-image' or filenames containing 'cover'
        try:
            tree = ET.fromstring(self.opf)
            # look for meta name='cover' content='id'
            cover_id = None
            for meta in tree.findall('.//{http://www.idpf.org/2007/opf}meta'):
                if meta.get('name') and meta.get('name').lower()=='cover':
                    cover_id = meta.get('content')
                    break
            if cover_id:
                for item in tree.findall('.//{http://www.idpf.org/2007/opf}item'):
                    if item.get('id')==cover_id:
                        href = item.get('href')
                        path = self._resolve(href)
                        data = self._read(path)
                        mime = item.get('media-type','image/png')
                        return data, mime, os.path.basename(href)
            # fallback: find item with media-type image and 'cover' in href
            for item in tree.findall('.//{http://www.idpf.org/2007/opf}item'):
                href = item.get('href')
                mime = item.get('media-type','')
                if mime.startswith('image/') and 'cover' in (href or '').lower():
                    path = self._resolve(href)
                    data = self._read(path)
                    return data, mime, os.path.basename(href)
            # fallback: any image in manifest
            for item in tree.findall('.//{http://www.idpf.org/2007/opf}item'):
                mime = item.get('media-type','')
                if mime.startswith('image/'):
                    href = item.get('href')
                    path = self._resolve(href)
                    data = self._read(path)
                    return data, mime, os.path.basename(href)
        except Exception:
            pass
        # lastly, scan zip for common image names
        for name in self.z.namelist():
            lname = name.lower()
            if any(p in lname for p in ('cover','cover.jpg','cover.png','cover.jpeg')) and lname.endswith(('.png','.jpg','.jpeg','.webp','.gif')):
                try:
                    data = self.z.read(name)
                    mime = 'image/png' if name.lower().endswith('.png') else 'image/jpeg'
                    return data, mime, os.path.basename(name)
                except Exception:
                    continue
        return None, None, None

class TerminalPager:
    def __init__(self, book: EPUBBook):
        self.book = book
        self.chapters = []
        for path, html in book.iter_html():
            parser = SimpleHTMLTextExtractor()
            parser.feed(html)
            text = parser.get_text()
            if text:
                self.chapters.append((os.path.basename(path), text))
        self.cur_ch = 0
        self.cur_page = 0
    def _paginate(self, text):
        cols, rows = get_terminal_size((80,24))
        max_lines = rows - 4
        lines = []
        for paragraph in text.split('\n'):
            wrapped = []
            for line in wrap(paragraph, width=cols-4):
                wrapped.append(line)
            if not wrapped:
                lines.append('')
            else:
                lines.extend(wrapped)
        pages = [lines[i:i+max_lines] for i in range(0, len(lines), max_lines)]
        if not pages:
            pages = [['']]
        return pages
    def show(self):
        while True:
            name, text = self.chapters[self.cur_ch]
            pages = self._paginate(text)
            total_pages = len(pages)
            page = pages[self.cur_page]
            os.system('clear')
            header = f"{self.book.title} — {self.cur_ch+1}/{len(self.chapters)} {name} — page {self.cur_page+1}/{total_pages}"
            print(header)
            print('-'*len(header))
            for line in page:
                print(line)
            print('\n[n]ext [p]rev [c]hapter [g]oto [q]uit')
            try:
                cmd = input('> ').strip().lower()
            except KeyboardInterrupt:
                return
            if cmd in ('n',''):
                if self.cur_page+1 < total_pages:
                    self.cur_page += 1
                else:
                    if self.cur_ch+1 < len(self.chapters):
                        self.cur_ch += 1
                        self.cur_page = 0
            elif cmd=='p':
                if self.cur_page>0:
                    self.cur_page -=1
                else:
                    if self.cur_ch>0:
                        self.cur_ch-=1
                        self.cur_page = 0
            elif cmd=='c':
                for i,(n,_) in enumerate(self.chapters,1):
                    print(f"{i}. {n}")
                sel = input('chapter> ').strip()
                try:
                    idx = int(sel)-1
                    if 0<=idx<len(self.chapters):
                        self.cur_ch = idx
                        self.cur_page = 0
                except Exception:
                    pass
            elif cmd=='g':
                sel = input('goto page> ').strip()
                try:
                    p = int(sel)-1
                    if 0<=p<total_pages:
                        self.cur_page = p
                except Exception:
                    pass
            elif cmd=='q':
                return

# GUI implementation (PySide6 / PyQt6 compatible)
def launch_gui(path=None):
    try:
        from PySide6 import QtWidgets, QtGui, QtCore
        BINDING = 'pyside6'
    except Exception:
        try:
            from PyQt6 import QtWidgets, QtGui, QtCore
            BINDING = 'pyqt6'
        except Exception:
            print('Qt not available. Install PySide6 or PyQt6 to use GUI mode.')
            return

    # create QApplication early to avoid 'Must construct a QApplication before a QWidget' errors
    try:
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_DontUseNativeDialogs, True)
    except Exception:
        pass
    app = QtWidgets.QApplication([])

    class Window(QtWidgets.QMainWindow):
        def __init__(self, epub_path=None):
            super().__init__()
            self.setWindowTitle('revreader')

            # central reader
            self.viewer = QtWidgets.QTextBrowser()
            reader_container = QtWidgets.QWidget()
            reader_layout = QtWidgets.QVBoxLayout(reader_container)
            reader_layout.setContentsMargins(10,10,10,10)
            reader_layout.addWidget(self.viewer)

            # header (no QToolBar) with Open, Back and Theme controls
            header = QtWidgets.QWidget()
            header_layout = QtWidgets.QHBoxLayout(header)
            header_layout.setContentsMargins(8,8,8,8)
            self.back_btn = QtWidgets.QPushButton('←')
            self.back_btn.setFixedHeight(28)
            self.back_btn.clicked.connect(self.go_back)
            header_layout.addWidget(self.back_btn)
            self.open_btn = QtWidgets.QPushButton('Open')
            self.open_btn.setFixedHeight(28)
            self.open_btn.clicked.connect(self.open_file)
            header_layout.addWidget(self.open_btn)
            # spacer: push following controls to the right
            header_layout.addStretch(1)
            # theme selection button (main menu)
            try:
                self.themes_btn = QtWidgets.QPushButton('Themes')
                self.themes_btn.setFixedHeight(28)
                self.themes_btn.clicked.connect(self.show_theme_dialog)
                header_layout.addWidget(self.themes_btn)
            except Exception:
                self.themes_btn = None
            # font size slider (right side) with numeric label
            try:
                self.font_container = QtWidgets.QWidget()
                fs_layout = QtWidgets.QHBoxLayout(self.font_container)
                fs_layout.setContentsMargins(0,0,0,0)
                self.font_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
                self.font_slider.setRange(10,30)
                self.font_slider.setFixedWidth(120)
                self.font_slider.setToolTip('Adjust text size')
                try:
                    self.font_val_label = QtWidgets.QLabel(str(self.read_font_size if hasattr(self,'read_font_size') else 16))
                except Exception:
                    self.font_val_label = QtWidgets.QLabel('16')
                self.font_val_label.setFixedWidth(30)
                fs_layout.addWidget(self.font_slider)
                fs_layout.addWidget(self.font_val_label)
                try:
                    self.font_container.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
                    header_layout.addWidget(self.font_container, 0, QtCore.Qt.AlignRight)
                except Exception:
                    header_layout.addWidget(self.font_container)
            except Exception:
                self.font_slider = None

            # stacked widget: library view and reader
            self.stack = QtWidgets.QStackedWidget()
            # library widget
            self.lib_widget = QtWidgets.QWidget()
            lib_layout = QtWidgets.QVBoxLayout(self.lib_widget)
            lib_layout.setContentsMargins(10,10,10,10)
            self.lib_list = QtWidgets.QListWidget()
            # Qt6 enums live under the enum class; support both bindings
            try:
                view_mode_icon = QtWidgets.QListView.ViewMode.IconMode
            except Exception:
                try:
                    view_mode_icon = QtWidgets.QListView.IconMode
                except Exception:
                    view_mode_icon = 1  # fallback to IconMode numeric value
            self.lib_list.setViewMode(view_mode_icon)
            # ResizeMode enum similarly
            try:
                resize_mode = QtWidgets.QListView.ResizeMode.Adjust
            except Exception:
                try:
                    resize_mode = QtWidgets.QListView.Adjust
                except Exception:
                    resize_mode = 0
            self.lib_list.setResizeMode(resize_mode)
            self.lib_list.setIconSize(QtCore.QSize(128,192))
            # grid cell size so cover icons show nicely
            try:
                self.lib_list.setGridSize(QtCore.QSize(150,240))
            except Exception:
                pass
            self.lib_list.itemActivated.connect(self.open_from_library)
            lib_layout.addWidget(self.lib_list)
            # Add / Remove buttons
            btn_row = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(btn_row)
            btn_layout.setContentsMargins(0,0,0,0)
            add_btn = QtWidgets.QPushButton('Add book')
            add_btn.clicked.connect(self.open_file)
            btn_layout.addWidget(add_btn)
            remove_btn = QtWidgets.QPushButton('Remove')
            remove_btn.clicked.connect(self.remove_selected)
            btn_layout.addWidget(remove_btn)
            btn_layout.addStretch(1)
            lib_layout.addWidget(btn_row)

            # add pages to stack
            self.stack.addWidget(self.lib_widget)
            self.reader_page = QtWidgets.QWidget()
            r_layout = QtWidgets.QVBoxLayout(self.reader_page)
            r_layout.setContentsMargins(0,0,0,0)
            r_layout.addWidget(reader_container)
            self.stack.addWidget(self.reader_page)

            # connect stack change to update header visibility
            try:
                self.stack.currentChanged.connect(self._on_stack_changed)
            except Exception:
                pass

            # main layout
            main_container = QtWidgets.QWidget()
            main_layout = QtWidgets.QVBoxLayout(main_container)
            main_layout.setContentsMargins(0,0,0,0)
            main_layout.addWidget(header)
            main_layout.addWidget(self.stack)
            self.setCentralWidget(main_container)

            # no TOC dock per user request
            self.toc_dock = None
            self.toc_list = None

            self.current_theme = 'light'
            self.html_parts = []
            self.css_base = ["body { margin: 20px; font-size: 14px; line-height: 1.5; }"]

            # shortcuts
            try:
                QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+O'), self).activated.connect(self.open_file)
                QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+T'), self).activated.connect(self.toggle_theme)
            except Exception:
                pass

            # library backend paths
            self.data_dir = Path.home() / '.local' / 'share' / 'revreader'
            self.covers_dir = self.data_dir / 'covers'
            self.library_file = self.data_dir / 'library.json'
            self.settings_file = self.data_dir / 'settings.json'
            self.settings = {}
            if self.settings_file.exists():
                try:
                    self.settings = json.loads(self.settings_file.read_text(encoding='utf-8'))
                except Exception:
                    self.settings = {}
            # theme presets
            self.theme_presets = {
                'Light': {'bg':'#ffffff','text':'#111111','toolbar':'#f5f5f5','body_bg':'#ffffff','link':'#1a73e8'},
                'Dark': {'bg':'#0f1115','text':'#e6eef8','toolbar':'#15171a','body_bg':'#0f1115','link':'#8ab4ff'},
                'Sepia': {'bg':'#fbf0e6','text':'#3b2f2f','toolbar':'#f0e6d8','body_bg':'#fbf0e6','link':'#8b5a00'},
                'Solarized': {'bg':'#fdf6e3','text':'#657b83','toolbar':'#eee8d5','body_bg':'#fdf6e3','link':'#268bd2'},
                'Midnight': {'bg':'#001f3f','text':'#cfe8ff','toolbar':'#002b54','body_bg':'#001f3f','link':'#66b2ff'},
                'High Contrast': {'bg':'#000000','text':'#ffffff','toolbar':'#111111','body_bg':'#000000','link':'#ffff00'}
            }
            self.current_theme = self.settings.get('theme', self.current_theme)
            # reading font size
            self.read_font_size = int(self.settings.get('font_size', 16))
            # set slider value if created
            try:
                if getattr(self, 'font_slider', None) is not None:
                    try:
                        self.font_slider.setValue(self.read_font_size)
                        self.font_slider.valueChanged.connect(self.set_font_size)
                    except Exception:
                        pass
                # ensure label reflects value
                try:
                    if hasattr(self, 'font_val_label'):
                        self.font_val_label.setText(str(self.read_font_size))
                except Exception:
                    pass
            except Exception:
                pass
            try:
                self.apply_theme()
            except Exception:
                pass

            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.covers_dir.mkdir(parents=True, exist_ok=True)
            self.library = self.load_library()
            self.populate_library()
            # show library first
            self.stack.setCurrentWidget(self.lib_widget)
            try:
                # ensure header visibility set correctly at start
                self._on_stack_changed(0)
            except Exception:
                pass

            if epub_path:
                self.load_epub(epub_path)

        def load_library(self):
            try:
                if self.library_file.exists():
                    return json.loads(self.library_file.read_text(encoding='utf-8'))
            except Exception:
                pass
            return []

        def save_library(self):
            try:
                self.library_file.write_text(json.dumps(self.library, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass

        def populate_library(self):
            self.lib_list.clear()
            for entry in self.library:
                item = QtWidgets.QListWidgetItem()
                title = entry.get('title') or entry.get('path')
                author = entry.get('author') or ''
                display = f"{title}" + (f"\n{author}" if author else "")
                item.setText(display)
                cover_path = entry.get('cover_path')
                if cover_path and Path(cover_path).exists():
                    item.setIcon(QtGui.QIcon(str(cover_path)))
                else:
                    # try to extract cover lazily
                    try:
                        if entry.get('path') and Path(entry.get('path')).exists():
                            b = EPUBBook(entry.get('path'))
                            data, mime, name = b.get_cover_bytes()
                            if data:
                                qimg = QtGui.QImage()
                                qimg.loadFromData(data)
                                thumb = qimg.scaled(240,360, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                                h = hashlib.sha256(entry.get('path').encode('utf-8')).hexdigest()
                                cover_file = self.covers_dir / f"{h}.png"
                                thumb.save(str(cover_file), 'PNG')
                                entry['cover_path'] = str(cover_file)
                                self.save_library()
                                item.setIcon(QtGui.QIcon(str(cover_file)))
                                cover_path = entry.get('cover_path')
                    except Exception:
                        pass
                    # placeholder icon — support Qt6 enum location with fallbacks
                    try:
                        sp_file_icon = QtWidgets.QStyle.StandardPixmap.SP_FileIcon
                    except Exception:
                        try:
                            sp_file_icon = QtWidgets.QStyle.SP_FileIcon
                        except Exception:
                            sp_file_icon = None
                    try:
                        if sp_file_icon is not None:
                            item.setIcon(self.style().standardIcon(sp_file_icon))
                        else:
                            item.setIcon(QtGui.QIcon())
                    except Exception:
                        item.setIcon(QtGui.QIcon())
                # store path in item user role with Qt6/Qt5 compatibility
                try:
                    user_role = QtCore.Qt.ItemDataRole.UserRole
                except Exception:
                    try:
                        user_role = QtCore.Qt.UserRole
                    except Exception:
                        user_role = 32
                item.setData(user_role, entry.get('path'))
                try:
                    item.setSizeHint(QtCore.QSize(150,220))
                except Exception:
                    pass
                self.lib_list.addItem(item)

        def add_to_library(self, path, epub_book=None):
            # avoid duplicates
            for e in self.library:
                if e.get('path')==path:
                    return
            entry = {'path': path, 'title': None, 'author': None, 'cover_path': None, 'last_opened': time.time(), 'position': 0}
            try:
                book = epub_book or EPUBBook(path)
                entry['title'] = book.title
                entry['author'] = book.author
                data, mime, name = book.get_cover_bytes()
                if data:
                    # create thumbnail using Qt
                    qimg = QtGui.QImage()
                    qimg.loadFromData(data)
                    thumb = qimg.scaled(240,360, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    # name by hash
                    h = hashlib.sha256(path.encode('utf-8')).hexdigest()
                    cover_file = self.covers_dir / f"{h}.png"
                    thumb.save(str(cover_file), 'PNG')
                    entry['cover_path'] = str(cover_file)
            except Exception:
                pass
            self.library.insert(0, entry)
            self.save_library()
            self.populate_library()

        def open_from_library(self, item):
            try:
                user_role = QtCore.Qt.ItemDataRole.UserRole
            except Exception:
                try:
                    user_role = QtCore.Qt.UserRole
                except Exception:
                    user_role = 32
            path = item.data(user_role)
            if path and os.path.isfile(path):
                self.load_epub(path)
                self.stack.setCurrentWidget(self.reader_page)

        def open_file(self):
            try:
                fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open EPUB', '', 'EPUB files (*.epub)', options=QtWidgets.QFileDialog.DontUseNativeDialog)
            except Exception:
                fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open EPUB', '', 'EPUB files (*.epub)')
            if fname:
                self.load_epub(fname)
                self.add_to_library(fname)
                self.stack.setCurrentWidget(self.reader_page)


        def toggle_theme(self):
            self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
            self.apply_theme()

        def go_back(self):
            try:
                self.stack.setCurrentWidget(self.lib_widget)
            except Exception:
                pass

        def _on_stack_changed(self, idx):
            # update header buttons depending on current page
            try:
                cur = self.stack.currentWidget()
                if cur == self.lib_widget:
                    # library view: show open/themes/remove; hide back
                    try:
                        self.back_btn.hide()
                    except Exception:
                        pass
                    try:
                        if self.open_btn: self.open_btn.show()
                    except Exception:
                        pass
                    try:
                        if self.themes_btn: self.themes_btn.show()
                    except Exception:
                        pass
                    try:
                        if hasattr(self, 'font_container') and self.font_container is not None:
                            self.font_container.show()
                        elif hasattr(self, 'font_slider') and self.font_slider is not None:
                            self.font_slider.show()
                        if hasattr(self, 'font_val_label'):
                            self.font_val_label.show()
                    except Exception:
                        pass
                else:
                    # reader view: show back; hide open/themes/remove
                    try:
                        self.back_btn.show()
                    except Exception:
                        pass
                    try:
                        if self.open_btn: self.open_btn.hide()
                    except Exception:
                        pass
                    try:
                        if self.themes_btn: self.themes_btn.hide()
                    except Exception:
                        pass
                    try:
                        if hasattr(self, 'font_container') and self.font_container is not None:
                            self.font_container.show()
                        elif hasattr(self, 'font_slider') and self.font_slider is not None:
                            self.font_slider.show()
                        if hasattr(self, 'font_val_label'):
                            self.font_val_label.show()
                    except Exception:
                        pass
            except Exception:
                pass

        def set_font_size(self, val):
            try:
                self.read_font_size = int(val)
            except Exception:
                return
            # update label
            try:
                if hasattr(self, 'font_val_label') and self.font_val_label:
                    self.font_val_label.setText(str(self.read_font_size))
            except Exception:
                pass
            # persist
            try:
                self.settings['font_size'] = self.read_font_size
                self.settings_file.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
            try:
                self.apply_theme()
            except Exception:
                pass

        def remove_selected(self):
            # remove currently selected book from library
            try:
                sel = self.lib_list.currentItem()
                if not sel:
                    sel_items = self.lib_list.selectedItems()
                    sel = sel_items[0] if sel_items else None
                if not sel:
                    return
                # obtain path
                try:
                    user_role = QtCore.Qt.ItemDataRole.UserRole
                except Exception:
                    try:
                        user_role = QtCore.Qt.UserRole
                    except Exception:
                        user_role = 32
                path = sel.data(user_role)
                # remove from library list
                newlib = [e for e in self.library if e.get('path')!=path]
                self.library = newlib
                # remove cover file if exists
                for e in list(newlib):
                    pass
                # delete cover file physically for the removed path
                try:
                    # compute hash used for cover
                    import hashlib
                    h = hashlib.sha256(path.encode('utf-8')).hexdigest()
                    for ext in ('.png','.jpg','.jpeg'):
                        f = self.covers_dir / (h+ext)
                        if f.exists():
                            try:
                                f.unlink()
                            except Exception:
                                pass
                except Exception:
                    pass
                self.save_library()
                self.populate_library()
            except Exception:
                pass

        def show_theme_dialog(self):
            dlg = QtWidgets.QDialog(self)
            dlg.setWindowTitle('Choose Theme')
            layout = QtWidgets.QVBoxLayout(dlg)
            listw = QtWidgets.QListWidget()
            for name in self.theme_presets.keys():
                listw.addItem(name)
            layout.addWidget(listw)
            btns = QtWidgets.QHBoxLayout()
            apply_btn = QtWidgets.QPushButton('Apply')
            save_btn = QtWidgets.QPushButton('Apply & Save')
            cancel_btn = QtWidgets.QPushButton('Cancel')
            btns.addWidget(apply_btn)
            btns.addWidget(save_btn)
            btns.addWidget(cancel_btn)
            layout.addLayout(btns)
            def do_apply():
                it = listw.currentItem()
                if it:
                    self.current_theme = it.text()
                    self.apply_theme()
            apply_btn.clicked.connect(do_apply)
            def do_save():
                it = listw.currentItem()
                if it:
                    self.current_theme = it.text()
                    self.settings['theme']=self.current_theme
                    try:
                        self.settings_file.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')
                    except Exception:
                        pass
                    self.apply_theme()
                    dlg.accept()
            save_btn.clicked.connect(do_save)
            cancel_btn.clicked.connect(dlg.reject)
            try:
                dlg.exec_()
            except Exception:
                dlg.exec()

        def apply_theme(self):
            # apply UI and HTML reading themes based on presets
            theme = self.theme_presets.get(self.current_theme, self.theme_presets.get('Light'))
            widget_css = f"""
    QMainWindow, QWidget {{ background: {theme['bg']}; color: {theme['text']}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; }}
    QPushButton {{ border-radius:6px; padding:6px; }}
    QTextBrowser {{ background: transparent; color: {theme['text']}; }}
    QDockWidget, QListWidget {{ background: {theme['toolbar']}; }}
    QListWidget::item {{ border: none; padding:8px; margin:6px; }}
    """
            try:
                app = QtWidgets.QApplication.instance()
                if app:
                    app.setStyleSheet(widget_css)
            except Exception:
                pass

            # HTML body theme and reading styles
            theme_vars = f"background: {theme['body_bg']}; color: {theme['text']}; a {{ color: {theme['link']}; }}"
            reading_css = f"body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 700px; margin: 30px auto; line-height:1.6; font-size:{self.read_font_size}px; padding:20px; background-clip: padding-box;}} img{{max-width:100%;height:auto;display:block;margin:12px auto;}}"
            css = "\n".join(self.css_base) + "\n" + reading_css + "\nbody {" + theme_vars + "}\n"

            content = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(self.html_parts)}</body></html>"
            self.viewer.setHtml(content)

            # theme button style (small indicator)



        def load_epub(self, path):
            import re, base64
            book = EPUBBook(path)
            # fonts handling
            embedded_fonts = []  # list of (family, css_rule)
            for name in book._collect_fonts():
                try:
                    data = book.z.read(name)
                except Exception:
                    continue
                try:
                    bq = QtCore.QByteArray(data)
                    fid = QtGui.QFontDatabase.addApplicationFontFromData(bq)
                    if fid != -1:
                        fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
                        family = fams[0] if fams else None
                    else:
                        family = None
                except Exception:
                    family = None
                # create CSS @font-face so QTextBrowser can use it reliably
                try:
                    ext = os.path.splitext(name)[1].lower()
                    if ext=='.ttf': fmt = 'truetype'
                    elif ext=='.otf': fmt = 'opentype'
                    else: fmt = 'truetype'
                    mime = 'font/ttf' if ext=='.ttf' else 'font/otf'
                    b64 = base64.b64encode(data).decode('ascii')
                    font_name = family or f'Embedded-{len(embedded_fonts)}'
                    css = "@font-face { font-family: '%s'; src: url('data:%s;base64,%s') format('%s'); }" % (font_name, mime, b64, fmt)
                except Exception:
                    css = None
                    font_name = family
                if css:
                    embedded_fonts.append((font_name, css))

            # images
            raw_images = {}
            for name in book.z.namelist():
                lname = name.lower()
                if lname.endswith(('.png','.jpg','.jpeg','.gif','.svg','.webp')):
                    try:
                        raw_images[name] = book.z.read(name)
                    except Exception:
                        pass
            resource_map = {}
            for name, raw in raw_images.items():
                lname = name.lower()
                if lname.endswith(('.jpg','.jpeg')):
                    mime = 'image/jpeg'
                elif lname.endswith('.png'):
                    mime = 'image/png'
                elif lname.endswith('.gif'):
                    mime = 'image/gif'
                elif lname.endswith('.svg'):
                    mime = 'image/svg+xml'
                elif lname.endswith('.webp'):
                    mime = 'image/webp'
                else:
                    mime = 'application/octet-stream'
                b64 = base64.b64encode(raw).decode('ascii')
                resource_map[name] = f"data:{mime};base64,{b64}"

            # build html parts and replace local resource references
            html_parts = []
            toc_titles = []
            for idx, (chpath, html) in enumerate(book.iter_html()):
                def src_repl(m):
                    q, h = m.group(1), m.group(2)
                    base = os.path.dirname(chpath)
                    candidate = os.path.normpath(os.path.join(base, h)).replace('\\','/')
                    return f'src={q}{resource_map.get(candidate, resource_map.get(h, h))}{q}'
                html = re.sub(r"src=(\"|')(.*?)\1", src_repl, html, flags=re.IGNORECASE)
                def url_repl(m):
                    inner = m.group(1).strip(' "\'')
                    base = os.path.dirname(chpath)
                    candidate = os.path.normpath(os.path.join(base, inner)).replace('\\','/')
                    resolved = resource_map.get(candidate, resource_map.get(inner, inner))
                    return f"url('{resolved}')"
                html = re.sub(r"url\(([^)]+)\)", url_repl, html, flags=re.IGNORECASE)
                # simple TOC title
                import re as _re
                m = _re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=_re.IGNORECASE|_re.DOTALL)
                if not m:
                    m = _re.search(r"<h2[^>]*>(.*?)</h2>", html, flags=_re.IGNORECASE|_re.DOTALL)
                title = _re.sub(r"<[^>]+>", '', m.group(1)).strip() if m else os.path.basename(chpath)
                toc_titles.append(title)
                anchor = f"ch_{idx}"
                html_parts.append(f"<div id=\"{anchor}\"><a name=\"{anchor}\"></a>{html}</div>")

            # insert a small front header mentioning title and author (no cover)
            try:
                front = f"<div class=\"front\"><h1>{book.title}</h1>"
                if getattr(book, 'author', None):
                    front += f"<h3>{book.author}</h3>"
                front += "</div>"
                html_parts.insert(0, front)
            except Exception:
                pass

            css_rules = []
            for name, rule in embedded_fonts:
                css_rules.append(rule)
            css_rules.append("body { margin: 20px; font-size: 14px; line-height: 1.5; }")
            # if we have embedded fonts, prefer the first
            if embedded_fonts and embedded_fonts[0][0]:
                primary = embedded_fonts[0][0]
                css_rules.append(f"body {{ font-family: '{primary}', serif; }}")
                try:
                    self.viewer.setFont(QtGui.QFont(primary, 12))
                except Exception:
                    pass

            self.html_parts = html_parts
            self.css_base = css_rules
            self.toc_titles = toc_titles
            # apply theme and show content
            self.apply_theme()

    # initialize and run
    w = Window(path)
    w.resize(900,700)
    w.show()
    app.exec()

# CLI handling
def launch_terminal(path):
    book = EPUBBook(path)
    pager = TerminalPager(book)
    pager.show()

def main():
    parser = argparse.ArgumentParser(prog='revreader',description='revreader — EPUB reader (terminal and Qt GUI)')
    parser.add_argument('-t','--terminal',action='store_true',help='run terminal mode')
    parser.add_argument('file',nargs='?',help='epub file to open')
    args = parser.parse_args()
    if not args.file:
        if args.terminal:
            print('Specify EPUB file for terminal mode: revreader -t file.epub')
            sys.exit(1)
        else:
            launch_gui()
            return
    path = args.file
    if not os.path.isfile(path):
        print('File not found:', path)
        sys.exit(1)
    if args.terminal:
        launch_terminal(path)
    else:
        launch_gui(path)

if __name__=='__main__':
    main()
