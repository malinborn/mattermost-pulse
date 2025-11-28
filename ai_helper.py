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


def generate_channel_summary(posts: list, start_date: str, end_date: str, api_key: Optional[str] = None, users_cache: dict = None) -> str:
    """
    Генерирует саммари канала на основе постов за период
    
    Args:
        posts: Список постов из канала
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        api_key: API ключ OpenAI (если не указан, берется из переменной окружения)
    
    Returns:
        Саммари в виде отформатированного текста
    
    Raises:
        Exception: Если произошла ошибка при обращении к API
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API ключ не найден. Укажите его в переменной окружения OPENAI_API_KEY")
    
    if not posts:
        return "Нет постов для анализа"
    
    # Если кеш пользователей не передан, создаем пустой
    if users_cache is None:
        users_cache = {}
    
    # Функция для получения имени автора
    def get_author_name(user_id: str) -> str:
        if user_id in users_cache:
            user_info = users_cache[user_id]
            return user_info.get('username') or user_info.get('email') or f"User-{user_id[:8]}"
        return f"User-{user_id[:8]}"  # Первые 8 символов ID
    
    # Подготавливаем данные для анализа - группируем по тредам
    threads = {}  # {root_id: {'root': post, 'replies': [posts]}}
    root_posts = []  # Посты без parent (рутовые)
    
    # Группируем посты
    for post in posts[:100]:  # Берем первые 100 постов
        root_id = post.get('root_id', '')
        
        if not root_id:  # Это root пост
            post_id = post.get('id', '')
            if post_id not in threads:
                threads[post_id] = {'root': post, 'replies': []}
            root_posts.append(post_id)
        else:  # Это reply
            if root_id not in threads:
                threads[root_id] = {'root': None, 'replies': []}
            threads[root_id]['replies'].append(post)
    
    # Формируем структурированный текст
    structured_messages = []
    
    for root_id in root_posts[:50]:  # Берем первые 50 тредов
        thread = threads.get(root_id)
        if not thread:
            continue
        
        root = thread['root']
        replies = thread['replies']
        
        # Root пост
        root_message = root.get('message', '').strip()
        if root_message:
            create_at = root.get('create_at', 0)
            user_id = root.get('user_id', '')
            author = get_author_name(user_id)
            
            date_str = ""
            if create_at:
                from datetime import datetime
                date_str = datetime.fromtimestamp(create_at / 1000).strftime('%Y-%m-%d %H:%M')
            
            thread_text = f"[ТРЕД {date_str}] @{author}\n{root_message}"
            
            # Добавляем реплаи
            if replies:
                thread_text += "\n  Ответы:"
                for reply in replies[:10]:  # Берем до 10 реплаев на тред
                    reply_message = reply.get('message', '').strip()
                    reply_user_id = reply.get('user_id', '')
                    reply_author = get_author_name(reply_user_id)
                    if reply_message:
                        thread_text += f"\n  → @{reply_author}: {reply_message}"
            
            structured_messages.append(thread_text)
    
    combined_text = "\n\n---\n\n".join(structured_messages)
    
    # Если текст слишком большой, обрезаем
    max_chars = 15000  # Увеличил лимит для структурированных данных
    if len(combined_text) > max_chars:
        combined_text = combined_text[:max_chars] + "\n\n...(текст обрезан)"
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""Ты - аналитик корпоративных коммуникаций. Проанализируй обсуждения из рабочего канала за период с {start_date} по {end_date}.

Данные представлены в виде ТРЕДОВ, где каждый тред это:
- Заголовок: [ТРЕД дата] @автор
- Основное сообщение (root пост) от автора
- Ответы (реплаи) с отступом "→ @автор: текст"

Создай краткое саммари в формате Markdown со следующими разделами:

## 📋 Краткое резюме
(2-3 предложения о главном)

## ❓ Открытые вопросы и проблемы
- Треды без ответов или с незавершенными обсуждениями
- Что требует срочного внимания
- Что требует дополнительного обсуждения
Важно указать конкретные примеры из тредов

## 📅 Важные даты и дедлайны
(если упоминались в обсуждениях)

Обсуждения:
{combined_text}

Саммари:"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты - профессиональный аналитик, который помогает создавать структурированные саммари обсуждений."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=3000
    )
    
    summary = response.choices[0].message.content.strip()
    return summary
