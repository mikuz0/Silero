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
            'remove_silence': self.qsettings.value('tts_remove_silence', True, type=bool),
            'split_sentences': self.qsettings.value('tts_split_sentences', True, type=bool),
            'sentence_pause': self.qsettings.value('tts_sentence_pause', 0.3, type=float)
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
        self.remove_silence = True
        self.silence_threshold = -50
    
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
            'remove_silence': self.remove_silence,
            'silence_threshold': self.silence_threshold
        }