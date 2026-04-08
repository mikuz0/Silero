from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QFileDialog, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt

from config.settings import AppConfig, TTSSettings, AppSettings
from workers.tts_worker import TTSWorker
from gui.widgets.audio_player import AudioPlayer
from utils.file_utils import FileUtils
from utils.logger import get_logger

logger = get_logger(__name__)


class TextTab(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.worker = None
        self.current_audio_file = None
        self.settings = TTSSettings()
        self.app_settings = AppSettings()
        self.working_dir = None
        
        self.init_ui()
        self.restore_working_dir()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info_layout = QHBoxLayout()
        self.working_dir_label = QLabel("📁 Рабочая папка: не выбрана")
        self.working_dir_label.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(self.working_dir_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        top_panel = QHBoxLayout()
        self.load_file_btn = QPushButton("📂 Загрузить файл")
        self.load_file_btn.clicked.connect(self.load_file)
        self.clear_btn = QPushButton("🗑️ Очистить")
        self.clear_btn.clicked.connect(self.clear_text)
        top_panel.addWidget(self.load_file_btn)
        top_panel.addWidget(self.clear_btn)
        top_panel.addStretch()
        layout.addLayout(top_panel)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Введите текст для озвучивания...")
        layout.addWidget(self.text_edit)
        
        self.stats_label = QLabel("Символов: 0 | Слов: 0 | Предложений: 0")
        self.text_edit.textChanged.connect(self.update_stats)
        layout.addWidget(self.stats_label)
        
        self.synthesize_btn = QPushButton("🎙️ Синтезировать речь")
        self.synthesize_btn.clicked.connect(self.start_synthesis)
        self.synthesize_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        layout.addWidget(self.synthesize_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        # Аудиоплеер
        self.audio_player = AudioPlayer()
        self.audio_player.setVisible(False)
        layout.addWidget(self.audio_player)
    
    def restore_working_dir(self):
        last_dir = self.app_settings.get_working_dir()
        if last_dir and Path(last_dir).exists():
            self.working_dir = Path(last_dir)
            self.working_dir_label.setText(f"📁 Рабочая папка: {self.working_dir}")
            self.working_dir_label.setStyleSheet("color: green; font-size: 10px;")
    
    def set_working_dir(self, working_dir: Path):
        self.working_dir = working_dir
        self.working_dir_label.setText(f"📁 Рабочая папка: {working_dir}")
        self.working_dir_label.setStyleSheet("color: green; font-size: 10px;")
    
    def update_stats(self):
        text = self.text_edit.toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = text.count('.') + text.count('!') + text.count('?') + text.count(';')
        self.stats_label.setText(f"Символов: {char_count} | Слов: {word_count} | Предложений: {sentence_count}")
    
    def load_file(self):
        initial_dir = str(Path.home())
        if self.working_dir:
            source_dir = FileUtils.get_source_dir(self.working_dir)
            if source_dir.exists():
                initial_dir = str(source_dir)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите текстовый файл", initial_dir,
            "Текстовые файлы (*.txt *.md *.rst);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.text_edit.setText(text)
                self.status_label.setText(f"Загружен: {Path(file_path).name}")
                logger.info(f"Загружен файл: {file_path}")
            except Exception as e:
                self.status_label.setText(f"Ошибка загрузки: {e}")
    
    def clear_text(self):
        self.text_edit.clear()
        self.current_audio_file = None
        self.audio_player.unload()
        self.audio_player.setVisible(False)
        self.status_label.setText("Текст очищен")
    
    def start_synthesis(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.status_label.setText("Введите текст для синтеза")
            return
        
        if not self.working_dir or not self.working_dir.exists():
            reply = QMessageBox.question(
                self, "Рабочая папка не выбрана",
                "Для сохранения аудио необходимо выбрать рабочую папку.\n\nВыбрать сейчас?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes and self.parent:
                self.parent.tab_widget.setCurrentIndex(1)
                self.parent.batch_tab.select_working_dir()
                self.working_dir = self.parent.batch_tab.working_dir
                if not self.working_dir:
                    return
            else:
                return
        
        audio_dir = FileUtils.get_audio_dir(self.working_dir)
        
        self.synthesize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Инициализация...")
        
        self.worker = TTSWorker(text, audio_dir, self.settings)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.synthesis_finished)
        self.worker.error.connect(self.synthesis_error)
        self.worker.start()
    
    def update_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def synthesis_finished(self, output_file):
        self.synthesize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        display_path = output_file
        if self.working_dir and str(output_file).startswith(str(self.working_dir)):
            display_path = str(Path(output_file).relative_to(self.working_dir))
        
        self.status_label.setText(f"✅ Готово! Сохранено: {display_path}")
        self.current_audio_file = output_file
        self.audio_player.load_file(output_file)
        self.audio_player.setVisible(True)
        logger.info(f"Синтез завершен: {output_file}")
    
    def synthesis_error(self, error_msg):
        self.synthesize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Ошибка: {error_msg[:100]}...")
        logger.error(f"Ошибка синтеза: {error_msg}")
    
    def update_settings(self, settings: TTSSettings):
        self.settings = settings
        self.status_label.setText(f"Настройки обновлены: голос {settings.voice}")