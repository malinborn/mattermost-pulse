"""
Модуль для работы с Mattermost API.
"""

import re
from typing import Optional

import requests


def parse_post_id(post_input: str) -> str:
    """Извлекает post ID из URL или возвращает как есть, если это уже ID."""
    # Паттерн для URL вида: https://server.com/team/pl/POST_ID
    url_pattern = r'/pl/([a-z0-9]+)'
    match = re.search(url_pattern, post_input)
    return match.group(1) if match else post_input.strip()


def get_reactions(server_url: str, token: str, post_id: str) -> Optional[list]:
    """Получает реакции для указанного поста."""
    api_url = f"{server_url.rstrip('/')}/api/v4/posts/{post_id}/reactions"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("Невалидный токен доступа")
        elif response.status_code == 404:
            raise ValueError("Пост не найден или недоступен")
        else:
            raise ValueError(f"Ошибка API: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Ошибка подключения: {str(e)}")


def get_user_info(server_url: str, token: str, user_id: str) -> dict:
    """Получает информацию о пользователе по user_id."""
    api_url = f"{server_url.rstrip('/')}/api/v4/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_thread_posts(server_url: str, token: str, post_id: str) -> Optional[dict]:
    """
    Получает все посты в треде (root пост + все replies).
    
    Returns:
        dict: Словарь с ключом 'order' (список post IDs) и 'posts' (словарь постов)
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/posts/{post_id}/thread"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("Невалидный токен доступа")
        elif response.status_code == 404:
            raise ValueError("Пост не найден или недоступен")
        else:
            raise ValueError(f"Ошибка API: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Ошибка подключения: {str(e)}")


def get_thread_reactions(server_url: str, token: str, post_id: str, include_replies: bool = True) -> list:
    """
    Собирает реакции со всех постов в треде.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        post_id: ID root поста
        include_replies: Если True, включает реакции из replies, иначе только из root поста
        
    Returns:
        list: Объединенный список всех реакций из треда
    """
    all_reactions = []
    
    # Получаем тред
    thread_data = get_thread_posts(server_url, token, post_id)
    
    if not thread_data:
        return all_reactions
    
    posts = thread_data.get('posts', {})
    order = thread_data.get('order', [])
    
    # Если не нужны replies, обрабатываем только root пост
    if not include_replies:
        reactions = get_reactions(server_url, token, post_id)
        return reactions if reactions else []
    
    # Собираем реакции со всех постов в треде
    for post_id_in_thread in order:
        reactions = get_reactions(server_url, token, post_id_in_thread)
        if reactions:
            all_reactions.extend(reactions)
    
    return all_reactions


def get_thread_reactions_separated(server_url: str, token: str, post_id: str) -> dict:
    """
    Собирает реакции из треда раздельно: root пост и replies.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        post_id: ID root поста
        
    Returns:
        dict: {'root': [...], 'replies': [...]}
    """
    result = {
        'root': [],
        'replies': []
    }
    
    # Получаем тред
    thread_data = get_thread_posts(server_url, token, post_id)
    
    if not thread_data:
        return result
    
    order = thread_data.get('order', [])
    
    # Собираем реакции раздельно
    for idx, post_id_in_thread in enumerate(order):
        reactions = get_reactions(server_url, token, post_id_in_thread)
        if reactions:
            # Первый пост в order это root пост
            if idx == 0:
                result['root'].extend(reactions)
            else:
                result['replies'].extend(reactions)
    
    return result


def get_thread_posts_with_reactions(server_url: str, token: str, post_id: str) -> dict:
    """
    Получает детальную информацию о постах в треде с реакциями.
    Для каждого поста возвращает: автора, текст сообщения и реакции.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        post_id: ID root поста
        
    Returns:
        dict: {
            'root': {
                'post_id': str,
                'author': str,
                'message': str,
                'reactions': dict  # emoji_name -> [users]
            },
            'replies': [
                {
                    'post_id': str,
                    'author': str,
                    'message': str,
                    'reactions': dict
                },
                ...
            ]
        }
    """
    result = {
        'root': None,
        'replies': []
    }
    
    # Получаем тред
    thread_data = get_thread_posts(server_url, token, post_id)
    
    if not thread_data:
        return result
    
    posts = thread_data.get('posts', {})
    order = thread_data.get('order', [])
    
    # Обрабатываем каждый пост
    for idx, post_id_in_thread in enumerate(order):
        post_data = posts.get(post_id_in_thread, {})
        
        # Получаем информацию об авторе
        user_id = post_data.get('user_id', '')
        user_info = get_user_info(server_url, token, user_id)
        author = user_info.get('username') or user_info.get('email') or user_id
        
        # Получаем текст сообщения
        message = post_data.get('message', '')
        
        # Получаем и обрабатываем реакции
        reactions_raw = get_reactions(server_url, token, post_id_in_thread)
        reactions_processed = {}
        
        if reactions_raw:
            reactions_processed = process_reactions(server_url, token, reactions_raw)
        
        post_info = {
            'post_id': post_id_in_thread,
            'author': author,
            'message': message,
            'reactions': reactions_processed
        }
        
        # Первый пост в order это root пост
        if idx == 0:
            result['root'] = post_info
        else:
            result['replies'].append(post_info)
    
    return result


def get_unique_emojis(reactions: list) -> list:
    """Возвращает список уникальных эмодзи из реакций."""
    emojis = set()
    for reaction in reactions:
        emoji_name = reaction.get('emoji_name')
        if emoji_name:
            emojis.add(emoji_name)
    return sorted(list(emojis))


def process_reactions(server_url: str, token: str, reactions: list, emoji_filter: Optional[list] = None) -> dict:
    """
    Обрабатывает реакции и маппит user_id на email/username.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        reactions: Список реакций
        emoji_filter: Опциональный список эмодзи для фильтрации (если None - обрабатываются все)
    """
    # Группируем реакции по emoji_name
    emoji_users = {}
    
    for reaction in reactions:
        emoji_name = reaction.get('emoji_name', 'unknown')
        user_id = reaction.get('user_id')
        
        if not user_id:
            continue
        
        # Фильтруем по выбранным эмодзи, если фильтр задан
        if emoji_filter is not None and emoji_name not in emoji_filter:
            continue
            
        # Получаем информацию о пользователе
        user_info = get_user_info(server_url, token, user_id)
        
        # Приоритет: email, затем username
        user_identifier = user_info.get('email') or user_info.get('username') or user_id
        
        if emoji_name not in emoji_users:
            emoji_users[emoji_name] = set()
        
        emoji_users[emoji_name].add(user_identifier)
    
    # Конвертируем sets в отсортированные списки
    return {emoji: sorted(list(users)) for emoji, users in emoji_users.items()}
