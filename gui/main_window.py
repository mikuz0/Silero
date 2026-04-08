"""Главное окно приложения"""
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QStatusBar,
    QMessageBox, QApplication, QMenuBar, QAction, QMenu
)
from PyQt5.QtCore import Qt

from config.settings import AppConfig, TTSSettings, AppSettings
from gui.text_tab import TextTab
from gui.batch_tab import BatchTab
from gui.settings_dialog import SettingsDialog
from utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        AppConfig.ensure_dirs()
        
        # Загружаем сохранённые настройки
        self.app_settings = AppSettings()
        self.settings = TTSSettings()
        self.load_settings()
        
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setMinimumSize(1000, 700)
        
        self.create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.tab_widget = QTabWidget()
        self.text_tab = TextTab(self)
        self.batch_tab = BatchTab(self)
        
        # Передаём настройки во вкладки
        self.text_tab.update_settings(self.settings)
        self.batch_tab.update_settings(self.settings)
        
        self.tab_widget.addTab(self.text_tab, "📝 Текст")
        self.tab_widget.addTab(self.batch_tab, "📚 Пакетная обработка")
        self.tab_widget.setCurrentIndex(1)
        
        layout.addWidget(self.tab_widget)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        setup_logger(AppConfig.BASE_DIR / "logs")
        self.restore_window_geometry()
        
        logger.info(f"{AppConfig.APP_NAME} запущен")
    
    def create_menu_bar(self):
        """Создание строки меню"""
        menubar = self.menuBar()
        
        # ===== Меню Файл =====
        file_menu = menubar.addMenu("📁 Файл")
        
        select_working_dir_action = QAction("📂 Выбрать рабочую папку", self)
        select_working_dir_action.triggered.connect(self.select_working_dir_from_menu)
        file_menu.addAction(select_working_dir_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 Выйти", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ===== Меню Правка =====
        edit_menu = menubar.addMenu("✏️ Правка")
        
        clear_audio_action = QAction("🗑️ Очистить аудио", self)
        clear_audio_action.triggered.connect(self.clear_audio_from_menu)
        edit_menu.addAction(clear_audio_action)
        
        # ===== Меню Настройки =====
        settings_menu = menubar.addMenu("⚙️ Настройки")
        
        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)
        
        # ===== Меню Помощь =====
        help_menu = menubar.addMenu("❓ Помощь")
        
        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def open_settings(self):
        """Открыть окно настроек"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            # Получаем обновлённые настройки
            self.settings = dialog.get_settings()
            # Сохраняем в QSettings
            self.save_settings()
            # Синхронизируем с вкладками
            self.text_tab.update_settings(self.settings)
            self.batch_tab.update_settings(self.settings)
            # Обновляем таблицу в batch_tab (для формата)
            self.batch_tab.scan_files()
            self.status_bar.showMessage("Настройки сохранены", 2000)
            logger.info(f"Настройки обновлены: голос={self.settings.voice}, "
                       f"ударения={self.settings.accent_model}, "
                       f"формат={self.settings.output_format}, "
                       f"битрейт={self.settings.mp3_bitrate}")
    
    def select_working_dir_from_menu(self):
        self.batch_tab.select_working_dir()
        if self.batch_tab.working_dir:
            self.text_tab.set_working_dir(self.batch_tab.working_dir)
    
    def clear_audio_from_menu(self):
        self.batch_tab.clear_audio()
    
    def load_settings(self):
        """Загрузка настроек из QSettings"""
        tts_settings = self.app_settings.get_tts_settings()
        self.settings.load_from_dict(tts_settings)
        logger.info(f"Настройки загружены из QSettings")
    
    def save_settings(self):
        """Сохранение настроек в QSettings"""
        self.app_settings.set_tts_settings(self.settings.to_dict())
        logger.info(f"Настройки сохранены в QSettings")
    
    def restore_window_geometry(self):
        geometry = self.app_settings.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        state = self.app_settings.get_window_state()
        if state:
            self.restoreState(state)
    
    def show_about(self):
        about_text = f"""
        <h2>{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}</h2>
        <p>Приложение для синтеза речи с поддержкой русского языка</p>
        <p><b>Компоненты:</b> Silero TTS, RUAccent, FFmpeg</p>
        <p><b>Настройки сохраняются автоматически</b></p>
        <ul>
            <li>Голос: {self.settings.voice}</li>
            <li>Ударения: {self.settings.accent_model}</li>
            <li>Формат: {self.settings.output_format}</li>
            <li>Битрейт: {self.settings.mp3_bitrate}</li>
            <li>Нормализация: {'вкл' if self.settings.normalize_audio else 'выкл'}</li>
            <li>Удаление тишины: {'вкл' if self.settings.remove_silence else 'выкл'}</li>
        </ul>
        """
        QMessageBox.about(self, "О программе", about_text)
    
    def closeEvent(self, event):
        self.app_settings.set_window_geometry(self.saveGeometry())
        self.app_settings.set_window_state(self.saveState())
        self.save_settings()
        logger.info("Приложение закрыто")
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setOrganizationName("TTSStudio")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()