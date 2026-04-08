#!/usr/bin/env python3
"""Тестовый скрипт для диагностики RUAccent и Silero"""

import sys
import traceback

def test_ruaccent():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ RUACCENT")
    print("=" * 60)
    
    try:
        from ruaccent import RUAccent
        
        print("\n1. Загрузка модели 'turbo2' (стандартная)...")
        accentizer = RUAccent()
        accentizer.load(omograph_model_size='turbo2', use_dictionary=True, device='CPU')
        print("   ✅ Модель 'turbo2' загружена")
        
        # Тест расстановки ударений
        test_texts = [
            "Замок на двери висит",
            "Я купил замок",
            "Мама мыла раму",
            "Привет мир!"
        ]
        
        print("\n2. Тест расстановки ударений:")
        for test in test_texts:
            result = accentizer.process_all(test)
            print(f"   📝 Вход: {test}")
            print(f"   🎯 Выход: {result}")
        
        print("\n3. Загрузка модели 'big_poetry'...")
        accentizer_big = RUAccent()
        accentizer_big.load(omograph_model_size='big_poetry', use_dictionary=True, device='CPU')
        print("   ✅ Модель 'big_poetry' загружена")
        
        result = accentizer_big.process_all("Замок на двери")
        print(f"   📝 Тест: 'Замок на двери' -> '{result}'")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        print(traceback.format_exc())
        return False

def test_silero():
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ SILERO TTS")
    print("=" * 60)
    
    try:
        # Проверяем импорт omegaconf
        try:
            import omegaconf
            print(f"✅ omegaconf версия: {omegaconf.__version__}")
        except ImportError as e:
            print(f"❌ omegaconf не импортируется: {e}")
            return False
        
        # Проверяем импорт hydra
        try:
            import hydra
            print(f"✅ hydra импортирован")
        except ImportError as e:
            print(f"❌ hydra не импортируется: {e}")
            return False
        
        import torch
        print(f"✅ PyTorch версия: {torch.__version__}")
        
        print("\nЗагрузка Silero модели...")
        model, _ = torch.hub.load(
            'snakers4/silero-models',
            'silero_tts',
            language='ru',
            speaker='v4_ru',
            trust_repo=True
        )
        print("✅ Silero модель загружена")
        
        print("\nТест синтеза...")
        audio = model.apply_tts(
            text="Привет мир",
            speaker="xenia",
            sample_rate=48000
        )
        print(f"✅ Аудио синтезировано, форма: {audio.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("\n" + "🔧 ДИАГНОСТИКА TTS СИСТЕМЫ 🔧".center(60))
    
    ruaccent_ok = test_ruaccent()
    silero_ok = test_silero()
    
    print("\n" + "=" * 60)
    print("ИТОГ:")
    print(f"  RUAccent: {'✅ РАБОТАЕТ' if ruaccent_ok else '❌ НЕ РАБОТАЕТ'}")
    print(f"  Silero:   {'✅ РАБОТАЕТ' if silero_ok else '❌ НЕ РАБОТАЕТ'}")
    print("=" * 60)