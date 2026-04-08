"""Движок синтеза речи на основе Silero"""
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Optional, Callable
from pydub import AudioSegment
import re
import unicodedata

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import TTSSettings, AppConfig
from core.text_processor import TextProcessor


class TTSEngine:
    """Основной класс для синтеза речи"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.speakers = {}
        self.progress_callback = progress_callback
        self.text_processor = TextProcessor()
        self._load_model()
    
    def _load_model(self):
        """Загрузка модели Silero"""
        if self.progress_callback:
            self.progress_callback("Загрузка модели Silero...", 0)
        
        # Путь к модели
        model_path = AppConfig.MODELS_DIR / "silero" / "model.pt"
        
        # Загружаем модель
        self.model = torch.package.PackageImporter(str(model_path)).load_pickle("tts_models", "model")
        self.model.to(self.device)
        
        # Получаем список доступных спикеров
        self.speakers = {
            'xenia': 'xenia',
            'aidar': 'aidar',
            'baya': 'baya',
            'kseniya': 'kseniya',
            'eugene': 'eugene'
        }
        
        if self.progress_callback:
            self.progress_callback("Модель загружена", 100)
    
    def synthesize_single(self, text: str, settings: TTSSettings) -> np.ndarray:
        """Синтез одного текста в аудио"""
        if not text or not text.strip():
            raise ValueError("Текст не может быть пустым")
        
        # Обработка текста (нормализация + ударения)
        text = self.text_processor.process(text, settings)
        
        # Разбиение на предложения (если нужно)
        if settings.split_sentences:
            sentences = self.text_processor.split_sentences(text)
            audio_chunks = []
            
            for i, sentence in enumerate(sentences):
                if self.progress_callback:
                    self.progress_callback(f"Синтез предложения {i+1}/{len(sentences)}", 
                                          int((i+1)/len(sentences)*100))
                
                # Синтез предложения
                audio = self._synthesize_text(sentence, settings)
                audio_chunks.append(audio)
                
                # Добавляем паузу между предложениями
                if i < len(sentences) - 1 and settings.sentence_pause > 0:
                    pause_samples = int(settings.sentence_pause * settings.sample_rate)
                    pause = np.zeros(pause_samples, dtype=np.float32)
                    audio_chunks.append(pause)
            
            # Объединяем все части
            result = np.concatenate(audio_chunks)
        else:
            # Синтез всего текста целиком
            if self.progress_callback:
                self.progress_callback("Синтез текста...", 50)
            result = self._synthesize_text(text, settings)
        
        if self.progress_callback:
            self.progress_callback("Синтез завершен", 100)
        
        return result
    
    def _synthesize_text(self, text: str, settings: TTSSettings) -> np.ndarray:
        """Непосредственный синтез текста моделью"""
        try:
            # Подготовка входных данных
            speaker = settings.voice
            
            # Синтез
            audio = self.model.apply_tts(
                text=text,
                speaker=speaker,
                sample_rate=settings.sample_rate
            )
            
            # Конвертируем в numpy array
            if torch.is_tensor(audio):
                audio = audio.cpu().numpy()
            
            return audio.astype(np.float32)
            
        except Exception as e:
            raise RuntimeError(f"Ошибка синтеза: {e}")
    
    def save_audio(self, audio_data: np.ndarray, output_path: str, settings: TTSSettings):
        """Сохранить аудио в файл с поддержкой MP3 и WAV"""
        from core.audio_processor import AudioProcessor
        
        # Постобработка аудио
        processor = AudioProcessor()
        
        if settings.normalize_audio:
            audio_data = processor.normalize_audio(audio_data)
        
        if settings.remove_silence:
            audio_data = processor.remove_silence(audio_data, settings.silence_threshold)
        
        # Создаем директорию если не существует
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем в нужном формате
        if settings.output_format == "wav":
            sf.write(output_path, audio_data, settings.sample_rate)
            
        elif settings.output_format == "mp3":
            # Сохраняем временный WAV
            temp_wav = Path(output_path).with_suffix('.temp.wav')
            sf.write(str(temp_wav), audio_data, settings.sample_rate)
            
            # Конвертируем в MP3
            audio_segment = AudioSegment.from_wav(str(temp_wav))
            audio_segment.export(
                output_path,
                format="mp3",
                bitrate=settings.mp3_bitrate
            )
            
            # Удаляем временный файл
            temp_wav.unlink()
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {settings.output_format}")
    
    def synthesize_batch(self, texts: List[str], output_dir: str, 
                        settings: TTSSettings, prefix: str = "audio") -> List[str]:
        """Пакетный синтез нескольких текстов"""
        output_files = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            if self.progress_callback:
                self.progress_callback(f"Синтез {i+1}/{total}", int((i+1)/total*100))
            
            try:
                # Синтез аудио
                audio = self.synthesize_single(text, settings)
                
                # Формируем имя файла
                extension = settings.output_format
                filename = f"{prefix}_{i+1:03d}.{extension}"
                output_path = Path(output_dir) / filename
                
                # Сохраняем
                self.save_audio(audio, str(output_path), settings)
                output_files.append(str(output_path))
                
            except Exception as e:
                print(f"Ошибка синтеза текста {i+1}: {e}")
                continue
        
        return output_files