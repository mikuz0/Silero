from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import traceback
import sys
import shutil

from config.settings import TTSSettings
from utils.file_utils import FileUtils
from workers.tts_worker import TTSWorker


class BatchWorker(QThread):
    
    progress = pyqtSignal(int, int, str, str)
    file_completed = pyqtSignal(str, str, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, files: List[Path], working_dir: Path, settings: TTSSettings):
        super().__init__()
        self.files = files
        self.working_dir = working_dir
        self.settings = settings
        self._is_running = True
        
    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [BATCH] {message}", flush=True)
        sys.stdout.flush()
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            total = len(self.files)
            results = []
            
            for i, file_path in enumerate(self.files):
                if not self._is_running:
                    self.log("Остановлено пользователем")
                    break
                
                self.progress.emit(i + 1, total, file_path.name, "Обработка...")
                self.log(f"Обработка {i+1}/{total}: {file_path.name}")
                
                # Целевой путь для аудио
                output_path = FileUtils.get_audio_path_for_batch(
                    file_path, self.working_dir, self.settings.output_format
                )
                
                # Пропускаем если уже есть
                if output_path.exists() and output_path.stat().st_size > 10240:
                    self.log(f"Пропуск (уже существует): {file_path.name}")
                    self.file_completed.emit(str(file_path), str(output_path), 'success')
                    results.append({'input': str(file_path), 'output': str(output_path), 'status': 'success'})
                    continue
                
                # Читаем текст
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception as e:
                    self.log(f"Ошибка чтения: {e}")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({'input': str(file_path), 'output': '', 'status': 'error', 'error': str(e)})
                    continue
                
                if not text.strip():
                    self.log(f"Файл пуст: {file_path.name}")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({'input': str(file_path), 'output': '', 'status': 'error', 'error': 'Файл пуст'})
                    continue
                
                # Создаём worker с готовым путём
                worker = TTSWorker(text, output_path, self.settings)
                
                # Ждём завершения
                worker.start()
                worker.wait()
                
                # Проверяем результат
                if output_path.exists() and output_path.stat().st_size > 1024:
                    self.log(f"Файл создан: {output_path.name}")
                    self.file_completed.emit(str(file_path), str(output_path), 'success')
                    results.append({'input': str(file_path), 'output': str(output_path), 'status': 'success'})
                else:
                    self.log(f"Ошибка: файл не создан")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({'input': str(file_path), 'output': '', 'status': 'error', 'error': 'Файл не создан'})
                
                # Очищаем
                worker.deleteLater()
                
                # Небольшая задержка
                self.msleep(500)
            
            FileUtils.save_processing_log(self.working_dir, results)
            self.log(f"Обработка завершена. Успешно: {len([r for r in results if r['status'] == 'success'])}")
            self.finished.emit()
            
        except Exception as e:
            self.log(f"Критическая ошибка: {e}")
            self.log(traceback.format_exc())
            self.error.emit(str(e))