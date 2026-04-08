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
        logger.info(f"Загружены настройки: голос={self.settings.voice}, "
                   f"ударения={self.settings.accent_model}, "
                   f"формат={self.settings.output_format}, "
                   f"битрейт={self.settings.mp3_bitrate}")
    
    def create_menu_bar(self):
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
        
        # Подменю Голос
        voice_menu = QMenu("🎤 Голос", self)
        self.voice_actions = {}
        for voice in AppConfig.AVAILABLE_VOICES:
            action = QAction(voice, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, v=voice: self.change_voice(v))
            voice_menu.addAction(action)
            self.voice_actions[voice] = action
        settings_menu.addMenu(voice_menu)
        
        settings_menu.addSeparator()
        
        # Подменю Качество ударений
        accent_menu = QMenu("📖 Качество ударений", self)
        self.accent_actions = {}
        fast_action = QAction("fast (быстро, turbo2)", self)
        fast_action.setCheckable(True)
        fast_action.triggered.connect(lambda checked: self.change_accent_model('fast'))
        accent_menu.addAction(fast_action)
        self.accent_actions['fast'] = fast_action
        accurate_action = QAction("accurate (точно, big_poetry)", self)
        accurate_action.setCheckable(True)
        accurate_action.triggered.connect(lambda checked: self.change_accent_model('accurate'))
        accent_menu.addAction(accurate_action)
        self.accent_actions['accurate'] = accurate_action
        settings_menu.addMenu(accent_menu)
        
        settings_menu.addSeparator()
        
        # Подменю Формат аудио
        format_menu = QMenu("💿 Формат аудио", self)
        self.format_actions = {}
        for fmt in ['mp3', 'wav']:
            action = QAction(fmt.upper(), self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, f=fmt: self.change_format(f))
            format_menu.addAction(action)
            self.format_actions[fmt] = action
        settings_menu.addMenu(format_menu)
        
        # Подменю Битрейт MP3
        self.bitrate_menu = QMenu("📊 Битрейт MP3", self)
        self.bitrate_actions = {}
        for bitrate in ['128k', '192k', '256k', '320k']:
            action = QAction(bitrate, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, b=bitrate: self.change_bitrate(b))
            self.bitrate_menu.addAction(action)
            self.bitrate_actions[bitrate] = action
        settings_menu.addMenu(self.bitrate_menu)
        
        # ===== Меню Помощь =====
        help_menu = menubar.addMenu("❓ Помощь")
        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Обновляем состояние меню
        self.update_menu_state()
    
    def update_menu_state(self):
        """Обновление галочек в меню в соответствии с текущими настройками"""
        for voice, action in self.voice_actions.items():
            action.setChecked(voice == self.settings.voice)
        
        self.accent_actions[self.settings.accent_model].setChecked(True)
        
        for fmt, action in self.format_actions.items():
            action.setChecked(fmt == self.settings.output_format)
        
        for bitrate, action in self.bitrate_actions.items():
            action.setChecked(bitrate == self.settings.mp3_bitrate)
        
        self.bitrate_menu.setEnabled(self.settings.output_format == 'mp3')
    
    def save_and_sync_settings(self):
        """Сохраняет настройки в QSettings и синхронизирует с вкладками"""
        # Сохраняем в QSettings
        self.app_settings.set_tts_settings(self.settings.to_dict())
        
        # Синхронизируем с вкладками
        self.text_tab.update_settings(self.settings)
        self.batch_tab.update_settings(self.settings)
        
        logger.info(f"Настройки сохранены: голос={self.settings.voice}, "
                   f"ударения={self.settings.accent_model}, "
                   f"формат={self.settings.output_format}, "
                   f"битрейт={self.settings.mp3_bitrate}")
    
    # ===== Обработчики изменения настроек =====
    
    def change_voice(self, voice: str):
        self.settings.voice = voice
        self.update_menu_state()
        self.save_and_sync_settings()
        self.status_bar.showMessage(f"Голос: {voice}", 2000)
    
    def change_accent_model(self, model: str):
        self.settings.accent_model = model
        self.update_menu_state()
        self.save_and_sync_settings()
        self.status_bar.showMessage(f"Режим ударений: {model}", 2000)
    
    def change_format(self, fmt: str):
        self.settings.output_format = fmt
        self.update_menu_state()
        self.save_and_sync_settings()
        self.status_bar.showMessage(f"Формат: {fmt.upper()}", 2000)
        # Обновляем таблицу в batch_tab для отображения статуса
        self.batch_tab.scan_files()
    
    def change_bitrate(self, bitrate: str):
        self.settings.mp3_bitrate = bitrate
        self.update_menu_state()
        self.save_and_sync_settings()
        self.status_bar.showMessage(f"Битрейт MP3: {bitrate}", 2000)
    
    # ===== Действия из меню =====
    
    def select_working_dir_from_menu(self):
        self.batch_tab.select_working_dir()
        if self.batch_tab.working_dir:
            self.text_tab.set_working_dir(self.batch_tab.working_dir)
    
    def clear_audio_from_menu(self):
        self.batch_tab.clear_audio()
    
    # ===== Загрузка/сохранение настроек =====
    
    def load_settings(self):
        """Загрузка настроек из QSettings"""
        tts_settings = self.app_settings.get_tts_settings()
        self.settings.load_from_dict(tts_settings)
        logger.info(f"Настройки загружены из QSettings")
    
    def save_settings(self):
        """Сохранение настроек в QSettings"""
        self.app_settings.set_tts_settings(self.settings.to_dict())
        logger.info(f"Настройки сохранены в QSettings")
    
    # ===== Геометрия окна =====
    
    def restore_window_geometry(self):
        geometry = self.app_settings.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        state = self.app_settings.get_window_state()
        if state:
            self.restoreState(state)
    
    # ===== О программе =====
    
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
        </ul>
        """
        QMessageBox.about(self, "О программе", about_text)
    
    def closeEvent(self, event):
        """Сохранение геометрии и настроек при закрытии"""
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