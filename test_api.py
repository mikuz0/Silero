#!/usr/bin/env python3
"""Тестирование API Silero и RUAccent"""

import sys
import os
import time
from pathlib import Path

def test_environment():
    """Проверка окружения"""
    print("=" * 60)
    print("1. ПРОВЕРКА ОКРУЖЕНИЯ")
    print("=" * 60)
    
    print(f"Python: {sys.version}")
    print(f"Рабочая директория: {Path.cwd()}")
    
    # Проверка FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        version_line = result.stdout.split('\n')[0]
        print(f"FFmpeg: {version_line[:80]}")
    except:
        print("FFmpeg: НЕ НАЙДЕН")
    
    print()

def test_ruaccent():
    """Тестирование RUAccent"""
    print("=" * 60)
    print("2. ТЕСТИРОВАНИЕ RUACCENT")
    print("=" * 60)
    
    test_text = "О вере в Господа нашего Иисуса Христа. Прежде всего, братия, мы должны веровать в Господа нашего Иисуса Христа."
    
    print(f"Исходный текст: {test_text[:100]}...")
    print(f"Длина текста: {len(test_text)} символов")
    
    try:
        from ruaccent import RUAccent
        print("✅ RUAccent импортирован")
        
        # Тест turbo2
        print("\n--- Тест модели turbo2 ---")
        accentizer = RUAccent()
        accentizer.load(omograph_model_size='turbo2', use_dictionary=True, device='CPU')
        print("✅ Модель turbo2 загружена")
        
        start = time.time()
        result = accentizer.process_all(test_text)
        elapsed = time.time() - start
        print(f"✅ Обработано за {elapsed:.2f} сек")
        print(f"Результат: {result[:200]}...")
        
        # Тест big_poetry (если хватает памяти)
        print("\n--- Тест модели big_poetry ---")
        try:
            accentizer2 = RUAccent()
            accentizer2.load(omograph_model_size='big_poetry', use_dictionary=True, device='CPU')
            print("✅ Модель big_poetry загружена")
            
            start = time.time()
            result2 = accentizer2.process_all(test_text)
            elapsed = time.time() - start
            print(f"✅ Обработано за {elapsed:.2f} сек")
            print(f"Результат: {result2[:200]}...")
        except Exception as e:
            print(f"❌ Ошибка big_poetry: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка RUAccent: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def test_silero():
    """Тестирование Silero"""
    print("=" * 60)
    print("3. ТЕСТИРОВАНИЕ SILERO")
    print("=" * 60)
    
    test_text = "Привет мир. Это тест синтеза речи."
    
    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
        
        print("\nЗагрузка модели Silero...")
        model, _ = torch.hub.load(
            'snakers4/silero-models',
            'silero_tts',
            language='ru',
            speaker='v4_ru',
            trust_repo=True
        )
        print("✅ Модель загружена")
        
        # Тест с разными голосами
        voices = ['xenia', 'aidar', 'baya', 'kseniya', 'eugene']
        
        for voice in voices:
            print(f"\n--- Тест голоса: {voice} ---")
            try:
                start = time.time()
                audio = model.apply_tts(
                    text=test_text,
                    speaker=voice,
                    sample_rate=48000
                )
                elapsed = time.time() - start
                print(f"✅ Синтезировано за {elapsed:.2f} сек")
                print(f"   Форма аудио: {audio.shape}")
                print(f"   Длительность: {audio.shape[0] / 48000:.2f} сек")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        
        # Тест с длинным текстом
        print("\n--- Тест с длинным текстом ---")
        long_text = "Это очень длинный текст для проверки стабильности синтеза. " * 20
        print(f"Длина текста: {len(long_text)} символов")
        
        try:
            start = time.time()
            audio = model.apply_tts(
                text=long_text,
                speaker='xenia',
                sample_rate=48000
            )
            elapsed = time.time() - start
            print(f"✅ Синтезировано за {elapsed:.2f} сек")
            print(f"   Форма аудио: {audio.shape}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка Silero: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def test_ruaccent_chunking():
    """Тестирование разбивки текста на чанки"""
    print("=" * 60)
    print("4. ТЕСТИРОВАНИЕ РАЗБИВКИ НА ЧАНКИ")
    print("=" * 60)
    
    # Полный текст из вашего файла
    full_text = """О вере в Господа нашего Иисуса Христа. Прежде всего, братия, мы должны веровать в Господа нашего Иисуса Христа, должны почитать Его, повиноваться Ему и исполнять волю Его во всякое время и мгновение; не должны веровать ни в какого другого бога, кроме Него, поскольку Он есть Бог Великий и Господь господствующих. Должны благословлять Его и не уподоблять никакой твари, будет ли она на небе вверху или на земле внизу, поскольку все через Него сотворено, а Сам Он существует прежде всего, будет существовать вечно и никогда не будет иметь конца. Потому мы должны веровать в Него и почитать Его, чтобы вместе с Ним и быть, и царствовать вечно, и наслаждаться Его благами, поскольку Он есть Царь царей и все царства от Него зависят. Итак, мы должны веровать в Него всем сердцем и исполнять Его заповеди, потому что вера без дел мертва, дабы Он помиловал нас в Царстве Своем, когда каждый из нас окончит странствование в мире сем и скажет: веровах, темже возглаголах."""
    
    print(f"Полный текст: {len(full_text)} символов")
    
    def split_text_into_chunks(text, max_chunk_size):
        sentences = __import__('re').split(r'([.!?;:]+)', text)
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
    
    for chunk_size in [100, 120, 150, 200, 300]:
        chunks = split_text_into_chunks(full_text, chunk_size)
        print(f"\nРазмер чанка: {chunk_size} символов")
        print(f"  Количество чанков: {len(chunks)}")
        total_chars = sum(len(c) for c in chunks)
        print(f"  Всего символов: {total_chars} (должно быть {len(full_text)})")
        if total_chars != len(full_text):
            print(f"  ⚠️ ПОТЕРЯНО {len(full_text) - total_chars} символов")
        for i, chunk in enumerate(chunks):
            print(f"  Чанк {i+1}: {len(chunk)} символов -> {chunk[:50]}...")

def test_ffmpeg_conversion():
    """Тестирование конвертации в MP3"""
    print("\n" + "=" * 60)
    print("5. ТЕСТИРОВАНИЕ FFMPEG")
    print("=" * 60)
    
    import numpy as np
    import scipy.io.wavfile as wavfile
    import subprocess
    from pathlib import Path
    
    # Создаём тестовый WAV (тишина 1 секунда)
    test_wav = Path("/tmp/test_audio.wav")
    sample_rate = 48000
    duration = 1
    audio = np.zeros(duration * sample_rate, dtype=np.int16)
    wavfile.write(str(test_wav), sample_rate, audio)
    print(f"Тестовый WAV создан: {test_wav}, размер: {test_wav.stat().st_size} байт")
    
    # Конвертация с разными битрейтами
    for bitrate in ['128k', '192k', '320k']:
        test_mp3 = Path(f"/tmp/test_{bitrate}.mp3")
        cmd = [
            'ffmpeg', '-y', '-i', str(test_wav),
            '-codec:a', 'libmp3lame',
            '-b:a', bitrate,
            '-ar', str(sample_rate),
            '-ac', '2',
            str(test_mp3)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and test_mp3.exists():
            size_kb = test_mp3.stat().st_size / 1024
            print(f"✅ {bitrate}: {size_kb:.1f} KB")
            test_mp3.unlink()
        else:
            print(f"❌ {bitrate}: ошибка конвертации")
    
    test_wav.unlink()
    print("Тестовые файлы удалены")

if __name__ == "__main__":
    print("\n" + "🔧 ДИАГНОСТИКА TTS СИСТЕМЫ 🔧".center(60))
    print()
    
    test_environment()
    test_ruaccent()
    test_silero()
    test_ruaccent_chunking()
    test_ffmpeg_conversion()
    
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 60)