from PyQt5.QtCore import QThread, pyqtSignal, QEventLoop
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import traceback
import sys
import shutil
import gc
import psutil
import os

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
    
    def log_memory_usage(self):
        """Логирование использования памяти"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.log(f"Память: {memory_mb:.1f} MB")
        except Exception as e:
            self.log(f"Ошибка получения памяти: {e}")
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            total = len(self.files)
            results = []
            
            audio_dir = FileUtils.get_audio_dir(self.working_dir)
            
            self.log(f"Старт пакетной обработки: {total} файлов")
            self.log_memory_usage()
            
            for i, file_path in enumerate(self.files):
                if not self._is_running:
                    self.log("Остановлено пользователем")
                    break
                
                self.progress.emit(i + 1, total, file_path.name, "Обработка...")
                self.log(f"Обработка {i+1}/{total}: {file_path.name}")
                self.log_memory_usage()
                
                # Целевой путь
                target_path = FileUtils.get_audio_path_for_batch(
                    file_path, self.working_dir, self.settings.output_format
                )
                
                # Пропускаем если уже есть
                if target_path.exists() and target_path.stat().st_size > 10240:
                    self.log(f"Пропуск (уже существует): {file_path.name}")
                    self.file_completed.emit(str(file_path), str(target_path), 'success')
                    results.append({
                        'input': str(file_path), 
                        'output': str(target_path), 
                        'status': 'success'
                    })
                    continue
                
                # Читаем текст
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception as e:
                    self.log(f"Ошибка чтения {file_path.name}: {e}")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({
                        'input': str(file_path), 
                        'output': '', 
                        'status': 'error', 
                        'error': str(e)
                    })
                    continue
                
                if not text.strip():
                    self.log(f"Файл пуст: {file_path.name}")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({
                        'input': str(file_path), 
                        'output': '', 
                        'status': 'error', 
                        'error': 'Файл пуст'
                    })
                    continue
                
                # Создаём временную директорию для этого файла
                temp_dir = audio_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Создаём TTSWorker (модели будут загружены заново и выгружены после)
                worker = TTSWorker(text, temp_dir / "temp_output", self.settings)
                
                # Используем QEventLoop для ожидания сигнала
                loop = QEventLoop()
                result_path = None
                error_msg = None
                
                def on_finished(path):
                    nonlocal result_path
                    result_path = path
                    self.log(f"Получен сигнал finished: {path}")
                    loop.quit()
                
                def on_error(err):
                    nonlocal error_msg
                    error_msg = err
                    self.log(f"Получен сигнал error: {err}")
                    loop.quit()
                
                worker.finished.connect(on_finished)
                worker.error.connect(on_error)
                
                # Запускаем worker
                worker.start()
                
                # Ждём сигнал finished или error
                loop.exec_()
                
                # Обрабатываем результат
                if result_path and not error_msg and Path(result_path).exists():
                    # Создаём целевую директорию
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Перемещаем файл в целевое место с правильным именем
                    try:
                        shutil.move(result_path, target_path)
                        self.log(f"Файл сохранён: {target_path.name}, размер: {target_path.stat().st_size / 1024:.1f} KB")
                        
                        self.file_completed.emit(str(file_path), str(target_path), 'success')
                        results.append({
                            'input': str(file_path), 
                            'output': str(target_path), 
                            'status': 'success'
                        })
                    except Exception as e:
                        self.log(f"Ошибка перемещения: {e}")
                        self.file_completed.emit(str(file_path), '', 'error')
                        results.append({
                            'input': str(file_path), 
                            'output': '', 
                            'status': 'error', 
                            'error': str(e)
                        })
                else:
                    self.log(f"Ошибка синтеза {file_path.name}: {error_msg}")
                    self.file_completed.emit(str(file_path), '', 'error')
                    results.append({
                        'input': str(file_path), 
                        'output': '', 
                        'status': 'error', 
                        'error': error_msg or 'Неизвестная ошибка'
                    })
                
                # Модели уже выгружены в TTSWorker.unload_models()
                # Удаляем временную директорию
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    self.log(f"Ошибка удаления временной директории: {e}")
                
                # Принудительный сбор мусора
                gc.collect()
                
                # Задержка между файлами
                self.msleep(500)
                
                # Логируем память после обработки файла
                self.log_memory_usage()
            
            # Сохраняем лог
            FileUtils.save_processing_log(self.working_dir, results)
            self.log(f"Обработка завершена. Успешно: {len([r for r in results if r['status'] == 'success'])}")
            self.log_memory_usage()
            self.finished.emit()
            
        except Exception as e:
            self.log(f"Критическая ошибка: {e}")
            self.log(traceback.format_exc())
            self.error.emit(str(e))