#!/usr/bin/env python3
import sys, os, zipfile, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from shutil import get_terminal_size
from textwrap import wrap
import argparse

# Terminal reader (kept simple)
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
    def _collect_fonts(self):
        fonts = []
        for name in self.z.namelist():
            if name.lower().endswith(('.ttf','.otf')):
                fonts.append(name)
        return fonts

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

            # header (no QToolBar) with Open and Theme
            header = QtWidgets.QWidget()
            header_layout = QtWidgets.QHBoxLayout(header)
            header_layout.setContentsMargins(8,8,8,8)
            self.open_btn = QtWidgets.QPushButton('Open')
            self.open_btn.setFixedHeight(28)
            self.open_btn.clicked.connect(self.open_file)
            header_layout.addWidget(self.open_btn)
            header_layout.addStretch(1)
            self.theme_btn = QtWidgets.QPushButton('')
            self.theme_btn.setFixedSize(20,20)
            self.theme_btn.setFlat(True)
            self.theme_btn.clicked.connect(self.toggle_theme)
            header_layout.addWidget(self.theme_btn)

            # main layout
            main_container = QtWidgets.QWidget()
            main_layout = QtWidgets.QVBoxLayout(main_container)
            main_layout.setContentsMargins(0,0,0,0)
            main_layout.addWidget(header)
            main_layout.addWidget(reader_container)
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

            if epub_path:
                self.load_epub(epub_path)

        def open_file(self):
            try:
                fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open EPUB', '', 'EPUB files (*.epub)', options=QtWidgets.QFileDialog.DontUseNativeDialog)
            except Exception:
                fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open EPUB', '', 'EPUB files (*.epub)')
            if fname:
                self.load_epub(fname)


        def toggle_theme(self):
            self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
            self.apply_theme()

        def apply_theme(self):
            light = {'bg':'#ffffff','text':'#111111','toolbar':'#f5f5f5'}
            dark = {'bg':'#0f1115','text':'#e6eef8','toolbar':'#15171a'}
            theme = dark if self.current_theme == 'dark' else light
            widget_css = f"""
QMainWindow, QWidget {{ background: {theme['bg']}; color: {theme['text']}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; }}
QPushButton {{ border-radius:6px; padding:6px; }}
QTextBrowser {{ background: transparent; color: {theme['text']}; }}
QDockWidget, QListWidget {{ background: {theme['toolbar']}; }}
"""
            try:
                app = QtWidgets.QApplication.instance()
                if app:
                    app.setStyleSheet(widget_css)
            except Exception:
                pass
            # HTML body theme
            light_vars = "background: #ffffff; color: #111111; a { color: #1a73e8; }"
            dark_vars = "background: #0f1115; color: #e6eef8; a { color: #8ab4ff; }"
            theme_vars = dark_vars if self.current_theme == 'dark' else light_vars
            css = "\n".join(self.css_base) + "\nbody {" + theme_vars + "}\n"
            content = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(self.html_parts)}</body></html>"
            self.viewer.setHtml(content)
            # theme button style
            try:
                if self.current_theme == 'light':
                    self.theme_btn.setStyleSheet('background:#ffffff; border:1px solid #ccc; border-radius:10px;')
                else:
                    self.theme_btn.setStyleSheet('background:#111; border:1px solid #444; border-radius:10px;')
            except Exception:
                pass

        def load_epub(self, path):
            import re, base64
            book = EPUBBook(path)
            families = []
            raw_images = {}
            for name in book.z.namelist():
                lname = name.lower()
                if lname.endswith(('.ttf','.otf')):
                    try:
                        data = book.z.read(name)
                        QtGui.QFontDatabase.addApplicationFontFromData(QtCore.QByteArray(data))
                    except Exception:
                        pass
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
            self.html_parts = html_parts
            self.css_base = ["body { margin: 20px; font-size: 14px; line-height: 1.5; }"]
            self.toc_titles = toc_titles
            # apply theme and show content
            self.apply_theme()

    # initialize app
    try:
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_DontUseNativeDialogs, True)
    except Exception:
        pass
    app = QtWidgets.QApplication([])
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
