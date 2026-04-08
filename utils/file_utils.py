"""Утилиты для работы с файлами и папками"""
from pathlib import Path
from typing import List, Dict, Optional
import shutil
from datetime import datetime

from config.settings import AppConfig


class FileUtils:
    
    @staticmethod
    def scan_text_files(directory: Path, recursive: bool = True) -> List[Path]:
        """Сканирование папки на наличие текстовых файлов"""
        if not directory.exists():
            return []
        
        pattern = '**/*' if recursive else '*'
        text_files = []
        
        for ext in AppConfig.SUPPORTED_INPUT:
            text_files.extend(directory.glob(f'{pattern}{ext}'))
        
        return sorted(set(text_files))
    
    @staticmethod
    def get_audio_path_for_batch(text_file: Path, working_dir: Path, output_format: str = 'mp3') -> Path:
        """
        Для пакетной обработки: имя аудиофайла совпадает с именем исходного файла
        Пример: source/chapter_01.txt → audio/chapter_01.mp3
        """
        try:
            # Получаем путь относительно папки source
            rel_path = text_file.relative_to(working_dir / 'source')
        except ValueError:
            # Если файл не в source, используем просто имя
            rel_path = Path(text_file.name)
        
        # Заменяем расширение и помещаем в audio/
        return working_dir / 'audio' / rel_path.with_suffix(f'.{output_format}')
    
    @staticmethod
    def get_audio_path_for_single(output_dir: Path, output_format: str = 'mp3') -> Path:
        """
        Для вкладки Текст: уникальное имя с временной меткой
        Пример: output/tts_20260407_223015_123456.mp3
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # убираем последние 3 цифры микросекунд
        return output_dir / f"tts_{timestamp}.{output_format}"
    
    @staticmethod
    def get_source_dir(working_dir: Path) -> Path:
        """Получить папку с исходными текстами"""
        source_dir = working_dir / 'source'
        source_dir.mkdir(parents=True, exist_ok=True)
        return source_dir
    
    @staticmethod
    def get_audio_dir(working_dir: Path) -> Path:
        """Получить папку с аудиофайлами"""
        audio_dir = working_dir / 'audio'
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir
    
    @staticmethod
    def get_logs_dir(working_dir: Path) -> Path:
        """Получить папку с логами"""
        logs_dir = working_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    
    @staticmethod
    def get_cache_dir(working_dir: Path) -> Path:
        """Получить папку с кэшем"""
        cache_dir = working_dir / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def get_file_status(text_file: Path, working_dir: Path, output_format: str = 'mp3') -> str:
        """Определить статус файла: 'pending' или 'completed'"""
        audio_path = FileUtils.get_audio_path_for_batch(text_file, working_dir, output_format)
        if audio_path.exists() and audio_path.stat().st_size > 1024:
            return 'completed'
        return 'pending'
    
    @staticmethod
    def clear_audio_files(working_dir: Path):
        """Удалить все сгенерированные аудиофайлы"""
        audio_dir = FileUtils.get_audio_dir(working_dir)
        if audio_dir.exists():
            shutil.rmtree(audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_processing_log(working_dir: Path, results: List[Dict]) -> Path:
        """Сохранить лог обработки"""
        logs_dir = FileUtils.get_logs_dir(working_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"session_{timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"TTS Studio - Пакетная обработка\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Рабочая папка: {working_dir}\n")
            f.write("=" * 60 + "\n\n")
            
            success_count = sum(1 for r in results if r.get('status') == 'success')
            error_count = sum(1 for r in results if r.get('status') == 'error')
            
            f.write(f"Обработано файлов: {len(results)}\n")
            f.write(f"Успешно: {success_count}\n")
            f.write(f"Ошибок: {error_count}\n\n")
            
            f.write("Детали:\n")
            for result in results:
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                f.write(f"{status_icon} {result.get('input', '')} → {result.get('output', '')}\n")
                if result.get('error'):
                    f.write(f"   Ошибка: {result['error']}\n")
            
            f.write("\n" + "=" * 60 + "\n")
        
        return log_file


class ProcessingState:
    
    STATE_FILE = "processing_state.json"
    
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.state_path = FileUtils.get_cache_dir(working_dir) / self.STATE_FILE
    
    def save(self, queue: List[Path], current_index: int, settings: Dict):
        import json
        state = {
            'queue': [str(p) for p in queue],
            'current_index': current_index,
            'settings': settings,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def load(self) -> Optional[Dict]:
        import json
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            state['queue'] = [Path(p) for p in state['queue']]
            return state
        except Exception:
            return None
    
    def clear(self):
        if self.state_path.exists():
            self.state_path.unlink()