"""Постобработка аудио"""
import numpy as np
from typing import Optional


class AudioProcessor:
    """Класс для постобработки аудио"""
    
    @staticmethod
    def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """Нормализация громкости аудио"""
        # Вычисляем текущую RMS
        rms = np.sqrt(np.mean(audio ** 2))
        if rms == 0:
            return audio
        
        # Целевая RMS (линейная шкала)
        target_rms = 10 ** (target_db / 20)
        
        # Коэффициент усиления
        gain = target_rms / rms
        
        # Применяем усиление с ограничением
        audio = audio * gain
        
        # Ограничиваем значения в диапазоне [-1, 1]
        audio = np.clip(audio, -1.0, 1.0)
        
        return audio
    
    @staticmethod
    def remove_silence(audio: np.ndarray, threshold_db: float = -50.0, 
                      min_silence_len: int = 500) -> np.ndarray:
        """Удаление тишины в начале и конце аудио"""
        # Преобразуем порог из dB в линейную шкалу
        threshold = 10 ** (threshold_db / 20)
        
        # Находим первый и последний индекс, превышающий порог
        non_silent = np.abs(audio) > threshold
        
        if not np.any(non_silent):
            return audio
        
        # Индексы первого и последнего не-тихого сэмпла
        start = np.argmax(non_silent)
        end = len(audio) - np.argmax(non_silent[::-1])
        
        # Обрезаем аудио
        trimmed = audio[start:end]
        
        return trimmed