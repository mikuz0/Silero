"""Обработка текста: нормализация и расстановка ударений"""
import re
import unicodedata
from typing import List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import TTSSettings


class TextProcessor:
    """Класс для обработки текста перед синтезом"""
    
    def __init__(self):
        self.accent_model = None
        self._load_accent_model()
    
    def _load_accent_model(self):
        """Загрузка модели расстановки ударений"""
        try:
            from ruaccent import RuAccent
            self.accent_model = RuAccent()
            self.accent_model.load(omograph_model='big_poetry')
            self.accent_model_fast = RuAccent()
            self.accent_model_fast.load(omograph_model='turbo2')
        except ImportError:
            print("RuAccent не установлен. Расстановка ударений недоступна.")
            self.accent_model = None
            self.accent_model_fast = None
        except Exception as e:
            print(f"Ошибка загрузки RuAccent: {e}")
            self.accent_model = None
            self.accent_model_fast = None
    
    def normalize_text(self, text: str) -> str:
        """Нормализация текста"""
        # Нормализация Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Замена множественных пробелов и переносов строк
        text = re.sub(r'\s+', ' ', text)
        
        # Удаление лишних пробелов в начале и конце
        text = text.strip()
        
        return text
    
    def apply_accents(self, text: str, model_type: str = "accurate") -> str:
        """Расстановка ударений в тексте"""
        if self.accent_model is None:
            return text
        
        try:
            if model_type == "fast" and self.accent_model_fast:
                return self.accent_model_fast.process_all(text)
            else:
                return self.accent_model.process_all(text)
        except Exception as e:
            print(f"Ошибка расстановки ударений: {e}")
            return text
    
    def split_sentences(self, text: str) -> List[str]:
        """Разбиение текста на предложения"""
        # Разбиение по знакам препинания
        sentences = re.split(r'[.!?;:]+', text)
        # Удаляем пустые предложения и очищаем
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def process(self, text: str, settings: TTSSettings) -> str:
        """Полная обработка текста"""
        # Нормализация
        text = self.normalize_text(text)
        
        # Расстановка ударений
        if settings.accent_model:
            text = self.apply_accents(text, settings.accent_model)
        
        return text