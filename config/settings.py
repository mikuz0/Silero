"""Конфигурация приложения"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from PyQt5.QtCore import QSettings


@dataclass
class AppConfig:
    """Основные настройки приложения"""
    APP_NAME = "TTS Studio"
    APP_VERSION = "1.0.0"
    BASE_DIR = Path(__file__).parent.parent
    MODELS_DIR = BASE_DIR / "models"
    OUTPUT_DIR = BASE_DIR / "output"
    
    SAMPLE_RATE = 48000
    DEFAULT_VOICE = "xenia"
    AVAILABLE_VOICES = ["xenia", "aidar", "baya", "kseniya", "eugene"]
    
    ACCENT_MODELS = {
        "fast": "turbo2",
        "accurate": "big_poetry"
    }
    
    DEFAULT_MP3_BITRATE = "192k"
    DEFAULT_OUTPUT_FORMAT = "mp3"
    DEFAULT_CHUNK_SIZE = 300
    
    # Значения по умолчанию для LogMMSE
    DEFAULT_LOGMMSE_INITIAL_NOISE = 6
    DEFAULT_LOGMMSE_WINDOW_SIZE = 0
    DEFAULT_LOGMMSE_NOISE_THRESHOLD = 0.15
    
    SUPPORTED_INPUT = ['.txt', '.md', '.rst']
    
    @classmethod
    def ensure_dirs(cls):
        """Создание необходимых директорий"""
        cls.MODELS_DIR.mkdir(exist_ok=True)
        (cls.MODELS_DIR / "ruaccent").mkdir(exist_ok=True)
        (cls.MODELS_DIR / "silero").mkdir(exist_ok=True)
        
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        (cls.OUTPUT_DIR / "single").mkdir(exist_ok=True)
        (cls.OUTPUT_DIR / "batch").mkdir(exist_ok=True)


class AppSettings:
    """Управление сохранением настроек приложения"""
    
    def __init__(self):
        self.qsettings = QSettings('TTSStudio', 'Settings')
    
    def get_working_dir(self) -> str:
        return self.qsettings.value('working_dir', '')
    
    def set_working_dir(self, path: str):
        self.qsettings.setValue('working_dir', path)
    
    def get_window_geometry(self):
        return self.qsettings.value('window_geometry')
    
    def set_window_geometry(self, geometry):
        self.qsettings.setValue('window_geometry', geometry)
    
    def get_window_state(self):
        return self.qsettings.value('window_state')
    
    def set_window_state(self, state):
        self.qsettings.setValue('window_state', state)
    
    def get_tts_settings(self) -> Dict:
        return {
            'voice': self.qsettings.value('tts_voice', 'xenia'),
            'accent_model': self.qsettings.value('tts_accent_model', 'accurate'),
            'output_format': self.qsettings.value('tts_output_format', 'mp3'),
            'mp3_bitrate': self.qsettings.value('tts_mp3_bitrate', '192k'),
            'normalize_audio': self.qsettings.value('tts_normalize_audio', True, type=bool),
            'split_sentences': self.qsettings.value('tts_split_sentences', True, type=bool),
            'sentence_pause': self.qsettings.value('tts_sentence_pause', 0.3, type=float),
            'chunk_size': self.qsettings.value('tts_chunk_size', 300, type=int),
            'eq_enabled': self.qsettings.value('tts_eq_enabled', False, type=bool),
            'eq_80': self.qsettings.value('tts_eq_80', 0, type=int),
            'eq_200': self.qsettings.value('tts_eq_200', 0, type=int),
            'eq_500': self.qsettings.value('tts_eq_500', 0, type=int),
            'eq_1000': self.qsettings.value('tts_eq_1000', 0, type=int),
            'eq_2000': self.qsettings.value('tts_eq_2000', 0, type=int),
            'eq_4000': self.qsettings.value('tts_eq_4000', 0, type=int),
            'eq_8000': self.qsettings.value('tts_eq_8000', 0, type=int),
            'logmmse_enabled': self.qsettings.value('tts_logmmse_enabled', False, type=bool),
            'logmmse_initial_noise': self.qsettings.value('tts_logmmse_initial_noise', 6, type=int),
            'logmmse_window_size': self.qsettings.value('tts_logmmse_window_size', 0, type=int),
            'logmmse_noise_threshold': self.qsettings.value('tts_logmmse_noise_threshold', 0.15, type=float)
        }
    
    def set_tts_settings(self, settings: Dict):
        for key, value in settings.items():
            self.qsettings.setValue(f'tts_{key}', value)


class TTSSettings:
    """Настройки синтеза речи"""
    def __init__(self):
        self.voice = "xenia"
        self.sample_rate = 48000
        self.accent_model = "accurate"
        self.normalize_text = True
        self.split_sentences = True
        self.sentence_pause = 0.3
        self.output_format = "mp3"
        self.mp3_bitrate = "192k"
        self.normalize_audio = True
        self.chunk_size = 300
        
        # Параметры эквалайзера
        self.eq_enabled = False
        self.eq_80 = 0
        self.eq_200 = 0
        self.eq_500 = 0
        self.eq_1000 = 0
        self.eq_2000 = 0
        self.eq_4000 = 0
        self.eq_8000 = 0
        
        # Параметры LogMMSE
        self.logmmse_enabled = False
        self.logmmse_initial_noise = 6
        self.logmmse_window_size = 0
        self.logmmse_noise_threshold = 0.15
    
    def load_from_dict(self, data: Dict):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict:
        return {
            'voice': self.voice,
            'sample_rate': self.sample_rate,
            'accent_model': self.accent_model,
            'normalize_text': self.normalize_text,
            'split_sentences': self.split_sentences,
            'sentence_pause': self.sentence_pause,
            'output_format': self.output_format,
            'mp3_bitrate': self.mp3_bitrate,
            'normalize_audio': self.normalize_audio,
            'chunk_size': self.chunk_size,
            'eq_enabled': self.eq_enabled,
            'eq_80': self.eq_80,
            'eq_200': self.eq_200,
            'eq_500': self.eq_500,
            'eq_1000': self.eq_1000,
            'eq_2000': self.eq_2000,
            'eq_4000': self.eq_4000,
            'eq_8000': self.eq_8000,
            'logmmse_enabled': self.logmmse_enabled,
            'logmmse_initial_noise': self.logmmse_initial_noise,
            'logmmse_window_size': self.logmmse_window_size,
            'logmmse_noise_threshold': self.logmmse_noise_threshold
        }