"""Поток для синтеза речи"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import torch
import torchaudio
from datetime import datetime
import traceback
import sys
import re
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess

from config.settings import AppConfig, TTSSettings


class TTSWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, text: str, output_dir: Path, settings: TTSSettings):
        super().__init__()
        self.text = text
        self.output_dir = output_dir
        self.settings = settings
        self._model = None
        self._accentizer = None
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}", flush=True)
        sys.stdout.flush()
    
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 300) -> list:
        """Разбивает текст на небольшие chunks для синтеза"""
        sentences = re.split(r'([.!?;:]+)', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_with_ruaccent(self, text: str) -> str:
        """Обработка текста через RUAccent с выбором модели из настроек"""
        from ruaccent import RUAccent
        
        if self._accentizer is None:
            self._accentizer = RUAccent()
            
            # Выбор модели из настроек
            if self.settings.accent_model == 'accurate':
                model_type = 'big_poetry'
            else:
                model_type = 'turbo2'
            
            self.log(f"Загрузка модели RUAccent: {model_type}")
            
            self._accentizer.load(
                omograph_model_size=model_type,
                use_dictionary=True,
                device='CPU'
            )
            self.log("RUAccent загружен")
        
        # Разбиваем текст на части для стабильности
        chunks = self.split_text_into_chunks(text, max_chunk_size=200)
        self.log(f"Разбито на {len(chunks)} частей для расстановки ударений")
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if not self._is_running:
                return ""
            try:
                processed = self._accentizer.process_all(chunk)
                processed_chunks.append(processed)
            except Exception as e:
                self.log(f"Ошибка обработки части {i+1}: {e}")
                # При ошибке используем исходный текст без ударений
                processed_chunks.append(chunk)
        
        return ' '.join(processed_chunks)
    
    def save_audio(self, audio: torch.Tensor, output_path: Path, sample_rate: int = 48000):
        """Сохранение аудио в MP3 или WAV с указанным битрейтом"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Конвертируем в numpy
        audio_np = audio.cpu().numpy()
        
        # Нормализуем в int16
        if audio_np.dtype == torch.float32 or audio_np.dtype == torch.float64:
            max_val = np.max(np.abs(audio_np))
            if max_val > 0:
                audio_np = audio_np / max_val
            audio_np = (audio_np * 32767).astype(np.int16)
        
        # Временный WAV файл
        temp_wav = output_path.parent / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
        wavfile.write(str(temp_wav), sample_rate, audio_np)
        
        if self.settings.output_format == 'mp3':
            mp3_path = output_path.with_suffix('.mp3')
            bitrate_value = self.settings.mp3_bitrate.replace('k', '')
            self.log(f"Конвертация в MP3 с битрейтом {bitrate_value} kbps")
            
            cmd = [
                'ffmpeg', '-y', '-i', str(temp_wav),
                '-codec:a', 'libmp3lame',
                '-b:a', f'{bitrate_value}k',
                '-ar', str(sample_rate),
                '-ac', '2',
                str(mp3_path)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and mp3_path.exists():
                    temp_wav.unlink()
                    self.log(f"MP3 создан, размер: {mp3_path.stat().st_size / 1024:.1f} KB")
                    return mp3_path
                else:
                    raise Exception("FFmpeg error")
            except Exception as e:
                self.log(f"Ошибка конвертации: {e}")
                wav_path = output_path.with_suffix('.wav')
                temp_wav.rename(wav_path)
                return wav_path
        else:
            wav_path = output_path.with_suffix('.wav')
            temp_wav.rename(wav_path)
            self.log(f"WAV сохранён, размер: {wav_path.stat().st_size / 1024:.1f} KB")
            return wav_path
    
    def run(self):
        try:
            self.log("=== НАЧАЛО СИНТЕЗА ===")
            self.log(f"Длина текста: {len(self.text)} символов")
            self.log(f"Настройки: голос={self.settings.voice}, "
                    f"ударения={self.settings.accent_model}, "
                    f"формат={self.settings.output_format}, "
                    f"битрейт={self.settings.mp3_bitrate}")
            
            # Шаг 1: Расстановка ударений
            self.progress.emit(10, "Расстановка ударений...")
            text = self.process_with_ruaccent(self.text)
            
            if not text:
                self.error.emit("Ошибка обработки текста")
                return
            
            # Шаг 2: Загрузка Silero
            self.progress.emit(30, "Загрузка модели Silero...")
            if self._model is None:
                self._model, _ = torch.hub.load(
                    'snakers4/silero-models', 'silero_tts',
                    language='ru', speaker='v4_ru', trust_repo=True
                )
                self.log("Silero загружен")
            
            # Шаг 3: Синтез речи
            self.progress.emit(40, "Синтез речи...")
            chunks = self.split_text_into_chunks(text, max_chunk_size=300)
            audio_segments = []
            
            for i, chunk in enumerate(chunks):
                if not self._is_running:
                    self.log("Синтез прерван")
                    return
                
                self.progress.emit(40 + int((i / len(chunks)) * 50), f"Синтез части {i+1}/{len(chunks)}...")
                
                audio = self._model.apply_tts(
                    text=chunk,
                    speaker=self.settings.voice,
                    sample_rate=48000
                )
                audio_segments.append(audio)
                
                # Пауза между частями
                if i < len(chunks) - 1:
                    pause = torch.zeros(int(0.3 * 48000))
                    audio_segments.append(pause)
            
            if not audio_segments:
                self.error.emit("Не удалось синтезировать аудио")
                return
            
            audio = torch.cat(audio_segments)
            
            # Шаг 4: Сохранение
            self.progress.emit(90, "Сохранение аудио...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = self.output_dir / f"tts_{timestamp}"
            
            final_path = self.save_audio(audio, output_path, 48000)
            
            self.progress.emit(100, "Готово!")
            self.log(f"Сохранено: {final_path}")
            self.finished.emit(str(final_path))
            
        except Exception as e:
            self.log(f"ОШИБКА: {e}")
            self.log(traceback.format_exc())
            self.error.emit(str(e))