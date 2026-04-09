"""Диалог настроек приложения"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QPushButton, QGroupBox,
    QRadioButton, QButtonGroup, QSlider, QTabWidget,
    QWidget, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt

from config.settings import AppConfig, TTSSettings


class SettingsDialog(QDialog):
    """Окно настроек приложения"""
    
    def __init__(self, settings: TTSSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Создаём вкладки
        tabs = QTabWidget()
        
        # Вкладка: Основные настройки
        main_tab = self.create_main_tab()
        tabs.addTab(main_tab, "Основные")
        
        # Вкладка: Постобработка
        postprocess_tab = self.create_postprocess_tab()
        tabs.addTab(postprocess_tab, "Постобработка")
        
        # Вкладка: Эквалайзер
        eq_tab = self.create_eq_tab()
        tabs.addTab(eq_tab, "Эквалайзер")
        
        layout.addWidget(tabs)
        
        # Кнопки внизу
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
    
    def create_main_tab(self) -> QWidget:
        """Создание вкладки с основными настройками"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
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
        
        # ===== Группа: Синтез =====
        synthesis_group = QGroupBox("Синтез")
        synthesis_layout = QVBoxLayout()
        
        # Длина чанка
        chunk_row = QHBoxLayout()
        chunk_row.addWidget(QLabel("Длина чанка для синтеза:"))
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(150, 600)
        self.chunk_size_spin.setSingleStep(50)
        self.chunk_size_spin.setSuffix(" символов")
        self.chunk_size_spin.setToolTip("Короткие чанки (200-300) — стабильнее, длинные (400-600) — плавнее")
        chunk_row.addWidget(self.chunk_size_spin)
        chunk_row.addStretch()
        synthesis_layout.addLayout(chunk_row)
        
        # Пояснение
        chunk_info = QLabel("Совет: для длинных книг увеличьте чанк до 400-500 символов")
        chunk_info.setStyleSheet("color: gray; font-size: 10px;")
        synthesis_layout.addWidget(chunk_info)
        
        synthesis_group.setLayout(synthesis_layout)
        layout.addWidget(synthesis_group)
        
        layout.addStretch()
        
        return tab
    
    def create_postprocess_tab(self) -> QWidget:
        """Создание вкладки с настройками постобработки"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ===== Группа: Нормализация =====
        normalize_group = QGroupBox("Нормализация")
        normalize_layout = QVBoxLayout()
        
        self.normalize_cb = QCheckBox("Нормализация громкости (loudnorm)")
        self.normalize_cb.setToolTip("Выравнивает громкость аудио до стандартного уровня")
        normalize_layout.addWidget(self.normalize_cb)
        
        normalize_group.setLayout(normalize_layout)
        layout.addWidget(normalize_group)
        
        # ===== Группа: LogMMSE шумоподавление =====
        logmmse_group = QGroupBox("LogMMSE шумоподавление")
        logmmse_layout = QVBoxLayout()
        
        # Чекбокс включения
        self.logmmse_cb = QCheckBox("Включить LogMMSE шумоподавление")
        self.logmmse_cb.setToolTip("Убирает артефакты синтеза и хрипотцу")
        self.logmmse_cb.toggled.connect(self.on_logmmse_toggled)
        logmmse_layout.addWidget(self.logmmse_cb)
        
        # Интенсивность (initial_noise)
        noise_layout = QHBoxLayout()
        noise_layout.addWidget(QLabel("Интенсивность шумоподавления (initial_noise):"))
        self.logmmse_noise_slider = QSlider(Qt.Horizontal)
        self.logmmse_noise_slider.setRange(0, 20)
        self.logmmse_noise_slider.setTickInterval(5)
        self.logmmse_noise_slider.setTickPosition(QSlider.TicksBelow)
        self.logmmse_noise_slider.setFixedWidth(200)
        self.logmmse_noise_slider.valueChanged.connect(self.on_logmmse_noise_changed)
        noise_layout.addWidget(self.logmmse_noise_slider)
        self.logmmse_noise_label = QLabel("6")
        noise_layout.addWidget(self.logmmse_noise_label)
        noise_layout.addStretch()
        logmmse_layout.addLayout(noise_layout)
        
        # Размер окна (window_size)
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Размер окна анализа (window_size):"))
        self.logmmse_window_spin = QSpinBox()
        self.logmmse_window_spin.setRange(0, 10000)
        self.logmmse_window_spin.setSingleStep(100)
        self.logmmse_window_spin.setSuffix(" семплов")
        self.logmmse_window_spin.setToolTip("0 = автоматический выбор (0.02 × частота дискретизации)")
        window_layout.addWidget(self.logmmse_window_spin)
        window_layout.addStretch()
        logmmse_layout.addLayout(window_layout)
        
        # Порог VAD (noise_threshold)
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Порог обновления шума (noise_threshold):"))
        self.logmmse_threshold_spin = QDoubleSpinBox()
        self.logmmse_threshold_spin.setRange(0.0, 1.0)
        self.logmmse_threshold_spin.setSingleStep(0.01)
        self.logmmse_threshold_spin.setDecimals(2)
        self.logmmse_threshold_spin.setToolTip("Ниже этого порога профиль шума обновляется")
        threshold_layout.addWidget(self.logmmse_threshold_spin)
        threshold_layout.addStretch()
        logmmse_layout.addLayout(threshold_layout)
        
        # Пояснение
        logmmse_info = QLabel("Совет: initial_noise=6, window_size=0, noise_threshold=0.15 — оптимально для синтезированной речи")
        logmmse_info.setStyleSheet("color: gray; font-size: 10px;")
        logmmse_layout.addWidget(logmmse_info)
        
        logmmse_group.setLayout(logmmse_layout)
        layout.addWidget(logmmse_group)
        
        layout.addStretch()
        
        return tab
    
    def on_logmmse_toggled(self, checked: bool):
        """При включении/выключении LogMMSE обновляем состояние элементов"""
        self.logmmse_noise_slider.setEnabled(checked)
        self.logmmse_noise_label.setEnabled(checked)
        self.logmmse_window_spin.setEnabled(checked)
        self.logmmse_threshold_spin.setEnabled(checked)
    
    def on_logmmse_noise_changed(self, value: int):
        """Обновление отображения значения интенсивности LogMMSE"""
        self.logmmse_noise_label.setText(str(value))
    
    def create_eq_tab(self) -> QWidget:
        """Создание вкладки с эквалайзером (вертикальные слайдеры)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Чекбокс включения эквалайзера
        self.eq_enabled_cb = QCheckBox("Включить эквалайзер")
        self.eq_enabled_cb.setToolTip("Применять частотную коррекцию к аудио")
        layout.addWidget(self.eq_enabled_cb)
        
        # Контейнер для слайдеров
        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(20)
        
        # Данные для слайдеров: (частота, название)
        eq_bands = [
            (80, "80 Hz"),
            (200, "200 Hz"),
            (500, "500 Hz"),
            (1000, "1000 Hz"),
            (2000, "2000 Hz"),
            (4000, "4000 Hz"),
            (8000, "8000 Hz")
        ]
        
        self.eq_sliders = {}
        self.eq_labels = {}
        
        for freq, name in eq_bands:
            # Вертикальная колонка
            col_layout = QVBoxLayout()
            col_layout.setAlignment(Qt.AlignCenter)
            
            # Вертикальный слайдер
            slider = QSlider(Qt.Vertical)
            slider.setRange(-6, 6)
            slider.setTickInterval(1)
            slider.setTickPosition(QSlider.TicksRight)
            slider.setFixedHeight(200)
            slider.setFixedWidth(50)
            slider.valueChanged.connect(lambda v, f=freq: self.on_eq_value_changed(f, v))
            col_layout.addWidget(slider, alignment=Qt.AlignCenter)
            
            # Значение dB
            value_label = QLabel("0 dB")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setFixedWidth(50)
            col_layout.addWidget(value_label)
            
            # Подпись частоты
            freq_label = QLabel(name)
            freq_label.setAlignment(Qt.AlignCenter)
            freq_label.setFixedWidth(50)
            col_layout.addWidget(freq_label)
            
            sliders_layout.addLayout(col_layout)
            
            self.eq_sliders[freq] = slider
            self.eq_labels[freq] = value_label
        
        layout.addLayout(sliders_layout)
        
        # Кнопка сброса
        reset_btn = QPushButton("Сбросить все настройки эквалайзера")
        reset_btn.clicked.connect(self.reset_eq)
        layout.addWidget(reset_btn, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
        return tab
    
    def on_eq_value_changed(self, freq: int, value: int):
        """Обновление отображения значения dB для полосы"""
        label = self.eq_labels.get(freq)
        if label:
            if value > 0:
                label.setText(f"+{value} dB")
            else:
                label.setText(f"{value} dB")
    
    def reset_eq(self):
        """Сброс всех настроек эквалайзера в 0"""
        for freq, slider in self.eq_sliders.items():
            slider.setValue(0)
    
    def on_format_changed(self, fmt: str):
        """При изменении формата включаем/выключаем выбор битрейта"""
        self.bitrate_combo.setEnabled(fmt == "mp3")
    
    def load_settings(self):
        """Загрузка текущих настроек в UI"""
        # Основные настройки
        index = self.voice_combo.findText(self.settings.voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        
        if self.settings.accent_model == 'accurate':
            self.accent_accurate_radio.setChecked(True)
        else:
            self.accent_fast_radio.setChecked(True)
        
        index = self.format_combo.findText(self.settings.output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        
        index = self.bitrate_combo.findText(self.settings.mp3_bitrate)
        if index >= 0:
            self.bitrate_combo.setCurrentIndex(index)
        
        self.bitrate_combo.setEnabled(self.settings.output_format == "mp3")
        
        # Длина чанка
        self.chunk_size_spin.setValue(self.settings.chunk_size)
        
        # Настройки постобработки
        self.normalize_cb.setChecked(self.settings.normalize_audio)
        
        # LogMMSE
        self.logmmse_cb.setChecked(self.settings.logmmse_enabled)
        self.logmmse_noise_slider.setValue(self.settings.logmmse_initial_noise)
        self.logmmse_noise_label.setText(str(self.settings.logmmse_initial_noise))
        self.logmmse_window_spin.setValue(self.settings.logmmse_window_size)
        self.logmmse_threshold_spin.setValue(self.settings.logmmse_noise_threshold)
        
        # Обновляем состояние элементов LogMMSE
        enabled = self.settings.logmmse_enabled
        self.logmmse_noise_slider.setEnabled(enabled)
        self.logmmse_noise_label.setEnabled(enabled)
        self.logmmse_window_spin.setEnabled(enabled)
        self.logmmse_threshold_spin.setEnabled(enabled)
        
        # Настройки эквалайзера
        self.eq_enabled_cb.setChecked(self.settings.eq_enabled)
        
        self.eq_sliders[80].setValue(self.settings.eq_80)
        self.eq_sliders[200].setValue(self.settings.eq_200)
        self.eq_sliders[500].setValue(self.settings.eq_500)
        self.eq_sliders[1000].setValue(self.settings.eq_1000)
        self.eq_sliders[2000].setValue(self.settings.eq_2000)
        self.eq_sliders[4000].setValue(self.settings.eq_4000)
        self.eq_sliders[8000].setValue(self.settings.eq_8000)
    
    def get_settings_from_ui(self) -> dict:
        """Получить настройки из UI"""
        if self.accent_accurate_radio.isChecked():
            accent_model = 'accurate'
        else:
            accent_model = 'fast'
        
        return {
            'voice': self.voice_combo.currentText(),
            'accent_model': accent_model,
            'output_format': self.format_combo.currentText(),
            'mp3_bitrate': self.bitrate_combo.currentText(),
            'chunk_size': self.chunk_size_spin.value(),
            'normalize_audio': self.normalize_cb.isChecked(),
            'eq_enabled': self.eq_enabled_cb.isChecked(),
            'eq_80': self.eq_sliders[80].value(),
            'eq_200': self.eq_sliders[200].value(),
            'eq_500': self.eq_sliders[500].value(),
            'eq_1000': self.eq_sliders[1000].value(),
            'eq_2000': self.eq_sliders[2000].value(),
            'eq_4000': self.eq_sliders[4000].value(),
            'eq_8000': self.eq_sliders[8000].value(),
            'logmmse_enabled': self.logmmse_cb.isChecked(),
            'logmmse_initial_noise': self.logmmse_noise_slider.value(),
            'logmmse_window_size': self.logmmse_window_spin.value(),
            'logmmse_noise_threshold': self.logmmse_threshold_spin.value()
        }
    
    def apply_settings(self):
        """Применить настройки без закрытия окна"""
        new_settings = self.get_settings_from_ui()
        
        for key, value in new_settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
    
    def save_settings(self):
        """Сохранить настройки и закрыть окно"""
        self.apply_settings()
        self.accept()
    
    def get_settings(self) -> TTSSettings:
        """Получить обновлённые настройки"""
        return self.settings