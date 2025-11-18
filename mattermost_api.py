"""
Модуль для работы с Mattermost API.
"""

import re
from datetime import datetime
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


# ============================================================================
# Функции для работы с каналами
# ============================================================================

def parse_channel_id_from_url(url: str) -> str:
    """Извлекает ID канала из URL Mattermost или возвращает как есть, если это уже ID."""
    # Паттерн для URL вида: https://server.com/team/channels/CHANNEL_ID
    url_pattern = r'/channels/([a-z0-9]+)'
    match = re.search(url_pattern, url)
    return match.group(1) if match else url.strip()


def format_post_preview(post_text: str, max_length: int = 100) -> str:
    """Форматирует превью текста поста."""
    if not post_text:
        return ""
    
    # Убираем переносы строк и лишние пробелы
    cleaned = ' '.join(post_text.split())
    
    if len(cleaned) <= max_length:
        return cleaned
    
    return cleaned[:max_length] + "..."


def generate_post_link(server_url: str, team_name: str, post_id: str) -> str:
    """Генерирует прямую ссылку на пост."""
    return f"{server_url.rstrip('/')}/{team_name}/pl/{post_id}"


def get_channel_posts(server_url: str, token: str, channel_id: str, 
                     start_date: datetime, end_date: datetime, 
                     per_page: int = 100) -> list:
    """
    Получает посты канала за указанный период с поддержкой пагинации.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        start_date: Начальная дата
        end_date: Конечная дата
        per_page: Количество постов на страницу (макс 200)
        
    Returns:
        list: Список постов с полной информацией
    """
    all_posts = []
    page = 0
    
    # Конвертируем даты в timestamp (миллисекунды)
    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        api_url = f"{server_url.rstrip('/')}/api/v4/channels/{channel_id}/posts"
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            posts = data.get('posts', {})
            order = data.get('order', [])
            
            if not order:
                break
            
            # Фильтруем посты по датам
            for post_id in order:
                post = posts.get(post_id)
                if post:
                    post_timestamp = post.get('create_at', 0)
                    
                    # Проверяем, попадает ли пост в диапазон дат
                    if start_timestamp <= post_timestamp <= end_timestamp:
                        all_posts.append(post)
                    
                    # Если пост старше начальной даты, прекращаем пагинацию
                    if post_timestamp < start_timestamp:
                        return all_posts
            
            # Проверяем, есть ли еще посты
            if len(order) < per_page:
                break
            
            page += 1
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ValueError("Невалидный токен доступа")
            elif response.status_code == 403:
                raise ValueError("Нет прав доступа к каналу")
            elif response.status_code == 404:
                raise ValueError("Канал не найден")
            else:
                raise ValueError(f"Ошибка API: {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
            raise ValueError("Превышено время ожидания ответа от сервера")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Ошибка подключения: {str(e)}")
    
    return all_posts


def analyze_channel_emojis(posts: list) -> list:
    """
    Анализирует эмодзи на всех постах и возвращает список уникальных эмодзи.
    
    Args:
        posts: Список постов
        
    Returns:
        list: Отсортированный список уникальных эмодзи (найденные + дефолтные)
    """
    emojis = set()
    
    # Дефолтные эмодзи
    default_emojis = ['ballot_box_with_check', 'leaves', 'ice_cube', 'hammer_and_wrench']
    
    # Собираем уникальные эмодзи из реакций
    for post in posts:
        metadata = post.get('metadata', {})
        reactions = metadata.get('reactions', [])
        
        for reaction in reactions:
            emoji_name = reaction.get('emoji_name')
            if emoji_name:
                emojis.add(emoji_name)
    
    # Объединяем с дефолтными и сортируем
    all_emojis = list(emojis.union(set(default_emojis)))
    return sorted(all_emojis)


def get_posts_without_reactions(posts: list) -> list:
    """
    Фильтрует посты без реакций.
    
    Args:
        posts: Список постов
        
    Returns:
        list: Список постов без реакций
    """
    posts_without_reactions = []
    
    for post in posts:
        metadata = post.get('metadata', {})
        reactions = metadata.get('reactions', [])
        
        if not reactions:
            posts_without_reactions.append(post)
    
    return posts_without_reactions


def get_posts_by_emoji(posts: list, emoji_name: str) -> list:
    """
    Фильтрует посты с конкретной реакцией.
    
    Args:
        posts: Список постов
        emoji_name: Название эмодзи
        
    Returns:
        list: Список постов с указанной реакцией, включая количество реакций
    """
    posts_with_emoji = []
    
    for post in posts:
        metadata = post.get('metadata', {})
        reactions = metadata.get('reactions', [])
        
        # Подсчитываем количество данной реакции
        emoji_count = sum(1 for r in reactions if r.get('emoji_name') == emoji_name)
        
        if emoji_count > 0:
            post_copy = post.copy()
            post_copy['emoji_count'] = emoji_count
            posts_with_emoji.append(post_copy)
    
    return posts_with_emoji
