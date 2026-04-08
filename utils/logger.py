import logging
from pathlib import Path
from datetime import datetime

def setup_logger(log_dir: Path = None):
    if log_dir is None:
        log_dir = Path.home() / ".tts_studio" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tts_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str):
    return logging.getLogger(name)