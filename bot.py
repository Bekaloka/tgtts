#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 IMBA Qwen3 TTS Telegram Bot 🔥
✅ Клонирование голосов за 3 секунды | ✅ Библиотека голосов | ✅ Настройки
✅ Локальный запуск | ✅ Удобное меню | ✅ Стабильная работа
✅ 10 языков | ✅ Сохранение голосов | ✅ Полная настройка
"""

import os
import json
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
import re

import telegram
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile, Voice, Audio, Document
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG_FILE = "bot_config.json"
VOICE_LIBRARY_DIR = "voice_library"
TEMP_DIR = "temp_audio"
DEFAULT_VOICE_NAME = "default"

# Структура конфигурации
DEFAULT_CONFIG = {
    "bot_token": "YOUR_BOT_TOKEN_HERE",    "admin_users": [],
    "default_voice": DEFAULT_VOICE_NAME,
    "voices": {
        DEFAULT_VOICE_NAME: {
            "model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "settings": {
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0,
                "emotion": "neutral",
                "language": "ru"
            },
            "cloned": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Голос по умолчанию"
        }
    },
    "max_voice_duration": 30,
    "supported_languages": ["ru", "en", "zh", "ja", "ko", "de", "fr", "es", "it", "pt"],
    "max_text_length": 1000,
    "audio_format": "wav",
    "sample_rate": 24000
}

# ==================== КЛАСС УПРАВЛЕНИЯ QWEN3 TTS ====================
class Qwen3TTSManager:
    """Управление Qwen3 TTS моделью и голосами"""
    
    def __init__(self):
        self.config = self.load_config()
        self.ensure_directories()
        self.tts_model = None
        self.voice_models = {}
        self.init_tts()
    
    def load_config(self) -> Dict:
        """Загрузка конфигурации"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Сохранение конфигурации"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        logger.info("✅ Конфигурация сохранена")
    
    def ensure_directories(self):
        """Создание необходимых директорий"""        os.makedirs(VOICE_LIBRARY_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        logger.info("✅ Директории созданы")
    
    def init_tts(self):
        """Инициализация TTS модели"""
        try:
            from modelscope import AutoModel, AutoTokenizer, snapshot_download
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks
            
            model_name = self.config['voices'][self.config['default_voice']]['model']
            
            logger.info(f"🔄 Загрузка модели Qwen3 TTS: {model_name}")
            self.tts_pipeline = pipeline(
                task=Tasks.text_to_speech,
                model=model_name
            )
            
            logger.info(f"✅ Qwen3 TTS модель загружена: {model_name}")
            return True
            
        except ImportError as e:
            logger.error(f"❌ Qwen3 TTS не установлен: {e}")
            logger.error("Установите: pip install modelscope torch torchaudio")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели: {e}")
            return False
    
    def get_voice_list(self) -> List[str]:
        """Получить список доступных голосов"""
        return list(self.config['voices'].keys())
    
    def get_voice_info(self, voice_name: str) -> Optional[Dict]:
        """Получить информацию о голосе"""
        return self.config['voices'].get(voice_name)
    
    def create_voice(self, voice_name: str, model: str = None, settings: Dict = None, description: str = "") -> tuple:
        """Создать новый голос"""
        if voice_name in self.config['voices']:
            return False, "Голос с таким названием уже существует"
        
        self.config['voices'][voice_name] = {
            "model": model or self.config['voices'][DEFAULT_VOICE_NAME]['model'],
            "settings": settings or self.config['voices'][DEFAULT_VOICE_NAME]['settings'].copy(),
,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": description or f"Пользовательский голос: {voice_name}"
        }        self.save_config()
        return True, f"Голос '{voice_name}' создан успешно"
    
    def clone_voice(self, voice_name: str, audio_path: str, reference_text: str = "", description: str = "") -> tuple:
        """Клонирование голоса из аудио файла"""
        try:
            if voice_name in self.config['voices'] and voice_name != DEFAULT_VOICE_NAME:
                return False, "Голос с таким названием уже существует"
            
            voice_dir = os.path.join(VOICE_LIBRARY_DIR, voice_name)
            os.makedirs(voice_dir, exist_ok=True)
            
            cloned_audio_path = os.path.join(voice_dir, "reference_audio.wav")
            shutil.copy2(audio_path, cloned_audio_path)
            
            self.config['voices'][voice_name] = {
                "model": self.config['voices'][DEFAULT_VOICE_NAME]['model'],
                "settings": self.config['voices'][DEFAULT_VOICE_NAME]['settings'].copy(),
                "cloned": True,
                "cloned_from": cloned_audio_path,
                "reference_text": reference_text,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": description or f"Клонированный голос: {voice_name}"
            }
            self.save_config()
            
            logger.info(f"✅ Голос '{voice_name}' клонирован успешно")
            return True, f"Голос '{voice_name}' клонирован успешно!"
            
        except Exception as e:
            logger.error(f"❌ Ошибка клонирования голоса: {e}")
            return False, f"Ошибка клонирования: {str(e)}"
    
    def delete_voice(self, voice_name: str) -> tuple:
        """Удалить голос"""
        if voice_name not in self.config['voices']:
            return False, "Голос не найден"
        
        if voice_name == DEFAULT_VOICE_NAME:
            return False, "Нельзя удалить голос по умолчанию"
        
        voice_dir = os.path.join(VOICE_LIBRARY_DIR, voice_name)
        if os.path.exists(voice_dir):
            try:
                shutil.rmtree(voice_dir)
                logger.info(f"🗑️ Удалены файлы голоса: {voice_name}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить файлы: {e}")
        
        del self.config['voices'][voice_name]        if self.config['default_voice'] == voice_name:
            self.config['default_voice'] = DEFAULT_VOICE_NAME
        
        self.save_config()
        return True, f"Голос '{voice_name}' удален"
    
    def update_voice_settings(self, voice_name: str, settings: Dict) -> tuple:
        """Обновить настройки голоса"""
        if voice_name not in self.config['voices']:
            return False, "Голос не найден"
        
        self.config['voices'][voice_name]['settings'].update(settings)
        self.save_config()
        return True, "Настройки обновлены"
    
    def set_default_voice(self, voice_name: str) -> tuple:
        """Установить голос по умолчанию"""
        if voice_name not in self.config['voices']:
            return False, "Голос не найден"
        
        self.config['default_voice'] = voice_name
        self.save_config()
        return True, f"Голос '{voice_name}' установлен по умолчанию"
    
    def synthesize(self, text: str, voice_name: str = None, output_path: str = None) -> Optional[str]:
        """Синтезировать речь"""
        if not hasattr(self, 'tts_pipeline'):
            logger.error("❌ TTS пайплайн не инициализирован")
            return None
        
        voice_name = voice_name or self.config['default_voice']
        voice_info = self.get_voice_info(voice_name)
        
        if not voice_info:
            logger.warning(f"⚠️ Голос '{voice_name}' не найден, использую '{DEFAULT_VOICE_NAME}'")
            voice_name = DEFAULT_VOICE_NAME
            voice_info = self.get_voice_info(DEFAULT_VOICE_NAME)
        
        try:
            settings = voice_info['settings']
            
            tts_params = {
                'text': text,
                'speed': settings.get('speed', 1.0),
                'pitch': settings.get('pitch', 1.0),
                'volume': settings.get('volume', 1.0),
                'language': settings.get('language', 'ru')
            }
            
            if voice_info.get('cloned') and voice_info.get('cloned_from'):                tts_params['reference_audio'] = voice_info['cloned_from']
                if voice_info.get('reference_text'):
                    tts_params['reference_text'] = voice_info['reference_text']
            
            logger.info(f"🎵 Синтез речи голосом: {voice_name}")
            result = self.tts_pipeline(tts_params)
            
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(TEMP_DIR, f"tts_{timestamp}.{self.config['audio_format']}")
            
            if isinstance(result, dict) and 'output_wav' in result:
                import soundfile as sf
                sf.write(output_path, result['output_wav'], self.config['sample_rate'])
            elif hasattr(result, 'audio'):
                import soundfile as sf
                sf.write(output_path, result.audio, self.config['sample_rate'])
            else:
                with open(output_path, 'wb') as f:
                    f.write(result)
            
            logger.info(f"✅ Аудио сохранено: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка синтеза: {e}", exc_info=True)
            return None
    
    def get_voice_statistics(self) -> Dict:
        """Получить статистику по голосам"""
        total_voices = len(self.config['voices'])
        cloned_voices = sum(1 for v in self.config['voices'].values() if v.get('cloned'))
        
        return {
            'total': total_voices,
            'cloned': cloned_voices,
            'standard': total_voices - cloned_voices,
            'default': self.config['default_voice']
        }

# ==================== ГЛОБАЛЬНЫЙ МЕНЕДЖЕР ====================
tts_manager = Qwen3TTSManager()

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu() -> ReplyKeyboardMarkup:
    """Основное меню"""
    keyboard = [
        ["🎵 Синтезировать речь", "🎭 Мои голоса"],
        ["➕ Создать голос", "🎤 Клонировать голос"],
        ["⚙️ Настройки", "📚 Библиотека"],        ["❓ Помощь", "📊 Статистика"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_voices_menu(page: int = 0) -> InlineKeyboardMarkup:
    """Меню выбора голоса с пагинацией"""
    voices = tts_manager.get_voice_list()
    voices_per_page = 8
    total_pages = (len(voices) + voices_per_page - 1) // voices_per_page
    
    start_idx = page * voices_per_page
    end_idx = start_idx + voices_per_page
    page_voices = voices[start_idx:end_idx]
    
    keyboard = []
    
    for i in range(0, len(page_voices), 2):
        row = []
        row.append(InlineKeyboardButton(
            f"{'🎤' if tts_manager.config['default_voice'] == page_voices[i] else '👤'} {page_voices[i]}",
            callback_data=f"select_voice_{page_voices[i]}"
        ))
        if i + 1 < len(page_voices):
            row.append(InlineKeyboardButton(
                f"{'🎤' if tts_manager.config['default_voice'] == page_voices[i+1] else '👤'} {page_voices[i+1]}",
                callback_data=f"select_voice_{page_voices[i+1]}"
            ))
        keyboard.append(row)
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"voices_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"voices_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton("🆕 Создать новый", callback_data="create_new_voice"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_voice_settings_menu(voice_name: str) -> InlineKeyboardMarkup:
    """Меню настроек голоса"""
    voice_info = tts_manager.get_voice_info(voice_name)
    cloned = voice_info.get('cloned', False)    
    keyboard = [
        [InlineKeyboardButton("🎚️ Настроить параметры", callback_data=f"settings_{voice_name}")],
        [InlineKeyboardButton("📝 Изменить описание", callback_data=f"edit_desc_{voice_name}")],
    ]
    
    if not cloned and voice_name != DEFAULT_VOICE_NAME:
        keyboard.append([InlineKeyboardButton("🎤 Клонировать этот голос", callback_data=f"clone_this_{voice_name}")])
    
    if voice_name != DEFAULT_VOICE_NAME:
        keyboard.append([InlineKeyboardButton("🗑️ Удалить голос", callback_data=f"delete_confirm_{voice_name}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад к голосам", callback_data="back_to_voices")])
    
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(voice_name: str) -> InlineKeyboardMarkup:
    """Клавиатура настроек параметров"""
    settings = tts_manager.get_voice_info(voice_name)['settings']
    
    keyboard = [
        [InlineKeyboardButton(f"⚡ Скорость: {settings['speed']}", callback_data=f"adjust_speed_{voice_name}")],
        [InlineKeyboardButton(f"🎵 Тон: {settings['pitch']}", callback_data=f"adjust_pitch_{voice_name}")],
        [InlineKeyboardButton(f"🔊 Громкость: {settings['volume']}", callback_data=f"adjust_volume_{voice_name}")],
        [InlineKeyboardButton(f"🎭 Эмоция: {settings['emotion']}", callback_data=f"adjust_emotion_{voice_name}")],
        [InlineKeyboardButton(f"🌐 Язык: {settings['language']}", callback_data=f"adjust_language_{voice_name}")],
        [InlineKeyboardButton("✅ Сохранить", callback_data=f"save_settings_{voice_name}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"voice_menu_{voice_name}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_emotion_keyboard(voice_name: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора эмоции"""
    keyboard = [
        [InlineKeyboardButton("😐 Neutral", callback_data=f"set_emotion_{voice_name}_neutral")],
        [InlineKeyboardButton("😊 Happy", callback_data=f"set_emotion_{voice_name}_happy")],
        [InlineKeyboardButton("😢 Sad", callback_data=f"set_emotion_{voice_name}_sad")],
        [InlineKeyboardButton("😠 Angry", callback_data=f"set_emotion_{voice_name}_angry")],
        [InlineKeyboardButton("🤩 Excited", callback_data=f"set_emotion_{voice_name}_excited")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"settings_{voice_name}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(voice_name: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    supported_langs = tts_manager.config['supported_languages']
    keyboard = []
    
    lang_names = {
        'ru': '🇷🇺 Русский',        'en': '🇬🇧 English',
        'zh': '🇨🇳 中文',
        'ja': '🇯🇵 日本語',
        'ko': '🇰🇷 한국어',
        'de': '🇩🇪 Deutsch',
        'fr': '🇫🇷 Français',
        'es': '🇪🇸 Español',
        'it': '🇮🇹 Italiano',
        'pt': '🇵🇹 Português'
    }
    
    for i in range(0, len(supported_langs), 2):
        row = []
        row.append(InlineKeyboardButton(
            lang_names.get(supported_langs[i], supported_langs[i]),
            callback_data=f"set_lang_{voice_name}_{supported_langs[i]}"
        ))
        if i + 1 < len(supported_langs):
            row.append(InlineKeyboardButton(
                lang_names.get(supported_langs[i+1], supported_langs[i+1]),
                callback_data=f"set_lang_{voice_name}_{supported_langs[i+1]}"
            ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"settings_{voice_name}")])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    stats = tts_manager.get_voice_statistics()
    
    welcome_text = f"""
🤖 **Добро пожаловать в IMBA Qwen3 TTS Bot!** 🎉

👋 Привет, {user.first_name}!

🔥 **Возможности бота:**
🎵 Синтез речи на **10 языках**
🎭 **Клонирование голосов** всего за 3 секунды [[3]]
📚 Библиотека голосов ({stats['total']} голосов)
⚙️ Гибкие настройки параметров
🎤 Создание своих голосов
💾 Сохранение всех голосов

**Используйте меню ниже для начала!**

📖 **Быстрая инструкция:**1️⃣ Выберите "🎵 Синтезировать речь"
2️⃣ Отправьте текст для озвучки
3️⃣ Выберите голос из библиотеки
4️⃣ Получите аудио файл!

💬 **Поддерживаемые языки:**
Русский, Английский, Китайский, Японский, Корейский, Немецкий, Французский, Испанский, Итальянский, Португальский

🚀 **Статистика:**
- Всего голосов: {stats['total']}
- Клонированных: {stats['cloned']}
- Стандартных: {stats['standard']}
- Активный: {stats['default']}
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📚 **ПОЛНАЯ ИНСТРУКЦИЯ**

**🎵 Синтезировать речь**
- Отправьте текст для озвучки (до 1000 символов)
- Выберите голос из списка
- Получите аудио файл в формате WAV

**🎭 Мои голоса**
- Просмотр всех доступных голосов
- Выбор активного голоса
- Настройка параметров каждого голоса

**➕ Создать голос**
- Создайте новый голос на базе модели
- Настройте параметры под себя
- Добавьте описание

**🎤 Клонировать голос**
- Отправьте аудио файл (до 30 секунд)
- Укажите текст для обучения (опционально)
- Создайте клон вашего голоса всего за 3 секунды! [[3]]

**⚙️ Настройки**
- Скорость речи (0.5 - 2.0)
- Тон голоса (0.5 - 2.0)
- Громкость (0.1 - 2.0)- Эмоции: neutral, happy, sad, angry, excited
- Язык: 10 поддерживаемых языков [[4]]

**📚 Библиотека**
- Все созданные и клонированные голоса
- Быстрый доступ к настройкам
- Управление голосами
- Статистика использования

**📊 Статистика**
- Количество голосов
- Информация о каждом голосе
- История использования

**Техническая поддержка:**
Если возникли проблемы, проверьте логи или напишите администратору.
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика"""
    stats = tts_manager.get_voice_statistics()
    voices = tts_manager.get_voice_list()
    
    stats_text = f"""
📊 **СТАТИСТИКА БОТА**

**Голоса:**
- Всего: {stats['total']}
- Клонированных: {stats['cloned']}
- Стандартных: {stats['standard']}
- Активный: `{stats['default']}`

**Доступные голоса:**
"""
    
    for voice_name in voices:
        voice_info = tts_manager.get_voice_info(voice_name)
        emoji = "🎤" if stats['default'] == voice_name else "👤"
        cloned = " (клон)" if voice_info.get('cloned') else ""
        
        stats_text += f"\n{emoji} **{voice_name}**{cloned}"
        stats_text += f"\n   Язык: `{voice_info['settings']['language']}`"
        stats_text += f"\n   Создан: {voice_info['created_at']}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def synthesize_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для синтеза"""    text = update.message.text.strip()
    
    if len(text) > tts_manager.config['max_text_length']:
        await update.message.reply_text(
            f"❌ Текст слишком длинный! Максимум {tts_manager.config['max_text_length']} символов."
        )
        return
    
    if len(text) < 2:
        await update.message.reply_text("❌ Текст слишком короткий! Минимум 2 символа.")
        return
    
    context.user_data['pending_text'] = text
    
    await update.message.reply_text(
        f"🎤 Выберите голос для синтеза:\n(Текст: {len(text)} символов)",
        reply_markup=get_voices_menu()
    )

async def voices_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список голосов"""
    await update.message.reply_text(
        "🎭 Доступные голоса:",
        reply_markup=get_voices_menu()
    )

async def create_voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание нового голоса - шаг 1: имя"""
    await update.message.reply_text(
        "➕ Введите название нового голоса:\n"
        "(только буквы, цифры и подчеркивания, минимум 3 символа)",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data['awaiting_voice_name'] = True

async def clone_voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Клонирование голоса - шаг 1: запрос аудио"""
    await update.message.reply_text(
        f"🎤 Отправьте аудио файл для клонирования голоса [[7]]\n\n"
        f"⚠️ **Требования:**\n"
        f"- Формат: голосовое сообщение, аудио файл или документ\n"
        f"- Длительность: до {tts_manager.config['max_voice_duration']} секунд (оптимально 3-10 сек) [[3]]\n"
        f"- Качество: четкая речь без шумов"
    )
    context.user_data['awaiting_voice_audio'] = True

async def settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню настроек"""
    stats = tts_manager.get_voice_statistics()
        settings_text = f"""
⚙️ **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**

**Текущие параметры:**
- Активный голос: `{tts_manager.config['default_voice']}`
- Макс. длительность для клонирования: {tts_manager.config['max_voice_duration']} сек
- Макс. длина текста: {tts_manager.config['max_text_length']} символов
- Формат аудио: {tts_manager.config['audio_format'].upper()}
- Частота дискретизации: {tts_manager.config['sample_rate']} Hz

**Доступные языки:**
{', '.join(tts_manager.config['supported_languages'])}

**Что хотите изменить?**
"""
    
    keyboard = [
        [InlineKeyboardButton("🎤 Активный голос", callback_data="change_default_voice")],
        [InlineKeyboardButton("⏱️ Макс. длительность", callback_data="change_max_duration")],
        [InlineKeyboardButton("📏 Макс. длина текста", callback_data="change_max_text")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    
    await update.message.reply_text(
        settings_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def voice_library_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Библиотека голосов"""
    voices = tts_manager.get_voice_list()
    stats = tts_manager.get_voice_statistics()
    
    library_text = f"📚 **БИБЛИОТЕКА ГОЛОСОВ**\n\n"
    library_text += f"**Статистика:**\n"
    library_text += f"Всего: {stats['total']} | Клонированных: {stats['cloned']} | Стандартных: {stats['standard']}\n\n"
    
    for voice_name in voices:
        voice_info = tts_manager.get_voice_info(voice_name)
        emoji = "🎤" if tts_manager.config['default_voice'] == voice_name else "👤"
        cloned = " (клонированный)" if voice_info.get('cloned') else ""
        
        library_text += f"{emoji} **{voice_name}**{cloned}\n"
        library_text += f"   Модель: `{voice_info['model']}`\n"
        library_text += f"   Язык: `{voice_info['settings']['language']}`\n"
        library_text += f"   Описание: {voice_info.get('description', 'Без описания')}\n"
        library_text += f"   Создан: {voice_info['created_at']}\n\n"
    
    await update.message.reply_text(        library_text,
        parse_mode='Markdown',
        reply_markup=get_voices_menu()
    )

# ==================== ОБРАБОТЧИКИ КОЛБЭКОВ ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("voices_page_"):
        page = int(data.replace("voices_page_", ""))
        await query.edit_message_text(
            "🎭 Доступные голоса:",
            reply_markup=get_voices_menu(page)
        )
        return
    
    if data.startswith("select_voice_"):
        voice_name = data.replace("select_voice_", "")
        success, message = tts_manager.set_default_voice(voice_name)
        
        if success:
            await query.edit_message_text(
                f"✅ Голос '{voice_name}' выбран как активный!\nВыберите действие:",
                reply_markup=get_voice_settings_menu(voice_name)
            )
        else:
            await query.answer(message, show_alert=True)
        return
    
    if data.startswith("voice_menu_"):
        voice_name = data.replace("voice_menu_", "")
        await query.edit_message_text(
            f"🎭 **Настройки голоса: {voice_name}**",
            reply_markup=get_voice_settings_menu(voice_name),
            parse_mode='Markdown'
        )
        return
    
    if data.startswith("settings_"):
        voice_name = data.replace("settings_", "")
        await query.edit_message_text(
            f"🎚️ **Настройте параметры голоса: {voice_name}**",
            reply_markup=get_settings_keyboard(voice_name),
            parse_mode='Markdown'
        )        return
    
    if data.startswith("adjust_"):
        parts = data.split('_')
        param_type = parts[1]
        voice_name = '_'.join(parts[2:])
        
        param_names = {
            'speed': 'скорость',
            'pitch': 'тон',
            'volume': 'громкость',
            'emotion': 'эмоцию',
            'language': 'язык'
        }
        
        context.user_data['adjusting_param'] = {
            'type': param_type,
            'voice': voice_name
        }
        
        current_value = tts_manager.get_voice_info(voice_name)['settings'].get(param_type, 'N/A')
        
        if param_type == 'emotion':
            await query.edit_message_text(
                f"🎭 Выберите эмоцию для голоса {voice_name}:",
                reply_markup=get_emotion_keyboard(voice_name)
            )
        elif param_type == 'language':
            await query.edit_message_text(
                f"🌐 Выберите язык для голоса {voice_name}:",
                reply_markup=get_language_keyboard(voice_name)
            )
        else:
            await query.message.reply_text(
                f"Введите новое значение для {param_names[param_type]}:\n"
                f"Текущее: {current_value}\n\n"
                f"Диапазоны:\n"
                f"- Скорость: 0.5 - 2.0 (1.0 = нормально)\n"
                f"- Тон: 0.5 - 2.0 (1.0 = нормально)\n"
                f"- Громкость: 0.1 - 2.0 (1.0 = нормально)"
            )
        return
    
    if data.startswith("set_emotion_"):
        parts = data.split('_')
        voice_name = parts[2]
        emotion = parts[3]
        
        success, message = tts_manager.update_voice_settings(voice_name, {'emotion': emotion})
                if success:
            await query.answer(f"✅ Эмоция установлена: {emotion}")
            await query.edit_message_text(
                f"🎭 **Настройки голоса: {voice_name}**",
                reply_markup=get_settings_keyboard(voice_name),
                parse_mode='Markdown'
            )
        else:
            await query.answer(message, show_alert=True)
        return
    
    if data.startswith("set_lang_"):
        parts = data.split('_')
        voice_name = parts[2]
        language = parts[3]
        
        success, message = tts_manager.update_voice_settings(voice_name, {'language': language})
        
        if success:
            await query.answer(f"✅ Язык установлен: {language}")
            await query.edit_message_text(
                f"🎭 **Настройки голоса: {voice_name}**",
                reply_markup=get_settings_keyboard(voice_name),
                parse_mode='Markdown'
            )
        else:
            await query.answer(message, show_alert=True)
        return
    
    if data.startswith("save_settings_"):
        voice_name = data.replace("save_settings_", "")
        await query.answer("✅ Настройки сохранены!")
        await query.edit_message_text(
            f"✅ Настройки для голоса '{voice_name}' сохранены!",
            reply_markup=get_voice_settings_menu(voice_name)
        )
        return
    
    if data.startswith("clone_this_"):
        voice_name = data.replace("clone_this_", "")
        context.user_data['cloning_voice'] = voice_name
        
        await query.message.reply_text(
            f"🎤 Отправьте аудио файл для клонирования голоса '{voice_name}'\n\n"
            f"⚠️ Максимальная длительность: {tts_manager.config['max_voice_duration']} секунд",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if data.startswith("edit_desc_"):        voice_name = data.replace("edit_desc_", "")
        context.user_data['editing_description'] = voice_name
        
        current_desc = tts_manager.get_voice_info(voice_name).get('description', 'Без описания')
        
        await query.message.reply_text(
            f"📝 Введите новое описание для голоса '{voice_name}':\n\n"
            f"Текущее: {current_desc}"
        )
        return
    
    if data.startswith("delete_confirm_"):
        voice_name = data.replace("delete_confirm_", "")
        
        if voice_name == DEFAULT_VOICE_NAME:
            await query.answer("❌ Нельзя удалить голос по умолчанию!", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_voice_{voice_name}")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data=f"voice_menu_{voice_name}")]
        ]
        
        await query.edit_message_text(
            f"⚠️ **Вы уверены, что хотите удалить голос '{voice_name}'?**\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    if data.startswith("delete_voice_"):
        voice_name = data.replace("delete_voice_", "")
        success, message = tts_manager.delete_voice(voice_name)
        
        if success:
            await query.edit_message_text(
                f"✅ {message}",
                reply_markup=get_voices_menu()
            )
        else:
            await query.answer(message, show_alert=True)
        return
    
    if data == "create_new_voice":
        await query.message.reply_text(
            "➕ Введите название нового голоса:\n"
            "(только буквы, цифры и подчеркивания, минимум 3 символа)",
            reply_markup=ReplyKeyboardRemove()
        )        context.user_data['awaiting_voice_name'] = True
        return
    
    if data == "back_to_main":
        await query.edit_message_text(
            "🏠 Главное меню:",
            reply_markup=get_main_menu()
        )
        return
    
    if data == "back_to_voices":
        await query.edit_message_text(
            "🎭 Доступные голоса:",
            reply_markup=get_voices_menu()
        )
        return
    
    if data == "noop":
        await query.answer()
        return

# ==================== ОБРАБОТКА ТЕКСТА И АУДИО ====================
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода"""
    
    if 'adjusting_param' in context.user_data:
        param_data = context.user_data['adjusting_param']
        param_type = param_data['type']
        voice_name = param_data['voice']
        
        try:
            if param_type in ['speed', 'pitch', 'volume']:
                value = float(update.message.text)
                
                if param_type == 'speed' and (value < 0.5 or value > 2.0):
                    await update.message.reply_text("❌ Скорость должна быть от 0.5 до 2.0")
                    return
                
                if param_type == 'pitch' and (value < 0.5 or value > 2.0):
                    await update.message.reply_text("❌ Тон должен быть от 0.5 до 2.0")
                    return
                
                if param_type == 'volume' and (value < 0.1 or value > 2.0):
                    await update.message.reply_text("❌ Громкость должна быть от 0.1 до 2.0")
                    return
                
                success, message = tts_manager.update_voice_settings(voice_name, {param_type: value})
                
                if success:
                    await update.message.reply_text(                        f"✅ {param_type.capitalize()} установлена на {value}",
                        reply_markup=get_settings_keyboard(voice_name)
                    )
                else:
                    await update.message.reply_text(f"❌ {message}")
                
            elif param_type == 'emotion':
                emotion = update.message.text.lower()
                valid_emotions = ['neutral', 'happy', 'sad', 'angry', 'excited']
                
                if emotion not in valid_emotions:
                    await update.message.reply_text(
                        f"❌ Неверная эмоция! Допустимые: {', '.join(valid_emotions)}"
                    )
                    return
                
                success, message = tts_manager.update_voice_settings(voice_name, {'emotion': emotion})
                
                if success:
                    await update.message.reply_text(
                        f"✅ Эмоция установлена: {emotion}",
                        reply_markup=get_settings_keyboard(voice_name)
                    )
                else:
                    await update.message.reply_text(f"❌ {message}")
            
            del context.user_data['adjusting_param']
            
        except ValueError:
            await update.message.reply_text("❌ Введите корректное число!")
        
        return
    
    if 'editing_description' in context.user_data:
        voice_name = context.user_data['editing_description']
        description = update.message.text.strip()
        
        if len(description) > 200:
            await update.message.reply_text("❌ Описание слишком длинное! Максимум 200 символов.")
            return
        
        voice_info = tts_manager.get_voice_info(voice_name)
        voice_info['description'] = description
        tts_manager.config['voices'][voice_name] = voice_info
        tts_manager.save_config()
        
        await update.message.reply_text(
            f"✅ Описание для голоса '{voice_name}' обновлено!",
            reply_markup=get_voice_settings_menu(voice_name)
        )        
        del context.user_data['editing_description']
        return
    
    if context.user_data.get('awaiting_voice_name'):
        voice_name = update.message.text.strip()
        
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', voice_name):
            await update.message.reply_text(
                "❌ Неверный формат названия!\n"
                "Используйте только буквы, цифры и подчеркивания.\n"
                "Минимум 3 символа, максимум 30."
            )
            return
        
        if voice_name in tts_manager.get_voice_list():
            await update.message.reply_text(
                "❌ Голос с таким названием уже существует!"
            )
            return
        
        context.user_data['new_voice_name'] = voice_name
        context.user_data['awaiting_voice_name'] = False
        context.user_data['awaiting_voice_description'] = True
        
        await update.message.reply_text(
            f"📝 Введите описание для голоса '{voice_name}':\n"
            "(опционально, можно пропустить)"
        )
        return
    
    if context.user_data.get('awaiting_voice_description'):
        voice_name = context.user_data['new_voice_name']
        description = update.message.text.strip()
        
        if description.lower() in ['пропустить', 'skip', '-']:
            description = f"Пользовательский голос: {voice_name}"
        
        success, message = tts_manager.create_voice(voice_name, description=description)
        
        if success:
            await update.message.reply_text(
                f"✅ {message}!\n\n"
                f"Теперь вы можете настроить параметры этого голоса.",
                reply_markup=get_voice_settings_menu(voice_name)
            )
        else:
            await update.message.reply_text(f"❌ {message}")
        
        context.user_data['awaiting_voice_description'] = False        del context.user_data['new_voice_name']
        return
    
    if 'pending_text' in context.user_data:
        await synthesize_text_handler(update, context)
        return
    
    await update.message.reply_text(
        "💬 Хотите озвучить этот текст? Нажмите '🎵 Синтезировать речь' в меню!",
        reply_markup=get_main_menu()
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка аудио файлов для клонирования"""
    
    if context.user_data.get('awaiting_voice_audio'):
        audio_file = None
        file_type = ""
        
        if update.message.voice:
            audio_file = await update.message.voice.get_file()
            file_type = "voice"
        elif update.message.audio:
            audio_file = await update.message.audio.get_file()
            file_type = "audio"
        elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('audio/'):
            audio_file = await update.message.document.get_file()
            file_type = "document"
        
        if not audio_file:
            await update.message.reply_text("❌ Не удалось получить аудио файл!")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_path = os.path.join(TEMP_DIR, f"voice_{timestamp}.ogg")
        
        try:
            await update.message.reply_text("🔄 Загружаю аудио файл...")
            await audio_file.download_to_drive(temp_path)
            
            try:
                import librosa
                duration = librosa.get_duration(filename=temp_path)
                
                if duration > tts_manager.config['max_voice_duration']:
                    os.remove(temp_path)
                    await update.message.reply_text(
                        f"❌ Аудио слишком длинное! Максимум {tts_manager.config['max_voice_duration']} секунд.\n"
                        f"Ваше аудио: {duration:.1f} секунд"
                    )                    return
                
                if duration < 1.0:
                    os.remove(temp_path)
                    await update.message.reply_text(
                        "❌ Аудио слишком короткое! Минимум 1 секунда для качественного клонирования."
                    )
                    return
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось проверить длительность: {e}")
            
            context.user_data['voice_audio_path'] = temp_path
            context.user_data['awaiting_voice_audio'] = False
            context.user_data['awaiting_cloned_voice_name'] = True
            
            await update.message.reply_text(
                f"✅ Аудио получено! Длительность: {duration:.1f} сек\n\n"
                f"📝 Введите название для клонированного голоса:\n"
                f"(только буквы, цифры и подчеркивания, минимум 3 символа)"
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке аудио!"
            )
        
        return
    
    if context.user_data.get('awaiting_cloned_voice_name'):
        voice_name = update.message.text.strip()
        
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', voice_name):
            await update.message.reply_text(
                "❌ Неверный формат названия!\n"
                "Используйте только буквы, цифры и подчеркивания.\n"
                "Минимум 3 символа, максимум 30."
            )
            return
        
        if voice_name in tts_manager.get_voice_list():
            await update.message.reply_text(
                "❌ Голос с таким названием уже существует!"
            )
            return
        
        context.user_data['cloned_voice_name'] = voice_name        context.user_data['awaiting_cloned_voice_name'] = False
        context.user_data['awaiting_cloned_voice_description'] = True
        
        await update.message.reply_text(
            f"📝 Введите описание для клонированного голоса '{voice_name}':\n"
            "(опционально, можно пропустить)"
        )
        return
    
    if context.user_data.get('awaiting_cloned_voice_description'):
        voice_name = context.user_data['cloned_voice_name']
        description = update.message.text.strip()
        
        if description.lower() in ['пропустить', 'skip', '-']:
            description = f"Клонированный голос: {voice_name}"
        
        audio_path = context.user_data.get('voice_audio_path')
        
        if not audio_path or not os.path.exists(audio_path):
            await update.message.reply_text("❌ Ошибка: аудио файл не найден!")
            return
        
        await update.message.reply_text("🔄 Начинаю клонирование голоса...\nЭто может занять несколько секунд.")
        
        success, message = tts_manager.clone_voice(voice_name, audio_path, description=description)
        
        if success:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            await update.message.reply_text(
                f"✅ {message}\n\n"
                f"Теперь вы можете использовать этот голос для синтеза речи!",
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_main_menu()
            )
        
        context.user_data['awaiting_cloned_voice_description'] = False
        if 'cloned_voice_name' in context.user_data:
            del context.user_data['cloned_voice_name']
        if 'voice_audio_path' in context.user_data:
            del context.user_data['voice_audio_path']
        
        return
    
    if 'cloning_voice' in context.user_data:        voice_name = context.user_data['cloning_voice']
        
        audio_file = None
        if update.message.voice:
            audio_file = await update.message.voice.get_file()
        elif update.message.audio:
            audio_file = await update.message.audio.get_file()
        elif update.message.document and update.message.document.mime_type.startswith('audio/'):
            audio_file = await update.message.document.get_file()
        
        if not audio_file:
            await update.message.reply_text("❌ Не удалось получить аудио файл!")
            return
        
        temp_path = os.path.join(TEMP_DIR, f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg")
        
        try:
            await audio_file.download_to_drive(temp_path)
            
            try:
                import librosa
                duration = librosa.get_duration(filename=temp_path)
                
                if duration > tts_manager.config['max_voice_duration']:
                    os.remove(temp_path)
                    await update.message.reply_text(
                        f"❌ Аудио слишком длинное! Максимум {tts_manager.config['max_voice_duration']} секунд."
                    )
                    return
            except:
                pass
            
            await update.message.reply_text("🔄 Начинаю клонирование голоса...")
            
            success, message = tts_manager.clone_voice(voice_name, temp_path)
            
            if success:
                await update.message.reply_text(
                    f"✅ {message}",
                    reply_markup=get_main_menu()
                )
            else:
                await update.message.reply_text(
                    f"❌ {message}",
                    reply_markup=get_main_menu()
                )
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                        del context.user_data['cloning_voice']
            
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке аудио!",
                reply_markup=get_main_menu()
            )
        
        return
    
    await update.message.reply_text("⚠️ Отправьте аудио только при клонировании голоса!")

# ==================== СИНТЕЗ И ОТПРАВКА АУДИО ====================
async def synthesize_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, voice_name: str):
    """Синтезировать и отправить аудио"""
    
    text = context.user_data.get('pending_text')
    if not text:
        return
    
    await update.message.reply_text(f"🔄 Генерирую аудио голосом '{voice_name}'...")
    
    audio_path = tts_manager.synthesize(text, voice_name)
    
    if not audio_path or not os.path.exists(audio_path):
        await update.message.reply_text("❌ Ошибка генерации аудио!")
        return
    
    try:
        file_size = os.path.getsize(audio_path)
        
        if file_size > 50 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Аудио файл слишком большой для отправки через Telegram!"
            )
        else:
            with open(audio_path, 'rb') as audio_file:
                await update.message.reply_voice(
                    voice=InputFile(audio_file),
                    caption=f"🎤 Озвучено голосом: {voice_name}\nТекст: {len(text)} символов"
                )
        
        os.remove(audio_path)
        
        if 'pending_text' in context.user_data:
            del context.user_data['pending_text']
        
        logger.info(f"✅ Аудио успешно отправлено голосом {voice_name}")
            except Exception as e:
        logger.error(f"Ошибка отправки аудио: {e}")
        await update.message.reply_text("❌ Ошибка отправки аудио!")

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================
async def handle_voice_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора голоса для синтеза"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("select_voice_"):
        voice_name = data.replace("select_voice_", "")
        await synthesize_and_send(update, context, voice_name)
        await query.message.delete()

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    """Запуск бота"""
    
    if tts_manager.config['bot_token'] == "YOUR_BOT_TOKEN_HERE":
        print("=" * 60)
        print("❌ ОШИБКА: Не указан Telegram Bot Token!")
        print("=" * 60)
        print("\n📝 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:")
        print("1️⃣  Создайте бота через @BotFather в Telegram")
        print("2️⃣  Получите токен (начинается с цифр и содержит ':')")
        print("3️⃣  Откройте файл bot_config.json")
        print("4️⃣  Замените 'YOUR_BOT_TOKEN_HERE' на ваш токен")
        print("5️⃣  Сохраните файл и запустите бота снова")
        print("\n🔗 Ссылка на @BotFather: https://t.me/BotFather")
        print("=" * 60)
        return
    
    try:
        from modelscope import AutoModel, AutoTokenizer, snapshot_download
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks
        print("✅ ModelScope установлен")
    except ImportError:
        print("=" * 60)
        print("❌ ОШИБКА: ModelScope не установлен!")
        print("=" * 60)
        print("\n📦 Установка зависимостей:")
        print("pip install modelscope torch torchaudio soundfile librosa")
        print("\n💡 ModelScope - это платформа для работы с моделями Alibaba,")
        print("   включая Qwen3 TTS для синтеза речи.")
        print("=" * 60)
        return    
    application = Application.builder().token(tts_manager.config['bot_token']).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(MessageHandler(
        filters.Regex("^🎵 Синтезировать речь$"), 
        lambda u, c: u.message.reply_text("💬 Отправьте текст для озвучки (до 1000 символов):")
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^🎭 Мои голоса$"), voices_list_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^➕ Создать голос$"), create_voice_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^🎤 Клонировать голос$"), clone_voice_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^⚙️ Настройки$"), settings_menu_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^📚 Библиотека$"), voice_library_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^❓ Помощь$"), help_command
    ))
    
    application.add_handler(MessageHandler(
        filters.Regex("^📊 Статистика$"), stats_command
    ))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.AUDIO, handle_audio))
    
    print("=" * 60)
    print("✅ IMBA Qwen3 TTS Bot запущен!")
    print("=" * 60)
    print(f"🤖 Бот готов к работе")
    print(f"🎵 Доступно голосов: {len(tts_manager.get_voice_list())}")
    print(f"🌍 Поддерживаемые языки: {', '.join(tts_manager.config['supported_languages'])}")    print(f"📚 Библиотека голосов: {VOICE_LIBRARY_DIR}/")
    print(f"📁 Временные файлы: {TEMP_DIR}/")
    print("=" * 60)
    print("🚀 Бот запущен! Нажмите Ctrl+C для остановки")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
