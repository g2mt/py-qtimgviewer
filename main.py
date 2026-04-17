#!/usr/bin/env python3
"""PySide6 Image Viewer - A simple image viewer with thumbnail sidebar and image display."""
import faulthandler, signal
faulthandler.register(signal.SIGUSR1)

import sys, os, hashlib, platform, csv, re
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from queue import Queue

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QSplitter, QScrollArea, QSizePolicy, QListView, QMessageBox, QTabWidget,
    QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtCore import (
    Qt, QSize, Signal, QTimer, QThread, Slot, QSettings,
    QAbstractListModel, QModelIndex, QUrl, QObject
)
from PySide6.QtGui import QPixmap, QIcon

# https://stackoverflow.com/a/4836734
def natural_sorted(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


@dataclass
class ConfigModel:
    """Configuration model dataclass."""
    image_directory: str = str(Path.home() / "Pictures")
    tags_path: str = str(Path.home() / "Pictures" / "tags.txt")
    tags_path_replace: str = ""


class Config:
    """Configuration manager using QSettings."""
    ORGANIZATION = "QtImgViewer"
    APPLICATION = "ImageViewer"
    
    @classmethod
    def load(cls) -> ConfigModel:
        s = QSettings(cls.ORGANIZATION, cls.APPLICATION)
        default = ConfigModel()
        return ConfigModel(
            image_directory=s.value("image_directory", default.image_directory, type=str),
            tags_path=s.value("tags_path", default.tags_path, type=str),
            tags_path_replace=s.value("tags_path_replace", default.tags_path_replace, type=str)
        )
    
    @classmethod
    def save(cls, model: ConfigModel):
        s = QSettings(cls.ORGANIZATION, cls.APPLICATION)
        for key, value in asdict(model).items():
            if value:
                s.setValue(key, value)
        s.sync()


class TagLoader:
    """Utility class for loading and parsing tag CSV files."""
    
    @staticmethod
    def parse_path_replacement(path_replace: str) -> tuple[str, str]:
        if not path_replace or ":" not in path_replace:
            return "", ""
        return tuple(path_replace.split(":", 1))
    
    @staticmethod
    def apply_path_replacement(path: str, replace_from: str, replace_to: str) -> str:
        return path.replace(replace_from, replace_to) if replace_from else path
    
    @staticmethod
    def load_tag_data(tags_path: str, path_replace: str = "") -> tuple[defaultdict[str, set[str]], set[str]]:
        tag_to_paths: defaultdict[str, set[str]] = defaultdict(set)
        all_tags: set[str] = set()
        
        if not tags_path or not os.path.isfile(tags_path):
            return tag_to_paths, all_tags
        
        replace_from, replace_to = TagLoader.parse_path_replacement(path_replace)
        
        try:
            with open(tags_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f, escapechar='\\')
                for row in reader:
                    if not row or not row[0].strip():
                        continue
                    
                    image_path = TagLoader.apply_path_replacement(row[0].strip(), replace_from, replace_to)
                    
                    for tag in row[1:]:
                        tag = tag.strip()
                        if tag:
                            all_tags.add(tag)
                            tag_to_paths[tag].add(image_path)
        except Exception:
            pass
        
        return tag_to_paths, all_tags


class ImageFilter(QObject):
    """Class for managing image filtering by name and tags."""
    
    filter_changed = Signal()
    
    # Sort function hashmap
    SORT_FUNCTIONS = {
        "name": lambda p: os.path.basename(p).lower(),
        "date_created": lambda p: os.path.getctime(p),
        "date_modified": lambda p: os.path.getmtime(p),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tag_to_paths: defaultdict[str, set[str]] = defaultdict(set)
        self._selected_tags: set[str] = set()
        self._filter_text: str = ""
        self._sort_by: str = "name"
        self._sort_descending: bool = False
        self._natural_sort: bool = False
    
    def load_tags(self, tags_path: str, path_replace: str = ""):
        self._tag_to_paths.clear()
        self._tag_to_paths, _ = TagLoader.load_tag_data(tags_path, path_replace)
    
    def set_filter_text(self, filter_text: str):
        self._filter_text = filter_text.lower().strip()
        self.filter_changed.emit()
    
    def set_selected_tags(self, tags: set[str]):
        self._selected_tags = tags
        self.filter_changed.emit()
    
    def set_sort_by(self, sort_by: str):
        self._sort_by = sort_by
        self.filter_changed.emit()
    
    def set_sort_descending(self, descending: bool):
        self._sort_descending = descending
        self.filter_changed.emit()
    
    def set_natural_sort(self, natural: bool):
        self._natural_sort = natural
        self.filter_changed.emit()
    
    def get_filtered_paths(self, all_paths: list[str]) -> list[str]:
        # Apply text filter
        filtered = [p for p in all_paths if self._filter_text in os.path.basename(p).lower()] if self._filter_text else all_paths
        
        # Apply tag filter (intersection of all selected tags)
        if self._selected_tags:
            matching_paths = set(filtered)
            for tag in self._selected_tags:
                matching_paths &= self._tag_to_paths.get(tag, set())
            filtered = list(matching_paths)
        
        # Apply sorting
        sort_key = self.SORT_FUNCTIONS.get(self._sort_by, self.SORT_FUNCTIONS["name"])
        reverse = self._sort_descending
        if self._natural_sort:
            # Get the sorted list first, then apply natural sort to the filenames
            sorted_list = sorted(filtered, key=sort_key, reverse=reverse)
            return natural_sorted(sorted_list)
        return sorted(filtered, key=sort_key, reverse=reverse)
    
    def get_all_tags(self) -> set[str]:
        return set(self._tag_to_paths.keys())


class ThumbnailLoader(QThread):
    """Thread for loading image thumbnails asynchronously on demand."""
    
    thumbnail_loaded = Signal(str, QPixmap)
    THUMBNAIL_SIZE = 128
    THUMBNAIL_CATEGORY = "normal"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._is_linux = platform.system() == "Linux"
        self._request_queue = Queue()
        self._loaded_paths = set()
    
    def _get_native_thumbnail_path(self, image_path: str) -> Optional[str]:
        if not self._is_linux:
            return None
        try:
            uri = QUrl.fromLocalFile(os.path.abspath(image_path)).toString()
            md5_hash = hashlib.md5(uri.encode('utf-8')).hexdigest()
            xdg_cache = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
            thumb_path = os.path.join(xdg_cache, 'thumbnails', self.THUMBNAIL_CATEGORY, f"{md5_hash}.png")
            return thumb_path if os.path.isfile(thumb_path) else None
        except Exception:
            return None
    
    def request_thumbnails(self, image_paths: list):
        for path in (image_paths if isinstance(image_paths, list) else [image_paths]):
            if path not in self._loaded_paths:
                self._request_queue.put(path)
    
    def run(self):
        while self._is_running:
            try:
                image_path = self._request_queue.get(timeout=0.1)
                if image_path in self._loaded_paths:
                    continue
                self._loaded_paths.add(image_path)
                
                # Try native thumbnail first, then manual resize
                native_path = self._get_native_thumbnail_path(image_path)
                thumbnail = QPixmap(native_path) if native_path else None
                
                if not thumbnail or thumbnail.isNull():
                    if pixmap := QPixmap(image_path):
                        if not pixmap.isNull():
                            thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                if thumbnail and not thumbnail.isNull():
                    self.thumbnail_loaded.emit(image_path, thumbnail)
            except:
                continue
    
    def stop(self):
        self._is_running = False
        self.wait()


class DirectoryListWidget(QListWidget):
    """Custom list widget for displaying directories."""
    
    directory_activated = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.directory_to_item = OrderedDict()
        self.setIconSize(QSize(20, 20))
        self.setSpacing(2)
        self.setViewMode(QListWidget.ListMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QListWidget::item { padding: 2px 5px; }")
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        path = next((p for p, i in self.directory_to_item.items() if i is item), None)
        if path:
            self.directory_activated.emit(path)
    
    def load_directories(self, directory: str):
        self.clear()
        self.directory_to_item.clear()
        
        if not os.path.isdir(directory):
            return
        
        # Add parent directory option if not at root
        parent_dir = os.path.dirname(directory)
        if parent_dir != directory:
            item = QListWidgetItem(".. (parent)")
            item.setToolTip(parent_dir)
            self.addItem(item)
            self.directory_to_item[parent_dir] = item
        
        # Get subdirectories
        try:
            for entry in os.scandir(directory):
                if entry.is_dir() and not entry.name.startswith('.'):
                    item = QListWidgetItem(entry.name)
                    item.setToolTip(entry.path)
                    self.addItem(item)
                    self.directory_to_item[entry.path] = item
        except PermissionError:
            pass
    

class TagsListWidget(QListWidget):
    """Custom list widget for displaying tags from a CSV file."""

    tags_selected = Signal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(20, 20))
        self.setSpacing(2)
        self.setViewMode(QListWidget.ListMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QListWidget::item { padding: 2px 5px; }")
        self.setSelectionMode(QListWidget.MultiSelection)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_tags(self, tags_path: str, path_replace: str = ""):
        self.clear()
        _, all_tags = TagLoader.load_tag_data(tags_path, path_replace)
        for tag in sorted(all_tags):
            self.addItem(QListWidgetItem(tag))

    def filter_tags(self, filter_text: str):
        """Filter tags based on the given text."""
        filter_text = filter_text.lower().strip()
        
        # Hide items that don't match
        for i in range(self.count()):
            item = self.item(i)
            tag_text = item.text().lower()
            if filter_text and filter_text not in tag_text:
                item.setHidden(True)
            else:
                item.setHidden(False)

    def _on_selection_changed(self):
        self.tags_selected.emit({item.text() for item in self.selectedItems()})


class ThumbnailModel(QAbstractListModel):
    """Model for managing image thumbnails with dynamic loading."""
    
    thumbnail_loaded = Signal(str, QPixmap)
    BATCH_SIZE = 20
    
    def __init__(self, image_filter: ImageFilter, parent=None):
        super().__init__(parent)
        self._all_image_files = []
        self._loaded_count = 0
        self._thumbnails = {}
        self.loader = None
        self._image_filter = image_filter
        self.current_directory = None
    
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._loaded_count
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= self._loaded_count:
            return None
        
        image_path = self._all_image_files[index.row()]
        return {
            Qt.DisplayRole: os.path.basename(image_path),
            Qt.ToolTipRole: image_path,
            Qt.DecorationRole: self._thumbnails.get(image_path),
            Qt.UserRole: image_path
        }.get(role)
    
    def canFetchMore(self, parent=QModelIndex()):
        return not parent.isValid() and self._loaded_count < len(self._all_image_files)
    
    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return
        
        remainder = len(self._all_image_files) - self._loaded_count
        items_to_fetch = min(remainder, self.BATCH_SIZE)
        
        if items_to_fetch <= 0:
            return
        
        self.beginInsertRows(QModelIndex(), self._loaded_count, self._loaded_count + items_to_fetch - 1)
        
        batch_start = self._loaded_count
        batch_end = self._loaded_count + items_to_fetch
        batch_paths = self._all_image_files[batch_start:batch_end]
        
        self._loaded_count += items_to_fetch
        self.endInsertRows()
        
        if self.loader:
            QTimer.singleShot(0, lambda: self.loader.request_thumbnails(batch_paths))
    
    def load_images(self, directory: str):
        self.current_directory = directory
        self.beginResetModel()
        self._all_image_files = []
        self._loaded_count = 0
        self._thumbnails.clear()
        self.endResetModel()
        
        if not directory or not os.path.isdir(directory):
            return
        
        if self.loader:
            self.loader.stop()
            self.loader.wait()
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}
        
        try:
            all_images = natural_sorted([entry.path for entry in os.scandir(directory)
                               if entry.is_file() and os.path.splitext(entry.name)[1].lower() in image_extensions])
        except PermissionError:
            return
        
        self._all_image_files = self._image_filter.get_filtered_paths(all_images)
        # print("all:", self._all_image_files)
        
        self.loader = ThumbnailLoader()
        self.loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.loader.start()
    
    @Slot(str, QPixmap)
    def _on_thumbnail_loaded(self, image_path: str, thumbnail: QPixmap):
        self._thumbnails[image_path] = thumbnail
        try:
            row = self._all_image_files.index(image_path)
            if row < self._loaded_count:
                index = self.index(row, 0)
                self.dataChanged.emit(index, index, [Qt.DecorationRole])
        except ValueError:
            pass
    
    def get_image_path(self, row: int) -> Optional[str]:
        return self._all_image_files[row] if 0 <= row < self._loaded_count else None
    
    def get_all_image_files(self) -> list:
        return self._all_image_files.copy()
    
    def cleanup(self):
        if self.loader:
            self.loader.stop()
            self.loader.wait()
            self.loader = None


class ThumbnailListWidget(QListView):
    """Custom list view for displaying image thumbnails using a model."""
    
    thumbnail_clicked = Signal(str)
    
    def __init__(self, image_filter: ImageFilter, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(100, 100))
        self.setSpacing(5)
        self.setViewMode(QListView.ListMode)
        self.setResizeMode(QListView.Adjust)
        self.setLayoutMode(QListView.Batched)
        self.setMovement(QListView.Static)
        self.setUniformItemSizes(True)
        
        self._model = ThumbnailModel(image_filter, self)
        self.setModel(self._model)
        self.clicked.connect(self._on_item_clicked)
    
    def _on_item_clicked(self, index: QModelIndex):
        if index.isValid():
            image_path = self._model.data(index, Qt.UserRole)
            if image_path:
                self.thumbnail_clicked.emit(image_path)
    
    def load_images(self, directory: str):
        self._model.load_images(directory)
    
    def get_image_path_at_row(self, row: int) -> Optional[str]:
        return self._model.get_image_path(row)
    
    def get_all_image_files(self) -> list:
        return self._model.get_all_image_files()
    
    def cleanup(self):
        self._model.cleanup()
    
    def on_filter_changed(self):
        """Called when ImageFilter's filter_changed signal is emitted."""
        if self._model.current_directory:
            self._model.load_images(self._model.current_directory)


class ImageViewer(QLabel):
    """Widget for displaying the selected image with mouse-centered zoom."""
    
    navigate = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Select an image from the sidebar")
        self.setStyleSheet("QLabel { background-color: #2b2b2b; color: #888; font-size: 14px; }")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        self.current_pixmap: Optional[QPixmap] = None
        self.scale_factor = 1.0
        self.scroll_area: Optional[QScrollArea] = None

    def set_scroll_area(self, scroll_area: QScrollArea):
        self.scroll_area = scroll_area

    def wheelEvent(self, event):
        if not self.current_pixmap or self.current_pixmap.isNull():
            return

        if not (event.modifiers() & Qt.ControlModifier):
            super().wheelEvent(event)
            return

        zoom_in_factor = 1.1
        zoom_out_factor = 1 / zoom_in_factor

        old_scale = self.scale_factor
        if event.angleDelta().y() > 0:
            self.scale_factor *= zoom_in_factor
        else:
            self.scale_factor *= zoom_out_factor

        # Limit scale
        self.scale_factor = max(0.1, min(self.scale_factor, 10.0))
        
        # Cursor-centered zoom adjustment
        if self.scroll_area:
            pos = event.position()
            h_bar = self.scroll_area.horizontalScrollBar()
            v_bar = self.scroll_area.verticalScrollBar()
            
            old_h_val = h_bar.value()
            old_v_val = v_bar.value()
            
            self._update_display()
            
            # Calculate new scroll values to keep the point under the cursor fixed
            scale_ratio = self.scale_factor / old_scale
            new_h_val = (old_h_val + pos.x()) * scale_ratio - pos.x()
            new_v_val = (old_v_val + pos.y()) * scale_ratio - pos.y()
            
            h_bar.setValue(max(0, min(int(new_h_val), h_bar.maximum())))
            v_bar.setValue(max(0, min(int(new_v_val), v_bar.maximum())))
        else:
            self._update_display()

    def keyPressEvent(self, event):
        direction = {
            Qt.Key_Left: -1,
            Qt.Key_Right: 1,
            Qt.Key_Up: -1,
            Qt.Key_Down: 1
        }.get(event.key())
        if direction:
            self.navigate.emit(direction)
        else:
            super().keyPressEvent(event)
    
    def display_image(self, image_path: str):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.current_pixmap = pixmap
            # Reset zoom when loading new image
            self.scale_factor = 1.0
            if self.scroll_area:
                # Fit to viewport initially
                view_size = self.scroll_area.viewport().size()
                self.scale_factor = min(view_size.width() / pixmap.width(), 
                                       view_size.height() / pixmap.height(), 1.0)
            self._update_display()
        else:
            self.setText(f"Failed to load image:\n{image_path}")
            self.current_pixmap = None
    
    def _update_display(self):
        if self.current_pixmap and not self.current_pixmap.isNull():
            new_size = self.current_pixmap.size() * self.scale_factor
            self.setPixmap(self.current_pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.resize(new_size)
        elif self.scroll_area:
            # Ensure the placeholder text label fills the viewport to stay centered
            self.resize(self.scroll_area.viewport().size())
    
    def mouseDoubleClickEvent(self, event):
        if self.current_pixmap:
            # Get the current image path from the parent window's state
            window = self.window()
            all_files = window.thumbnail_list.get_all_image_files()
            if 0 <= window._current_index < len(all_files):
                image_path = all_files[window._current_index]
                try:
                    import subprocess
                    subprocess.Popen(['feh', image_path])
                except FileNotFoundError:
                    QMessageBox.critical(self, "Error", "feh is not installed or not found in PATH.\n\nInstall it with: sudo apt install feh")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to launch feh:\n{str(e)}")
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, image_directory: str):
        super().__init__()
        self.image_directory = image_directory
        self.sidebar_visible = True
        self._new_thumbnail_loaded = False
        self._current_index = -1
        
        self.setWindowTitle("Image Viewer")
        self.setWindowIcon(QIcon.fromTheme("multimedia-photo-manager"))
        self.setGeometry(100, 100, 1200, 800)
        
        # Create ImageFilter instance
        self.image_filter = ImageFilter(self)
        
        self._setup_ui()
        self._load_images()
    
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Sidebar
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        
        # Search container
        self.search_container = QWidget()
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.toggle_button = QPushButton()
        self.toggle_button.setFixedWidth(30)
        self.toggle_button.setIcon(QIcon.fromTheme("go-previous"))
        self.toggle_button.setToolTip("Hide sidebar")
        self.toggle_button.clicked.connect(self._toggle_sidebar)
        search_layout.addWidget(self.toggle_button)
        
        # Search filter container
        self.search_filter_container = QWidget()
        search_filter_layout = QHBoxLayout(self.search_filter_container)
        search_filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter images by file name...")
        search_filter_layout.addWidget(self.filter_input)

        self.clear_filter_button = QPushButton()
        self.clear_filter_button.setFixedWidth(30)
        self.clear_filter_button.setIcon(QIcon.fromTheme("edit-clear"))
        self.clear_filter_button.setToolTip("Clear filter and selected tags")
        search_filter_layout.addWidget(self.clear_filter_button)
        
        # Sort button with menu
        self.sort_button = QPushButton()
        self.sort_button.setFixedWidth(30)
        self.sort_button.setIcon(QIcon.fromTheme("view-sort"))
        self.sort_button.setToolTip("Sort images")
        #self.sort_button.setPopupMode(QPushButton.InstantPopup)
        search_filter_layout.addWidget(self.sort_button)
        
        # Create sort menu
        self.sort_menu = QMenu(self.sort_button)
        self.sort_menu.addAction(QIcon.fromTheme("text-plain"), "File name", lambda: self.image_filter.set_sort_by("name"))
        self.sort_menu.addAction(QIcon.fromTheme("document-new"), "Date created", lambda: self.image_filter.set_sort_by("date_created"))
        self.sort_menu.addAction(QIcon.fromTheme("document-edit"), "Date modified", lambda: self.image_filter.set_sort_by("date_modified"))
        self.sort_menu.addSeparator()
        self.sort_descending_action = QAction("Descending", self.sort_menu)
        self.sort_descending_action.setCheckable(True)
        self.sort_descending_action.setChecked(False)
        self.sort_descending_action.triggered.connect(lambda: self.image_filter.set_sort_descending(self.sort_descending_action.isChecked()))
        self.sort_menu.addAction(self.sort_descending_action)
        self.sort_menu.addSeparator()
        self.natural_sort_action = QAction("Natural sort", self.sort_menu)
        self.natural_sort_action.setCheckable(True)
        self.natural_sort_action.setChecked(False)
        self.natural_sort_action.triggered.connect(lambda: self.image_filter.set_natural_sort(self.natural_sort_action.isChecked()))
        self.sort_menu.addAction(self.natural_sort_action)
        self.sort_button.setMenu(self.sort_menu)
        
        search_layout.addWidget(self.search_filter_container)

        sidebar_layout.addWidget(self.search_container)

        # Tab widget for sidebar content
        self.sidebar_tabs = QTabWidget()
        sidebar_layout.addWidget(self.sidebar_tabs)

        # Directory tab
        self.directory_list = DirectoryListWidget()
        self.directory_list.directory_activated.connect(self._load_images)
        self.sidebar_tabs.addTab(self.directory_list, "Directory")

        # Tags tab
        self.tags_list = TagsListWidget()
        
        # Tags container with filter input
        self.tags_container = QWidget()
        tags_layout = QVBoxLayout(self.tags_container)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(2)
        
        self.tags_filter_input = QLineEdit()
        self.tags_filter_input.setPlaceholderText("Filter tags...")
        tags_layout.addWidget(self.tags_list)
        tags_layout.addWidget(self.tags_filter_input)
        
        self.sidebar_tabs.addTab(self.tags_container, "Tags")
        self.clear_filter_button.clicked.connect(self.tags_list.clearSelection)
        self.tags_filter_input.textChanged.connect(self.tags_list.filter_tags)

        # Thumbnail list
        self.thumbnail_list = ThumbnailListWidget(self.image_filter)
        self.thumbnail_list.thumbnail_clicked.connect(self._on_thumbnail_clicked)
        sidebar_layout.addWidget(self.thumbnail_list)
        
        # Image viewer
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #2b2b2b; border: none; }")
        
        self.image_viewer = ImageViewer()
        self.image_viewer.set_scroll_area(self.scroll_area)
        self.image_viewer.navigate.connect(self._navigate_image)
        self.scroll_area.setWidget(self.image_viewer)

        # Connect widgets to image filter
        self.filter_input.textChanged.connect(self.image_filter.set_filter_text)
        self.tags_list.tags_selected.connect(self.image_filter.set_selected_tags)
        self.image_filter.filter_changed.connect(self.thumbnail_list.on_filter_changed)
        
        # Add widgets to splitter
        self.splitter.addWidget(self.sidebar)
        self.sidebar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.splitter.addWidget(self.scroll_area)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
    
    def _load_images(self, directory: str = None):
        self.image_directory = directory or self.image_directory
        self.thumbnail_list.load_images(self.image_directory)
        self.directory_list.load_directories(self.image_directory)
        self.setWindowTitle(f"Image Viewer - {self.image_directory}")

        config = Config.load()
        if config.tags_path:
            self.tags_list.load_tags(config.tags_path, config.tags_path_replace)
            self.image_filter.load_tags(config.tags_path, config.tags_path_replace)
    
    def _on_thumbnail_clicked(self, image_path: str):
        all_files = self.thumbnail_list.get_all_image_files()
        self._current_index = all_files.index(image_path) if image_path in all_files else -1
        self.image_viewer.display_image(image_path)
    
    def keyPressEvent(self, event):
        if self._current_index >= 0 and (direction := {Qt.Key_Left: -1, Qt.Key_Right: 1}.get(event.key())):
            self._navigate_image(direction)
        else:
            super().keyPressEvent(event)
    
    def _navigate_image(self, direction: int):
        all_files = self.thumbnail_list.get_all_image_files()
        self._current_index = max(0, min(self._current_index + direction, len(all_files) - 1))
        
        if 0 <= self._current_index < len(all_files):
            model_index = self.thumbnail_list.model().index(self._current_index, 0)
            if model_index.isValid():
                self.thumbnail_list.setCurrentIndex(model_index)
            self.image_viewer.display_image(all_files[self._current_index])

    def _toggle_sidebar(self):

        self.sidebar_visible = not self.sidebar_visible
        
        for widget in [self.search_filter_container, self.sidebar_tabs, self.thumbnail_list]:
            widget.setVisible(self.sidebar_visible)
        
        self.toggle_button.setIcon(QIcon.fromTheme("go-previous" if self.sidebar_visible else "go-next"))
        self.toggle_button.setToolTip(f"{'Hide' if self.sidebar_visible else 'Show'} sidebar")
        self.toggle_button.setSizePolicy(
            QSizePolicy.Preferred if self.sidebar_visible else QSizePolicy.Expanding,
            QSizePolicy.Preferred if self.sidebar_visible else QSizePolicy.Expanding
        )
        QTimer.singleShot(0, lambda: self.splitter.setSizes([0, 1]))
    
    def closeEvent(self, event):
        self.thumbnail_list.cleanup()
        super().closeEvent(event)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    model = Config.load()
    model.image_directory = sys.argv[1] if len(sys.argv) > 1 else model.image_directory
    Config.save(model)
    
    image_directory = os.path.expanduser(model.image_directory)
    
    if not os.path.isdir(image_directory):
        print(f"Warning: Directory '{image_directory}' does not exist. Creating...")
        try:
            os.makedirs(image_directory, exist_ok=True)
        except OSError:
            print("Failed to create directory. Using current directory instead.")
            image_directory = os.getcwd()
    
    window = MainWindow(image_directory)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
