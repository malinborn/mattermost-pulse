"""
Модуль для работы с AI для улучшения текстов
"""
import os
from typing import Optional
from openai import OpenAI


def improve_message_text(text: str, api_key: Optional[str] = None) -> str:
    """
    Улучшает текст сообщения с помощью OpenAI API
    
    Args:
        text: Исходный текст для улучшения
        api_key: API ключ OpenAI (если не указан, берется из переменной окружения)
    
    Returns:
        Улучшенный текст
    
    Raises:
        Exception: Если произошла ошибка при обращении к API
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API ключ не найден. Укажите его в переменной окружения OPENAI_API_KEY")
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""Ты - профессиональный редактор текстов. Улучши следующее сообщение, сделав его более четким, профессиональным и понятным. 
Сохрани основной смысл и тон сообщения. Исправь грамматические ошибки, улучши структуру и формулировки.
Не добавляй лишней информации, которой не было в оригинале.

Исходное сообщение:
{text}

Улучшенное сообщение:"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты - профессиональный редактор текстов, который помогает улучшать деловые сообщения."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    improved_text = response.choices[0].message.content.strip()
    return improved_text
