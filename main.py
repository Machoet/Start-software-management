import sys
import os
import json
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QListWidget, QListWidgetItem, QPushButton, QFileDialog, 
                             QAbstractItemView, QAction, QMessageBox, QFileIconProvider, QActionGroup, QMenu)
from PyQt5.QtCore import Qt, QSize, QFileInfo
from PyQt5.QtGui import QIcon

# --- 语言字典 ---
LANG_DATA = {
    'zh': {
        'title': 'Quick Start - 快速启动',
        'file_menu': '文件(F)',
        'settings_sub': '设置',
        'set_path': '设置存档位置...',
        'open_folder': '打开存档文件夹',
        'auto_sel_opt': '启动时默认全选',
        'exit': '退出',
        'help_menu': '帮助(H)',
        'guide': '操作指南',
        'lang_option': '切换语言 (Language)',
        'start_btn': '启 动',
        'guide_title': '操作指南',
        'guide_content': "🚀 快捷操作：\n\n• 添加：从外部拖入文件/快捷方式\n• 排序：列表内上下拖动\n• 启动：双击、回车或点START\n• 删除：选中后按 Delete 键\n• 多选：配合 Ctrl 或 Shift",
        'select_json': '设置存档位置',
    },
    'en': {
        'title': 'Quick Start',
        'file_menu': 'File(F)',
        'settings_sub': 'Settings',
        'set_path': 'Set Storage Path...',
        'open_folder': 'Open Storage Folder',
        'auto_sel_opt': 'Auto-select on Start',
        'exit': 'Exit',
        'help_menu': 'Help(H)',
        'guide': 'User Guide',
        'lang_option': 'Language',
        'start_btn': 'START',
        'guide_title': 'User Guide',
        'guide_content': "🚀 Quick Actions:\n\n• Add: Drag files/shortcuts here\n• Sort: Drag items up/down\n• Run: Double-click, Enter or START\n• Delete: Press Delete key\n• Multi: Use Ctrl or Shift",
        'select_json': 'Select Storage Path',
    }
}

class CleanListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ref = parent
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setIconSize(QSize(24, 24))

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.parent_ref.handle_external_drop(event)
        else:
            super().dropEvent(event)
            self.parent_ref.save_current_order()

class UltimateLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 路径设置
        app_data_root = os.getenv('LOCALAPPDATA')
        self.cache_dir = os.path.join(app_data_root, "QuickStart_App")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        self.pointer_file = os.path.join(self.cache_dir, "path_pointer.txt")
        self.icon_provider = QFileIconProvider()
        
        # 偏好加载
        self.current_lang = 'zh'
        self.auto_select_all = True 
        self.config_path = self.load_settings()
        
        self.apps_data = self.load_data()
        self.initUI()
        self.retranslate_ui()

        # --- 核心修正：仅在程序启动时执行一次自动全选 ---
        if self.auto_select_all:
            self.list_widget.selectAll()

    def load_settings(self):
        default_json = os.path.join(self.cache_dir, "my_shortcuts.json")
        if os.path.exists(self.pointer_file):
            try:
                with open(self.pointer_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    parts = content.split("|")
                    if len(parts) >= 1: path = parts[0]
                    if len(parts) >= 2: self.current_lang = parts[1]
                    if len(parts) >= 3: self.auto_select_all = (parts[2] == 'True')
                    return path if path else default_json
            except: pass
        return default_json

    def save_settings(self):
        try:
            with open(self.pointer_file, 'w', encoding='utf-8') as f:
                f.write(f"{self.config_path}|{self.current_lang}|{self.auto_select_all}")
        except: pass

    def initUI(self):
        self.setFixedSize(380, 600)
        self.setWindowIcon(QIcon()) 
        
        self.menubar = self.menuBar()
        self.file_menu = QMenu(self)
        self.help_menu = QMenu(self)
        self.menubar.addMenu(self.file_menu)
        self.menubar.addMenu(self.help_menu)

        self.change_path_act = QAction('', self)
        self.change_path_act.setShortcut("Ctrl+S")
        self.change_path_act.triggered.connect(self.change_config_location)
        self.open_dir_act = QAction('', self)
        self.open_dir_act.triggered.connect(self.open_config_folder)
        self.exit_act = QAction('', self)
        self.exit_act.triggered.connect(self.close)
        self.guide_act = QAction('', self)
        self.guide_act.triggered.connect(self.show_guide)

        self.auto_sel_act = QAction('', self, checkable=True)
        self.auto_sel_act.setChecked(self.auto_select_all)
        self.auto_sel_act.triggered.connect(self.toggle_auto_select)

        self.lang_group = QActionGroup(self)
        self.zh_act = QAction('简体中文', self, checkable=True)
        self.en_act = QAction('English', self, checkable=True)
        self.lang_group.addAction(self.zh_act)
        self.lang_group.addAction(self.en_act)
        self.zh_act.triggered.connect(lambda: self.switch_lang('zh'))
        self.en_act.triggered.connect(lambda: self.switch_lang('en'))
        
        if self.current_lang == 'zh': self.zh_act.setChecked(True)
        else: self.en_act.setChecked(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.list_widget = CleanListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.run_selected_apps)
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #ccc; border-radius: 6px; font-size: 14px; outline: none; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background-color: #0078d7; color: white; border-radius: 4px; }
        """)
        layout.addWidget(self.list_widget)

        self.btn_run = QPushButton("")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("background-color: #28a745; color: white; border-radius: 6px; font-weight: bold; font-size: 16px;")
        self.btn_run.clicked.connect(self.run_selected_apps)
        layout.addWidget(self.btn_run)

    def retranslate_ui(self):
        d = LANG_DATA[self.current_lang]
        self.setWindowTitle(d['title'])
        self.btn_run.setText(d['start_btn'])
        self.file_menu.setTitle(d['file_menu'])
        self.file_menu.clear()
        
        settings_menu = self.file_menu.addMenu(d['settings_sub'])
        lang_submenu = settings_menu.addMenu(d['lang_option'])
        lang_submenu.addAction(self.zh_act)
        lang_submenu.addAction(self.en_act)
        
        self.auto_sel_act.setText(d['auto_sel_opt'])
        settings_menu.addAction(self.auto_sel_act)
        
        settings_menu.addSeparator()
        settings_menu.addAction(self.change_path_act)
        self.change_path_act.setText(d['set_path'])
        
        self.file_menu.addAction(self.open_dir_act)
        self.open_dir_act.setText(d['open_folder'])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_act)
        self.exit_act.setText(d['exit'])
        
        self.help_menu.setTitle(d['help_menu'])
        self.help_menu.clear()
        self.help_menu.addAction(self.guide_act)
        self.guide_act.setText(d['guide'])
        
        self.update_list_display()

    def toggle_auto_select(self, state):
        self.auto_select_all = state
        self.save_settings()

    def switch_lang(self, lang_code):
        self.current_lang = lang_code
        self.save_settings()
        self.retranslate_ui()

    def show_guide(self):
        d = LANG_DATA[self.current_lang]
        QMessageBox.information(self, d['guide_title'], d['guide_content'])

    def save_current_order(self):
        new_data = {}
        for i in range(self.list_widget.count()):
            name = self.list_widget.item(i).text()
            if name in self.apps_data: new_data[name] = self.apps_data[name]
        self.apps_data = new_data
        self.save_data()

    def handle_external_drop(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                name = os.path.basename(path)
                self.apps_data[name] = path
        self.save_data()
        self.update_list_display()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            selected = self.list_widget.selectedItems()
            if not selected: return
            for item in selected:
                if item.text() in self.apps_data: del self.apps_data[item.text()]
            self.save_data()
            self.update_list_display()
        elif event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            self.run_selected_apps()

    def run_selected_apps(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items:
            path = self.apps_data.get(item.text())
            if path:
                try: os.startfile(path)
                except: pass

    def open_config_folder(self):
        folder = os.path.dirname(self.config_path)
        if os.path.exists(folder): os.startfile(folder)

    def change_config_location(self):
        d = LANG_DATA[self.current_lang]
        new_path, _ = QFileDialog.getSaveFileName(self, d['select_json'], "my_shortcuts.json", "JSON Files (*.json)")
        if new_path:
            self.save_data()
            if os.path.exists(self.config_path):
                try: shutil.copy2(self.config_path, new_path)
                except: pass
            self.config_path = new_path
            self.save_settings()
            self.apps_data = self.load_data()
            self.update_list_display()

    def load_data(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

    def save_data(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.apps_data, f, ensure_ascii=False, indent=4)

    def update_list_display(self):
        self.list_widget.clear()
        for name, path in self.apps_data.items():
            item = QListWidgetItem(name)
            if os.path.exists(path):
                item.setIcon(self.icon_provider.icon(QFileInfo(path)))
            else:
                item.setIcon(self.style().standardIcon(self.style().SP_MessageBoxWarning))
            self.list_widget.addItem(item)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UltimateLauncher()
    window.show()
    sys.exit(app.exec_())