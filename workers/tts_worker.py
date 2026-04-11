"""Поток для синтеза речи"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import torch
from datetime import datetime
import traceback
import sys
import re
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess
import gc

from config.settings import AppConfig, TTSSettings


class TTSWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, text: str, output_path: Path, settings: TTSSettings):
        super().__init__()
        self.text = text
        self.output_path = output_path
        self.settings = settings
        self._model = None
        self._accentizer = None
        self._is_running = True
        
    def stop(self):
        self._is_running = False
    
    def unload_models(self):
        """Выгрузка моделей из памяти"""
        self.log("Выгрузка моделей из памяти...")
        if self._model is not None:
            del self._model
            self._model = None
        if self._accentizer is not None:
            del self._accentizer
            self._accentizer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.log("Модели выгружены")
        
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
        
        # Фильтруем пустые чанки
        return [chunk for chunk in chunks if chunk.strip()]
    
    def process_with_ruaccent(self, text: str) -> str:
        """Обработка текста через RUAccent с выбором модели из настроек"""
        from ruaccent import RUAccent
        
        # Всегда загружаем модель заново (не кэшируем между файлами)
        self.log("Загрузка модели RUAccent...")
        self._accentizer = RUAccent()
        
        if self.settings.accent_model == 'accurate':
            model_type = 'big_poetry'
        else:
            model_type = 'turbo2'
        
        self.log(f"Модель RUAccent: {model_type}")
        
        self._accentizer.load(
            omograph_model_size=model_type,
            use_dictionary=True,
            device='CPU'
        )
        self.log("RUAccent загружен")
        
        # Разбиваем на чанки по 150 символов для стабильности
        chunks = self.split_text_into_chunks(text, max_chunk_size=150)
        self.log(f"Разбито на {len(chunks)} частей для расстановки ударений")
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if not self._is_running:
                return ""
            try:
                processed = self._accentizer.process_all(chunk)
                processed_chunks.append(processed)
                self.log(f"Часть {i+1}/{len(chunks)} обработана")
            except Exception as e:
                self.log(f"Ошибка обработки части {i+1}: {e}")
                processed_chunks.append(chunk)
        
        result = ' '.join(processed_chunks)
        self.log(f"Расстановка ударений завершена, длина текста: {len(result)} символов")
        return result
    
    def load_silero(self):
        """Загрузка модели Silero"""
        self.log("Загрузка модели Silero...")
        self._model, _ = torch.hub.load(
            'snakers4/silero-models', 'silero_tts',
            language='ru', speaker='v4_ru', trust_repo=True
        )
        self.log("Silero загружен")
    
    def build_filters(self) -> str:
        """Построение строки фильтров для FFmpeg (эквалайзер)"""
        filters = []
        
        # Эквалайзер (7 полос)
        if self.settings.eq_enabled:
            if self.settings.eq_80 != 0:
                filters.append(f"equalizer=f=80:width_type=h:width=40:g={self.settings.eq_80}")
            if self.settings.eq_200 != 0:
                filters.append(f"equalizer=f=200:width_type=h:width=100:g={self.settings.eq_200}")
            if self.settings.eq_500 != 0:
                filters.append(f"equalizer=f=500:width_type=h:width=200:g={self.settings.eq_500}")
            if self.settings.eq_1000 != 0:
                filters.append(f"equalizer=f=1000:width_type=h:width=200:g={self.settings.eq_1000}")
            if self.settings.eq_2000 != 0:
                filters.append(f"equalizer=f=2000:width_type=h:width=400:g={self.settings.eq_2000}")
            if self.settings.eq_4000 != 0:
                filters.append(f"equalizer=f=4000:width_type=h:width=800:g={self.settings.eq_4000}")
            if self.settings.eq_8000 != 0:
                filters.append(f"equalizer=f=8000:width_type=h:width=1600:g={self.settings.eq_8000}")
        
        return ",".join(filters) if filters else "anull"
    
    def apply_logmmse(self, input_path: Path, output_path: Path, sample_rate: int) -> Path:
        """Применение LogMMSE шумоподавления с выгрузкой после использования"""
        
        self.log(f"Применение LogMMSE шумоподавления: "
                f"initial_noise={self.settings.logmmse_initial_noise}, "
                f"window_size={self.settings.logmmse_window_size}, "
                f"noise_threshold={self.settings.logmmse_noise_threshold}")
        
        try:
            # Динамический импорт
            import logmmse as logmmse_module
            
            # Читаем аудиофайл
            rate, data = wavfile.read(str(input_path))
            
            # Применяем LogMMSE с параметрами из настроек
            denoised = logmmse_module.logmmse(
                data, 
                rate, 
                initial_noise=self.settings.logmmse_initial_noise,
                window_size=self.settings.logmmse_window_size,
                noise_threshold=self.settings.logmmse_noise_threshold
            )
            
            # Сохраняем результат
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wavfile.write(str(output_path), rate, denoised.astype(np.int16))
            
            self.log(f"LogMMSE применён: {output_path}")
            
            # Принудительно удаляем модуль и очищаем память
            del logmmse_module
            gc.collect()
            
            return output_path
            
        except ImportError:
            self.log("LogMMSE не установлен. Установите: pip install logmmse")
            return input_path
        except Exception as e:
            self.log(f"Ошибка LogMMSE: {e}")
            return input_path
    
    def apply_normalization(self, input_path: Path, output_path: Path, sample_rate: int) -> Path:
        """Применение нормализации громкости через FFmpeg"""
        if not self.settings.normalize_audio:
            return input_path
        
        cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-af', 'loudnorm=I=-16:LRA=11:TP=-1.5',
            '-ar', str(sample_rate),
            '-ac', '2',
            str(output_path)
        ]
        
        self.log(f"Применение нормализации громкости...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and output_path.exists():
                self.log(f"Нормализация применена")
                return output_path
            else:
                self.log(f"Ошибка нормализации: {result.stderr}")
                return input_path
        except Exception as e:
            self.log(f"Ошибка нормализации: {e}")
            return input_path
    
    def save_audio(self, audio: torch.Tensor, output_path: Path, sample_rate: int = 48000):
        """Сохранение аудио в MP3 или WAV с постобработкой"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        audio_np = audio.cpu().numpy()
        
        if audio_np.dtype == torch.float32 or audio_np.dtype == torch.float64:
            max_val = np.max(np.abs(audio_np))
            if max_val > 0:
                audio_np = audio_np / max_val
            audio_np = (audio_np * 32767).astype(np.int16)
        
        # Временный WAV файл (сырой от Silero)
        temp_raw = output_path.parent / f"temp_raw_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
        wavfile.write(str(temp_raw), sample_rate, audio_np)
        self.log(f"Сырой WAV создан: {temp_raw.name}, размер: {temp_raw.stat().st_size / 1024:.1f} KB")
        
        current_file = temp_raw
        
        # Шаг 1: Применяем эквалайзер (если включён)
        filter_str = self.build_filters()
        if filter_str != "anull":
            temp_eq = output_path.parent / f"temp_eq_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
            
            cmd = [
                'ffmpeg', '-y', '-i', str(current_file),
                '-af', filter_str,
                '-ar', str(sample_rate),
                '-ac', '2',
                str(temp_eq)
            ]
            
            self.log(f"Применение эквалайзера...")
            self.log(f"Фильтры: {filter_str[:100]}...")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and temp_eq.exists():
                    current_file.unlink()
                    current_file = temp_eq
                    self.log(f"Эквалайзер применён")
                else:
                    self.log(f"Ошибка эквалайзера: {result.stderr}")
            except Exception as e:
                self.log(f"Ошибка эквалайзера: {e}")
        
        # Шаг 2: Применяем нормализацию громкости (если включена)
        if self.settings.normalize_audio:
            temp_norm = output_path.parent / f"temp_norm_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
            result_file = self.apply_normalization(current_file, temp_norm, sample_rate)
            if result_file != current_file:
                current_file.unlink()
                current_file = result_file
        
        # Шаг 3: Применяем LogMMSE шумоподавление (если включено)
        if self.settings.logmmse_enabled:
            temp_denoised = output_path.parent / f"temp_denoised_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
            result_file = self.apply_logmmse(current_file, temp_denoised, sample_rate)
            if result_file != current_file:
                current_file.unlink()
                current_file = result_file
        
        # Шаг 4: Финальная конвертация в MP3 или WAV
        if self.settings.output_format == 'mp3':
            final_path = output_path.with_suffix('.mp3')
            bitrate_value = self.settings.mp3_bitrate.replace('k', '')
            
            cmd = [
                'ffmpeg', '-y', '-i', str(current_file),
                '-codec:a', 'libmp3lame',
                '-b:a', f'{bitrate_value}k',
                '-ar', str(sample_rate),
                '-ac', '2',
                str(final_path)
            ]
            
            self.log(f"Конвертация в MP3 с битрейтом {bitrate_value} kbps")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and final_path.exists():
                    self.log(f"MP3 создан, размер: {final_path.stat().st_size / 1024:.1f} KB")
                    
                    # Проверяем битрейт
                    try:
                        probe_cmd = [
                            'ffprobe', '-v', 'error',
                            '-select_streams', 'a:0',
                            '-show_entries', 'format=bit_rate',
                            '-of', 'default=noprint_wrappers=1:nokey=1',
                            str(final_path)
                        ]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                        if probe_result.returncode == 0 and probe_result.stdout.strip():
                            actual_bitrate = int(probe_result.stdout.strip()) // 1000
                            self.log(f"Фактический битрейт: {actual_bitrate} kbps")
                    except:
                        pass
                    
                    # Удаляем временные файлы
                    if current_file.exists() and current_file != final_path:
                        current_file.unlink()
                    
                    return final_path
                else:
                    raise Exception("FFmpeg error")
            except Exception as e:
                self.log(f"Ошибка конвертации в MP3: {e}")
                # Если конвертация не удалась, сохраняем WAV
                wav_path = output_path.with_suffix('.wav')
                current_file.rename(wav_path)
                return wav_path
        else:
            final_path = output_path.with_suffix('.wav')
            current_file.rename(final_path)
            self.log(f"WAV сохранён, размер: {final_path.stat().st_size / 1024:.1f} KB")
            return final_path
    
    def synthesize_text(self, text: str) -> torch.Tensor:
        """Синтез текста с разбивкой на чанки"""
        chunks = self.split_text_into_chunks(text, max_chunk_size=self.settings.chunk_size)
        
        # Фильтруем пустые чанки (0 символов)
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        if not chunks:
            self.log("Нет текста для синтеза (все чанки пустые)")
            return None
        
        self.log(f"Разбито на {len(chunks)} частей для синтеза (размер чанка: {self.settings.chunk_size})")
        
        audio_segments = []
        
        for i, chunk in enumerate(chunks):
            if not self._is_running:
                return None
            
            self.log(f"Синтез части {i+1}/{len(chunks)}: {len(chunk)} символов")
            
            audio = self._model.apply_tts(
                text=chunk,
                speaker=self.settings.voice,
                sample_rate=48000
            )
            audio_segments.append(audio)
            
            if i < len(chunks) - 1:
                pause = torch.zeros(int(0.3 * 48000))
                audio_segments.append(pause)
        
        return torch.cat(audio_segments) if audio_segments else None
    
    def run(self):
        try:
            self.log("=== НАЧАЛО СИНТЕЗА ===")
            self.log(f"Длина текста: {len(self.text)} символов")
            self.log(f"Путь сохранения: {self.output_path}")
            self.log(f"Настройки: голос={self.settings.voice}, "
                    f"ударения={self.settings.accent_model}, "
                    f"формат={self.settings.output_format}, "
                    f"битрейт={self.settings.mp3_bitrate}, "
                    f"чанк={self.settings.chunk_size}, "
                    f"эквалайзер={'вкл' if self.settings.eq_enabled else 'выкл'}, "
                    f"нормализация={'вкл' if self.settings.normalize_audio else 'выкл'}, "
                    f"LogMMSE={'вкл' if self.settings.logmmse_enabled else 'выкл'}")
            
            # Шаг 1: Расстановка ударений (всегда загружаем модель заново)
            self.progress.emit(10, "Расстановка ударений...")
            text = self.process_with_ruaccent(self.text)
            
            if not text:
                self.error.emit("Ошибка обработки текста")
                return
            
            # Шаг 2: Загрузка Silero (всегда загружаем заново)
            self.progress.emit(30, "Загрузка модели Silero...")
            self.load_silero()
            
            # Шаг 3: Синтез речи
            self.progress.emit(40, "Синтез речи...")
            audio = self.synthesize_text(text)
            
            if audio is None:
                self.error.emit("Синтез прерван")
                return
            
            # Шаг 4: Сохранение и постобработка
            self.progress.emit(90, "Сохранение и постобработка...")
            final_path = self.save_audio(audio, self.output_path, 48000)
            
            self.progress.emit(100, "Готово!")
            self.log(f"Сохранено: {final_path}")
            self.finished.emit(str(final_path))
            
        except Exception as e:
            self.log(f"ОШИБКА: {e}")
            self.log(traceback.format_exc())
            self.error.emit(str(e))
        finally:
            # Выгружаем модели из памяти
            self.unload_models()