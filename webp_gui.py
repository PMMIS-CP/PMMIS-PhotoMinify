# webp_gui.py
import sys
import os
import zipfile
from functools import partial

from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
                             QFileDialog, QSpinBox, QCheckBox, QTextEdit,
                             QMessageBox, QProgressBar, QDialog,
                             QDialogButtonBox, QMenu, QMenuBar)
from PyQt6.QtGui import QAction, QIcon, QFontDatabase, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

try:
    import qt_material
except ImportError:
    print("qt-material library not found. Consider installing it: pip install qt-material")
    qt_material = None

import image_converter

def load_persian_font():
    """
    Load Vazir font and return the font object.
    Tries multiple possible filenames and locations.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_font_filenames = [
        "Vazir.ttf",
        "Vazir-Regular.ttf", 
        "Vazir-FD.ttf",
        "vazir.ttf",
        "Vazir.woff2.ttf",
    ]
    
    # Also check if there's a fonts folder
    possible_dirs = [
        script_dir,
        os.path.join(script_dir, "fonts"),
        os.path.join(script_dir, "Fonts"),
        os.path.join(script_dir, "font"),
        os.path.join(script_dir, "Font"),
    ]
    
    # Collect all possible font paths
    font_paths_to_check = []
    for directory in possible_dirs:
        if os.path.isdir(directory):
            for filename in os.listdir(directory):
                if filename.lower().endswith('.ttf') or filename.lower().endswith('.otf'):
                    font_paths_to_check.append(os.path.join(directory, filename))
            # Also add specific filenames
            for filename in possible_font_filenames:
                full_path = os.path.join(directory, filename)
                if full_path not in font_paths_to_check:
                    font_paths_to_check.append(full_path)
    
    print(f"[DEBUG] Searching for fonts in: {possible_dirs}")
    print(f"[DEBUG] Found {len(font_paths_to_check)} potential font files")
    
    for font_path in font_paths_to_check:
        if os.path.exists(font_path):
            print(f"[DEBUG] Trying font: {font_path}")
            font_id = QFontDatabase.addApplicationFont(font_path)
            print(f"[DEBUG] Font ID: {font_id}")
            
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    font_family = font_families[0]
                    print(f"[DEBUG] Successfully loaded: {font_family}")
                    
                    # Create font with multiple sizes for testing
                    vazir_font = QFont(font_family, 10)
                    vazir_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
                    
                    # Return font and family name
                    return vazir_font, font_family
    
    print("[DEBUG] ERROR: Could not find any valid Persian font!")
    return QFont(), None

# --- DEBUG: Print current working directory and script location ---
print(f"[DEBUG] Current working directory: {os.getcwd()}")
print(f"[DEBUG] Script location: {os.path.dirname(os.path.abspath(__file__))}")

class NewFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ایجاد پوشه جدید")

        self.layout = QVBoxLayout()
        self.label = QLabel("نام پوشه:")
        self.lineEdit = QLineEdit()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.lineEdit)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("تأیید")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)
        if qt_material and hasattr(self.parent(), 'current_theme_name'):
             qt_material.apply_stylesheet(self, theme=self.parent().current_theme_name)


    def getFolderName(self):
        return self.lineEdit.text()

class ConversionThread(QThread):
    progress_update = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, input_path, output_dir, quality, lossless, recursive, no_overwrite, zip_output):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.quality = quality
        self.lossless = lossless
        self.recursive = recursive
        self.no_overwrite = no_overwrite
        self.zip_output = zip_output

    def run(self):
        try:
            image_converter.process_images(
                self.input_path, self.output_dir, self.quality, self.lossless,
                self.recursive, self.no_overwrite, self.progress_update.emit,
                parallel=True  # فعال‌سازی پردازش موازی
            )
            self.finished_signal.emit(self.output_dir if self.output_dir else self.input_path)
        except Exception as e:
            self.error_signal.emit(f"Error in conversion thread: {str(e)}")


class ImageConverterGUI(QMainWindow):
    PREDEFINED_SIZES = {
        "پیش‌فرض (600x650)": (600, 650),
        "عمودی - کوچک (500x700)": (500, 700),
        "عمودی - بلند (600x800)": (600, 800),
        "مربع - کوچک (700x700)": (700, 700),
        "افقی - کوچک (800x600)": (800, 600),
        "افقی - متوسط (1024x768)": (1024, 768),
    }
    DEFAULT_SIZE_NAME = "پیش‌فرض (600x650)"
    DEFAULT_THEME = 'dark_amber.xml'

    def __init__(self):
        super().__init__()
        self.current_theme_name = self.DEFAULT_THEME
        self.setWindowTitle("کاهش حجم عکس")

        initial_width, initial_height = self.PREDEFINED_SIZES[self.DEFAULT_SIZE_NAME]
        self.setFixedSize(initial_width, initial_height)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self._create_menu_bar()
        self._create_ui_elements()

        self.toggle_output_folder_widgets(self.output_folder_checkbox.checkState().value)
        self._debug_font_status()  # برای دیباگ
        # Apply Persian font immediately after UI creation
        if QApplication.instance().property("persian_font_family"):
            self._apply_persian_font()

        # --- DEBUG: Check if font is actually applied to widgets ---
        print(f"[DEBUG] Main window font family: {self.font().family()}")
        print(f"[DEBUG] Main window font info: {self.font().toString()}")

    def _debug_font_status(self):
        """Print detailed font information for debugging"""
        print("\n" + "="*50)
        print("[DEBUG] FONT DIAGNOSTICS:")
        print(f"[DEBUG] Application font: {QApplication.instance().font().family()}")
        print(f"[DEBUG] Window font: {self.font().family()}")
        
        # Check a few widgets
        test_widgets = [
            self.input_folder_label,
            self.input_folder_line_edit,
            self.browse_input_button,
            self.convert_button,
            self.status_output
        ]
        
        for widget in test_widgets:
            if widget:
                print(f"[DEBUG] {widget.__class__.__name__} font: {widget.font().family()}")
                print(f"[DEBUG] {widget.__class__.__name__} text sample: '{widget.text()[:30] if hasattr(widget, 'text') else widget.placeholderText()[:30]}'")
        
        # Check available fonts
        available_fonts = QFontDatabase.families()
        persian_fonts = [f for f in available_fonts if 'vazir' in f.lower()]
        print(f"[DEBUG] Available Vazir fonts: {persian_fonts}")
        print("[DEBUG] First 10 available fonts:", available_fonts[:10])
        print("="*50 + "\n")

    def _create_ui_elements(self):
        # Input Folder
        input_folder_layout = QHBoxLayout()
        self.input_folder_label = QLabel("پوشه/فایل ورودی:")
        self.input_folder_line_edit = QLineEdit()
        self.input_folder_line_edit.setPlaceholderText("مسیر تصویر یا پوشه تصاویر")
        self.browse_input_button = QPushButton("مرور...")
        self.browse_input_button.setIcon(QIcon.fromTheme("document-open", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-open-16.png")))
        self.browse_input_button.clicked.connect(self.browse_input)
        input_folder_layout.addWidget(self.input_folder_label)
        input_folder_layout.addWidget(self.input_folder_line_edit)
        input_folder_layout.addWidget(self.browse_input_button)
        self.layout.addLayout(input_folder_layout)

        # Output Folder Checkbox
        self.output_folder_checkbox = QCheckBox("استفاده از پوشه خروجی جداگانه")
        self.output_folder_checkbox.setChecked(True)
        self.output_folder_checkbox.stateChanged.connect(self.toggle_output_folder_widgets)
        self.layout.addWidget(self.output_folder_checkbox)

        # Output Folder Path
        self.output_folder_layout = QHBoxLayout()
        self.output_folder_label = QLabel("پوشه خروجی:")
        self.output_folder_line_edit = QLineEdit()
        self.output_folder_line_edit.setPlaceholderText("خالی بگذارید تا در کنار ورودی ذخیره شود")
        self.browse_output_button = QPushButton("مرور...")
        self.browse_output_button.setIcon(QIcon.fromTheme("folder-open", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-open-16.png")))
        self.browse_output_button.clicked.connect(self.browse_output_folder)
        self.output_folder_layout.addWidget(self.output_folder_label)
        self.output_folder_layout.addWidget(self.output_folder_line_edit)
        self.output_folder_layout.addWidget(self.browse_output_button)
        self.layout.addLayout(self.output_folder_layout)

        # Create Output Folder Button
        self.create_output_folder_button = QPushButton("ایجاد زیرپوشه خروجی جدید...")
        self.create_output_folder_button.setIcon(QIcon.fromTheme("folder-new", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-new-16.png")))
        self.create_output_folder_button.clicked.connect(self.create_output_folder)
        self.layout.addWidget(self.create_output_folder_button)

        self.output_folder_hint_label = QLabel()
        self.output_folder_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.output_folder_hint_label)

        # WebP Settings
        webp_settings_layout = QHBoxLayout()
        self.quality_label = QLabel("کیفیت WebP (0-100):")
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(0, 100)
        self.quality_spinbox.setValue(85)
        self.quality_spinbox.setToolTip("مقادیر بالاتر کیفیت بهتر و حجم بیشتر. 0 برای کمترین حجم (کمترین کیفیت).")
        webp_settings_layout.addWidget(self.quality_label)
        webp_settings_layout.addWidget(self.quality_spinbox)
        self.layout.addLayout(webp_settings_layout)

        self.lossless_checkbox = QCheckBox("فشرده‌سازی بدون افت کیفیت")
        self.lossless_checkbox.setToolTip("حجم فایل بیشتر اما بدون افت کیفیت. تنظیمات کیفیت را نادیده می‌گیرد.")
        self.layout.addWidget(self.lossless_checkbox)

        # Options
        options_layout = QHBoxLayout()
        self.recursive_checkbox = QCheckBox("پردازش زیرپوشه‌ها")
        self.recursive_checkbox.setChecked(True)
        self.recursive_checkbox.setToolTip("اگر ورودی یک پوشه است، تصاویر زیرپوشه‌های آن نیز تبدیل شوند.")
        options_layout.addWidget(self.recursive_checkbox)

        self.overwrite_checkbox = QCheckBox("بازنویسی فایل‌های WebP موجود")
        self.overwrite_checkbox.setChecked(False)
        self.overwrite_checkbox.setToolTip("اگر علامت نخورد، فایل‌های webp. موجود با همین نام نادیده گرفته می‌شوند.")
        options_layout.addWidget(self.overwrite_checkbox)
        self.layout.addLayout(options_layout)

        self.zip_output_checkbox = QCheckBox("زیپ کردن خروجی پس از تبدیل")
        self.zip_output_checkbox.setChecked(True)
        self.zip_output_checkbox.setToolTip("اگر پوشه خروجی جداگانه استفاده شود، محتویات آن پس از تبدیل زیپ شود.")
        self.layout.addWidget(self.zip_output_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.layout.addWidget(self.progress_bar)

        self.convert_button = QPushButton("تبدیل به WebP")
        self.convert_button.setIcon(QIcon.fromTheme("document-save", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-save-16.png")))
        self.convert_button.clicked.connect(self.start_conversion)
        self.layout.addWidget(self.convert_button)

        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setPlaceholderText("وضعیت تبدیل در اینجا نمایش داده می‌شود...")
        self.layout.addWidget(self.status_output)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        # Remove & for menu items as they can cause issues with Persian text
        # The & is for Alt+key shortcuts which don't work well with Persian
        menu_bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        file_menu = menu_bar.addMenu("فایل")
        exit_action = QAction(QIcon.fromTheme("application-exit"), "خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("نمایش")
        size_menu = view_menu.addMenu("تنظیم اندازه پنجره")
        for name, (width, height) in self.PREDEFINED_SIZES.items():
            action = QAction(name, self)
            action.triggered.connect(partial(self._set_selected_window_size, width, height))
            size_menu.addAction(action)
        
        if qt_material:
            view_menu.addSeparator()
            theme_menu = view_menu.addMenu("پوسته")
            available_themes = sorted(qt_material.list_themes())
            for theme_file in available_themes:
                theme_name = theme_file.replace('.xml', '').replace('_', ' ').title()
                action = QAction(theme_name, self, checkable=True)
                action.setProperty("theme_file", theme_file)
                if theme_file == self.current_theme_name:
                    action.setChecked(True)
                action.triggered.connect(self._change_theme)
                theme_menu.addAction(action)
            self.theme_menu = theme_menu


    def _set_selected_window_size(self, width, height):
        self.setFixedSize(width, height)

    def _change_theme(self):
        action = self.sender()
        if action and action.isChecked():
            new_theme_file = action.property("theme_file")
            try:
                # IMPORTANT: Apply theme first, then re-apply the Persian font
                qt_material.apply_stylesheet(QApplication.instance(), theme=new_theme_file)
                self.current_theme_name = new_theme_file
                for act in self.theme_menu.actions():
                    act.setChecked(act.property("theme_file") == new_theme_file)
                
                # Re-apply Vazir font after theme change
                self._apply_persian_font()
                
            except Exception as e:
                QMessageBox.warning(self, "خطای پوسته", f"نمی‌توان پوسته '{new_theme_file}' را اعمال کرد: {e}")
                action.setChecked(False)

    def _apply_persian_font(self):
        """Force apply Persian font and clear widget stylesheets including menus"""
        font_family = QApplication.instance().property("persian_font_family")
        if not font_family:
            return
        
        vazir_font = QFont(font_family, 10)
        vazir_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        vazir_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        
        QApplication.instance().setFont(vazir_font)
        self.setFont(vazir_font)
        
        def force_font_and_clear_style(widget):
            widget.setFont(vazir_font)
            if hasattr(widget, 'setStyleSheet'):
                widget.setStyleSheet("")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            
            for child in widget.findChildren(QWidget):
                child.setFont(vazir_font)
                if hasattr(child, 'setStyleSheet'):
                    child.setStyleSheet("")
                child.style().unpolish(child)
                child.style().polish(child)
                
                # Fix QMenu items explicitly
                if isinstance(child, QMenu):
                    child.setStyleSheet("")
                    for action in child.actions():
                        action.setFont(vazir_font)
        
        force_font_and_clear_style(self)
        
        # CRITICAL: Fix menubar specifically
        menubar = self.menuBar()
        menubar.setFont(vazir_font)
        menubar.setStyleSheet("")
        for action in menubar.actions():
            action.setFont(vazir_font)
            menu = action.menu()
            if menu:
                menu.setFont(vazir_font)
                menu.setStyleSheet("")
                for sub_action in menu.actions():
                    sub_action.setFont(vazir_font)
        
        self.update()
        QApplication.processEvents()
        
        print(f"[DEBUG] Font forcefully applied to all widgets including menus")

    def browse_input(self):
        current_path_in_lineedit = self.input_folder_line_edit.text().strip()
        start_dir = os.path.dirname(current_path_in_lineedit) if current_path_in_lineedit and (os.path.isfile(current_path_in_lineedit) or os.path.isdir(current_path_in_lineedit)) else os.path.expanduser("~")
        if not os.path.isdir(start_dir):
             start_dir = os.path.expanduser("~")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("انتخاب نوع ورودی")
        msg_box.setText("چه چیزی را به عنوان ورودی انتخاب می‌کنید؟")
        folder_button = msg_box.addButton("انتخاب پوشه", QMessageBox.ButtonRole.ActionRole)
        file_button = msg_box.addButton("انتخاب فایل", QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        if qt_material and hasattr(self, 'current_theme_name'):
             qt_material.apply_stylesheet(msg_box, theme=self.current_theme_name)
        
        msg_box.exec()

        selected_path = ""

        if msg_box.clickedButton() == folder_button:
            path = QFileDialog.getExistingDirectory(
                self,
                "انتخاب پوشه ورودی",
                start_dir
            )
            if path:
                selected_path = path
        elif msg_box.clickedButton() == file_button:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "انتخاب فایل ورودی",
                start_dir,
                "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
            )
            if path:
                selected_path = path

        if selected_path:
            self.input_folder_line_edit.setText(selected_path)


    def browse_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه خروجی")
        if folder_path:
            self.output_folder_line_edit.setText(folder_path)

    def create_output_folder(self):
        parent_for_new_folder = self.output_folder_line_edit.text()
        if not parent_for_new_folder or not os.path.isdir(parent_for_new_folder):
            parent_for_new_folder = self.input_folder_line_edit.text()
            if os.path.isfile(parent_for_new_folder):
                parent_for_new_folder = os.path.dirname(parent_for_new_folder)

        if not parent_for_new_folder or not os.path.isdir(parent_for_new_folder):
            QMessageBox.warning(self, "پوشه پایه موجود نیست",
                                "لطفاً ابتدا یک پوشه ورودی یا خروجی انتخاب کنید تا زیرپوشه در آن ایجاد شود.")
            return

        dialog = NewFolderDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder_name = dialog.getFolderName()
            if not folder_name:
                QMessageBox.warning(self, "نام پوشه موجود نیست", "لطفاً یک نام برای زیرپوشه وارد کنید.")
                return
            
            new_folder_path = os.path.join(parent_for_new_folder, folder_name)
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                self.output_folder_line_edit.setText(new_folder_path)
                if not self.output_folder_checkbox.isChecked():
                    self.output_folder_checkbox.setChecked(True)
            except OSError as e:
                QMessageBox.critical(self, "خطا در ایجاد پوشه", f"نمی‌توان پوشه '{new_folder_path}' را ایجاد کرد: {e}")

    def toggle_output_folder_widgets(self, state_value):
        enabled = (state_value == Qt.CheckState.Checked.value)
        self.output_folder_label.setEnabled(enabled)
        self.output_folder_line_edit.setEnabled(enabled)
        self.browse_output_button.setEnabled(enabled)
        self.zip_output_checkbox.setEnabled(enabled)

        if enabled:
            self.output_folder_hint_label.setText("(فایل‌های WebP در پوشه خروجی مشخص شده ذخیره می‌شوند)")
        else:
            self.output_folder_hint_label.setText("(فایل‌های WebP در کنار فایل‌های اصلی ذخیره می‌شوند)")


    def start_conversion(self):
        input_path = self.input_folder_line_edit.text().strip()
        
        output_dir_text = self.output_folder_line_edit.text().strip()
        use_separate_output = self.output_folder_checkbox.isChecked()
        
        output_dir_to_use = output_dir_text if use_separate_output else None

        quality = self.quality_spinbox.value()
        lossless = self.lossless_checkbox.isChecked()
        recursive = self.recursive_checkbox.isChecked()
        no_overwrite = not self.overwrite_checkbox.isChecked()
        zip_output_flag = self.zip_output_checkbox.isChecked() and use_separate_output


        if not input_path:
            QMessageBox.warning(self, "ورودی نامشخص", "لطفاً یک تصویر یا پوشه ورودی انتخاب کنید.")
            return
        if not os.path.exists(input_path):
            QMessageBox.warning(self, "ورودی نامعتبر", f"مسیر ورودی وجود ندارد: {input_path}")
            return
        
        if use_separate_output and not output_dir_to_use:
            QMessageBox.warning(self, "خروجی نامشخص",
                                "لطفاً یک پوشه خروجی مشخص کنید یا تیک 'استفاده از پوشه خروجی جداگانه' را بردارید.")
            return
        
        if output_dir_to_use and not os.path.isdir(output_dir_to_use):
            reply = QMessageBox.question(self, "ایجاد پوشه خروجی؟",
                                         f"پوشه خروجی '{output_dir_to_use}' وجود ندارد. ایجاد شود؟",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(output_dir_to_use, exist_ok=True)
                except OSError as e:
                    QMessageBox.critical(self, "خطای پوشه خروجی", f"نمی‌توان پوشه خروجی را ایجاد کرد: {e}")
                    return
            else:
                return

        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("در حال شروع...")
        self.status_output.clear()
        self.status_output.append("شروع تبدیل...")

        self.conversion_thread = ConversionThread(
            input_path, output_dir_to_use, quality, lossless, 
            recursive, no_overwrite, zip_output_flag
        )
        self.conversion_thread.progress_update.connect(self.update_progress)
        self.conversion_thread.finished_signal.connect(self.conversion_complete)
        self.conversion_thread.error_signal.connect(self.conversion_error)
        self.conversion_thread.start()

    def update_progress(self, current, total, message):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{percentage}% ({current}/{total}) - {message}")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(message)
        self.status_output.append(message)
        QApplication.processEvents()

    def conversion_complete(self, thread_output_dir_info):
        self.status_output.append("------------------------------")
        self.status_output.append("فرایند تبدیل از رابط کاربری کامل شد.")
        self.progress_bar.setFormat("تکمیل شد!")

        actual_output_location_for_zipping = None
        if self.output_folder_checkbox.isChecked() and self.output_folder_line_edit.text().strip():
            actual_output_location_for_zipping = self.output_folder_line_edit.text().strip()
        
        if self.zip_output_checkbox.isChecked() and actual_output_location_for_zipping:
            if os.path.isdir(actual_output_location_for_zipping):
                self.status_output.append(f"در حال تلاش برای زیپ کردن: {actual_output_location_for_zipping}")
                self.zip_output_folder(actual_output_location_for_zipping)
            else:
                self.status_output.append(f"رد شدن زیپ: مسیر خروجی '{actual_output_location_for_zipping}' یک پوشه معتبر نیست.")
        
        self.convert_button.setEnabled(True)
        QMessageBox.information(self, "تبدیل به پایان رسید",
                                "فرایند تبدیل تصویر به پایان رسید. جزئیات را در گزارش وضعیت ببینید.")

    def conversion_error(self, message):
        self.status_output.append(f"خطا: {message}")
        self.progress_bar.setFormat("خطا!")
        QMessageBox.critical(self, "خطای تبدیل", f"خطایی رخ داد: {message}")
        self.convert_button.setEnabled(True)

    def zip_output_folder(self, folder_to_zip):
        try:
            parent_dir = os.path.dirname(folder_to_zip)
            zip_filename_base = os.path.basename(folder_to_zip)
            if not zip_filename_base: zip_filename_base = "converted_output"
            
            zip_filepath = os.path.join(parent_dir if parent_dir else folder_to_zip, f"{zip_filename_base}.zip")

            self.status_output.append(f"در حال زیپ کردن محتویات '{folder_to_zip}' به '{zip_filepath}'...")
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_to_zip):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_to_zip)
                        zipf.write(file_path, arcname)
            self.status_output.append(f"با موفقیت زیپ شد به: {zip_filepath}")
            QMessageBox.information(self, "زیپ کامل شد", f"خروجی با موفقیت در مسیر زیر زیپ شد:\n{zip_filepath}")
        except Exception as e:
            self.status_output.append(f"خطا در زیپ: {e}")
            QMessageBox.critical(self, "خطای زیپ", f"نمی‌توان پوشه خروجی '{folder_to_zip}' را زیپ کرد:\n{e}")

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    # --- Load Persian Font ---
    vazir_font, font_family = load_persian_font()
    
    # --- Apply qt-material theme FIRST ---
    if qt_material:
        try:
            qt_material.apply_stylesheet(
                app, 
                theme=ImageConverterGUI.DEFAULT_THEME, 
                invert_secondary=True
            )
            print(f"[DEBUG] Applied qt-material theme: {ImageConverterGUI.DEFAULT_THEME}")
        except Exception as e:
            print(f"Could not apply initial qt-material theme: {e}")
    
    # --- NOW apply Persian font AFTER theme ---
    if font_family:
        app.setProperty("persian_font_family", font_family)
        
        # CRITICAL FIX: Override qt-material's stylesheet to use Vazir font
        # but ONLY set font-family, preserve all other theme styles
        current_style = app.styleSheet()
        # Replace any existing font-family declarations
        import re
        # Remove all font-family related styles from the stylesheet
        cleaned_style = re.sub(r'\*?\s*\{[^}]*font-family:[^;!]*[!important]*\s*;?\s*\}', '', current_style)
        cleaned_style = re.sub(r'font-family:[^;!]*[!important]*\s*;?', '', cleaned_style)
        
        # Add Vazir font at the end with !important
        persian_style = f"""
            * {{
                font-family: '{font_family}' !important;
            }}
        """
        app.setStyleSheet(cleaned_style + persian_style)
        
        # Also set font directly as fallback
        vazir_font = QFont(font_family, 10)
        vazir_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        vazir_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        app.setFont(vazir_font)
        
        print(f"[DEBUG] Applied Persian font with stylesheet override")
    else:
        print("[DEBUG] WARNING: No Persian font loaded")
    
    # --- Create and show window ---
    window = ImageConverterGUI()
    
    # Final font application to all widgets
    # Final font application to all widgets
    if font_family:
        vazir_font = QFont(font_family, 10)
        vazir_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        vazir_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        
        def force_font_and_clear_style(widget):
            widget.setFont(vazir_font)
            # Clear stylesheet from widget itself
            if hasattr(widget, 'setStyleSheet'):
                widget.setStyleSheet("")
            
            # Special handling for menus - they need their own font + stylesheet fix
            if isinstance(widget, QMenuBar):
                # Clear stylesheet from menubar
                widget.setStyleSheet("")
                # Fix each menu
                for action in widget.actions():
                    menu = action.menu()
                    if menu:
                        menu.setFont(vazir_font)
                        menu.setStyleSheet("")
                        # Fix each action within the menu
                        for sub_action in menu.actions():
                            sub_action.setFont(vazir_font)
            
            # Handle nested menus and all children
            for child in widget.findChildren(QWidget):
                child.setFont(vazir_font)
                if hasattr(child, 'setStyleSheet'):
                    child.setStyleSheet("")
                
                # Fix QMenu items explicitly
                if isinstance(child, QMenu):
                    child.setFont(vazir_font)
                    child.setStyleSheet("")
                    for action in child.actions():
                        action.setFont(vazir_font)
        
        force_font_and_clear_style(window)
        
        # Also fix the menubar directly after window creation
        menubar = window.menuBar()
        menubar.setFont(vazir_font)
        menubar.setStyleSheet("")
        for action in menubar.actions():
            action.setFont(vazir_font)
            menu = action.menu()
            if menu:
                menu.setFont(vazir_font)
                menu.setStyleSheet("")
                for sub_action in menu.actions():
                    sub_action.setFont(vazir_font)
        
        print(f"[DEBUG] Cleared widget stylesheets and applied font directly (including menus)")
    
    window.show()
    
    # Debug
    print("\n" + "="*50)
    print("[DEBUG] FINAL STATUS:")
    print(f"[DEBUG] App font: {app.font().family()}")
    print(f"[DEBUG] Window font: {window.font().family()}")
    if hasattr(window, 'input_folder_label'):
        print(f"[DEBUG] Label font: {window.input_folder_label.font().family()}")
        print(f"[DEBUG] Label text: '{window.input_folder_label.text()}'")
        print(f"[DEBUG] Label stylesheet: '{window.input_folder_label.styleSheet()}'")
    print("="*50 + "\n")
    
    sys.exit(app.exec())