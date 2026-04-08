"""Оркестрация полного пайплайна обработки"""
from pathlib import Path
from typing import Callable, Optional
import time

from core.text_processor import TextProcessor
from core.tts_engine import SileroEngine
from core.audio_processor import AudioProcessor
from config.settings import TTSSettings, AppConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class TTSPipeline:
    """Основной пайплайн TTS"""
    
    def __init__(self, settings: TTSSettings = None):
        self.settings = settings or TTSSettings()
        self.text_processor = TextProcessor(accent_model=self.settings.accent_model)
        self.tts_engine = SileroEngine(sample_rate=self.settings.sample_rate)
        self.audio_processor = AudioProcessor()
        
        self.progress_callback: Optional[Callable[[int, str], None]] = None
        
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """Установка callback для отчета о прогрессе"""
        self.progress_callback = callback
    
    def _emit_progress(self, percent: int, message: str):
        """Отправка прогресса"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        logger.info(f"Progress {percent}%: {message}")
    
    def process_text(self, text: str, output_path: Path) -> Path:
        """
        Полная обработка текста в аудио
        
        Args:
            text: Исходный текст
            output_path: Путь для сохранения результата
            
        Returns:
            Путь к созданному аудиофайлу
        """
        start_time = time.time()
        
        try:
            # Шаг 1: Нормализация текста
            self._emit_progress(5, "Нормализация текста...")
            normalized_text = self.text_processor.normalize_text(text)
            
            # Шаг 2: Расстановка ударений
            self._emit_progress(15, "Расстановка ударений...")
            accented_text = self.text_processor.add_stress(normalized_text)
            
            # Разбивка на предложения (опционально)
            if self.settings.split_sentences:
                self._emit_progress(25, "Разбивка на предложения...")
                sentences = self.text_processor.split_into_sentences(accented_text)
                self._emit_progress(30, f"Синтез {len(sentences)} предложений...")
                
                # Синтез с паузами
                audio = self.tts_engine.synthesize_batch(
                    sentences,
                    voice=self.settings.voice,
                    pause=self.settings.sentence_pause
                )
            else:
                self._emit_progress(30, "Синтез речи...")
                audio = self.tts_engine.synthesize(
                    accented_text,
                    voice=self.settings.voice
                )
            
            # Шаг 4: Сохранение и постобработка
            self._emit_progress(70, "Сохранение аудио...")
            
            # Сначала сохраняем как WAV
            temp_output = output_path.with_suffix('.temp.wav')
            self.audio_processor.save_audio(
                audio, temp_output,
                sample_rate=self.settings.sample_rate,
                format="wav"
            )
            
            # Постобработка
            final_path = temp_output
            
            if self.settings.remove_silence:
                self._emit_progress(80, "Удаление тишины...")
                final_path = self.audio_processor.remove_silence(final_path)
            
            if self.settings.normalize_audio:
                self._emit_progress(90, "Нормализация громкости...")
                final_path = self.audio_processor.normalize_audio(final_path)
            
            # Конвертация в нужный формат
            self._emit_progress(95, f"Конвертация в {self.settings.output_format}...")
            final_path = self.audio_processor.convert_format(
                final_path,
                self.settings.output_format,
                bitrate=self.settings.mp3_bitrate
            )
            
            # Переименовываем в нужный путь
            expected_path = output_path.with_suffix(f'.{self.settings.output_format}')
            if final_path != expected_path:
                final_path.rename(expected_path)
                final_path = expected_path
            
            elapsed = time.time() - start_time
            logger.info(f"Обработка завершена за {elapsed:.2f} сек")
            
            self._emit_progress(100, "Готово!")
            return final_path
            
        except Exception as e:
            logger.error(f"Ошибка в пайплайне: {e}")
            raise
    
    def process_file(self, input_path: Path, output_dir: Path) -> Path:
        """
        Обработка текстового файла
        
        Args:
            input_path: Путь к текстовому файлу
            output_dir: Директория для сохранения
            
        Returns:
            Путь к созданному аудиофайлу
        """
        # Чтение файла
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Формирование имени выходного файла
        output_name = input_path.stem
        output_path = output_dir / output_name
        
        return self.process_text(text, output_path)