from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List
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
        
    def stop(self):
        self._is_running = False
        
    def run(self):
        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break
            
            self.progress.emit(i + 1, len(self.files), file_path.name, "Обработка...")
            
            # Пропускаем если уже есть
            output_path = FileUtils.get_audio_path(file_path, self.working_dir, self.settings.output_format)
            if output_path.exists():
                self.file_completed.emit(str(file_path), str(output_path), 'success')
                continue
            
            # Читаем текст
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                self.file_completed.emit(str(file_path), '', 'error')
                continue
            
            if not text.strip():
                self.file_completed.emit(str(file_path), '', 'error')
                continue
            
            # Синтез
            audio_dir = FileUtils.get_audio_dir(self.working_dir)
            worker = TTSWorker(text, audio_dir, self.settings)
            
            # Ждём результат
            result = None
            def on_finished(path):
                nonlocal result
                result = path
            worker.finished.connect(on_finished)
            worker.start()
            worker.wait()
            
            if result:
                # Перемещаем в нужное место
                shutil.move(result, output_path)
                self.file_completed.emit(str(file_path), str(output_path), 'success')
            else:
                self.file_completed.emit(str(file_path), '', 'error')
        
        self.finished.emit()