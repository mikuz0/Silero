"""Диалог настроек приложения"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QPushButton, QGroupBox,
    QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt

from config.settings import AppConfig, TTSSettings


class SettingsDialog(QDialog):
    """Окно настроек приложения"""
    
    def __init__(self, settings: TTSSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)
        self.setModal(True)
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # ===== Группа: Голос =====
        voice_group = QGroupBox("Голос")
        voice_layout = QVBoxLayout()
        
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(AppConfig.AVAILABLE_VOICES)
        voice_layout.addWidget(self.voice_combo)
        
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # ===== Группа: Качество ударений =====
        accent_group = QGroupBox("Качество ударений")
        accent_layout = QVBoxLayout()
        
        self.accent_fast_radio = QRadioButton("fast (быстро, turbo2)")
        self.accent_fast_radio.setToolTip("Быстрая модель, подходит для коротких текстов")
        
        self.accent_accurate_radio = QRadioButton("accurate (точно, big_poetry)")
        self.accent_accurate_radio.setToolTip("Точная модель, требует больше памяти и времени")
        
        self.accent_group = QButtonGroup()
        self.accent_group.addButton(self.accent_fast_radio, 0)
        self.accent_group.addButton(self.accent_accurate_radio, 1)
        
        accent_layout.addWidget(self.accent_fast_radio)
        accent_layout.addWidget(self.accent_accurate_radio)
        
        accent_group.setLayout(accent_layout)
        layout.addWidget(accent_group)
        
        # ===== Группа: Постобработка =====
        postprocess_group = QGroupBox("Постобработка")
        postprocess_layout = QVBoxLayout()
        
        self.normalize_cb = QCheckBox("Нормализация громкости")
        self.normalize_cb.setToolTip("Выравнивает громкость аудио")
        
        self.remove_silence_cb = QCheckBox("Удаление тишины в начале и конце")
        self.remove_silence_cb.setToolTip("Обрезает длинные паузы")
        
        postprocess_layout.addWidget(self.normalize_cb)
        postprocess_layout.addWidget(self.remove_silence_cb)
        
        postprocess_group.setLayout(postprocess_layout)
        layout.addWidget(postprocess_group)
        
        # ===== Группа: Формат и битрейт =====
        format_group = QGroupBox("Формат аудио")
        format_layout = QVBoxLayout()
        
        # Формат
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp3", "wav"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        format_layout.addLayout(format_row)
        
        # Битрейт
        bitrate_row = QHBoxLayout()
        bitrate_row.addWidget(QLabel("Битрейт MP3:"))
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["128k", "192k", "256k", "320k"])
        bitrate_row.addWidget(self.bitrate_combo)
        bitrate_row.addStretch()
        format_layout.addLayout(bitrate_row)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # ===== Кнопки =====
        btn_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.apply_settings)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def on_format_changed(self, fmt: str):
        """При изменении формата включаем/выключаем выбор битрейта"""
        self.bitrate_combo.setEnabled(fmt == "mp3")
    
    def load_settings(self):
        """Загрузка текущих настроек в UI"""
        # Голос
        index = self.voice_combo.findText(self.settings.voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        
        # Ударения
        if self.settings.accent_model == 'accurate':
            self.accent_accurate_radio.setChecked(True)
        else:
            self.accent_fast_radio.setChecked(True)
        
        # Постобработка
        self.normalize_cb.setChecked(self.settings.normalize_audio)
        self.remove_silence_cb.setChecked(self.settings.remove_silence)
        
        # Формат
        index = self.format_combo.findText(self.settings.output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        
        # Битрейт
        index = self.bitrate_combo.findText(self.settings.mp3_bitrate)
        if index >= 0:
            self.bitrate_combo.setCurrentIndex(index)
        
        # Обновляем состояние битрейта
        self.bitrate_combo.setEnabled(self.settings.output_format == "mp3")
    
    def get_settings_from_ui(self) -> dict:
        """Получить настройки из UI"""
        # Определяем модель ударений
        if self.accent_accurate_radio.isChecked():
            accent_model = 'accurate'
        else:
            accent_model = 'fast'
        
        return {
            'voice': self.voice_combo.currentText(),
            'accent_model': accent_model,
            'normalize_audio': self.normalize_cb.isChecked(),
            'remove_silence': self.remove_silence_cb.isChecked(),
            'output_format': self.format_combo.currentText(),
            'mp3_bitrate': self.bitrate_combo.currentText()
        }
    
    def apply_settings(self):
        """Применить настройки без закрытия окна"""
        new_settings = self.get_settings_from_ui()
        
        # Обновляем объект настроек
        for key, value in new_settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        # Сигнал о применении (можно использовать для обновления UI)
        self.accept()  # Временно закрываем, можно заменить на сигнал
    
    def save_settings(self):
        """Сохранить настройки и закрыть окно"""
        self.apply_settings()
        self.accept()
    
    def get_settings(self) -> TTSSettings:
        """Получить обновлённые настройки"""
        return self.settings