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

def parse_channel_url(url: str) -> dict:
    """Парсит URL канала Mattermost и извлекает team name и channel name."""
    # Паттерн для URL вида: https://server.com/team-name/channels/channel-name
    url_pattern = r'/([a-z0-9\-_]+)/channels/([a-z0-9\-_]+)'
    match = re.search(url_pattern, url, re.IGNORECASE)
    
    if match:
        return {
            'team_name': match.group(1),
            'channel_name': match.group(2),
            'is_url': True
        }
    
    return {
        'channel_name': url.strip(),
        'is_url': False
    }


def parse_channel_id_from_url(url: str) -> str:
    """Извлекает ID канала из URL Mattermost или возвращает как есть, если это уже ID."""
    # Паттерн для URL вида: https://server.com/team/channels/CHANNEL_ID
    url_pattern = r'/channels/([a-z0-9]+)'
    match = re.search(url_pattern, url)
    return match.group(1) if match else url.strip()


def get_channel_info(server_url: str, token: str, channel_id: str) -> dict:
    """
    Получает информацию о канале.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        
    Returns:
        dict: Информация о канале (включая team_id)
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/channels/{channel_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_channel_members(server_url: str, token: str, channel_id: str, per_page: int = 200) -> list:
    """
    Получает список членов канала с их полной информацией.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        per_page: Количество членов на страницу (макс 200)
        
    Returns:
        list: Список словарей с информацией о пользователях
    """
    all_members = []
    page = 0
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        api_url = f"{server_url.rstrip('/')}/api/v4/channels/{channel_id}/members"
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            members_batch = response.json()
            
            if not members_batch:
                break
            
            # Получаем полную информацию о каждом пользователе
            for member in members_batch:
                user_id = member.get('user_id')
                if user_id:
                    user_info = get_user_info(server_url, token, user_id)
                    if user_info:
                        all_members.append(user_info)
            
            # Если получили меньше чем per_page, значит это последняя страница
            if len(members_batch) < per_page:
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
    
    return all_members


def get_team_info(server_url: str, token: str, team_id: str) -> dict:
    """
    Получает информацию о team.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        team_id: ID команды
        
    Returns:
        dict: Информация о team (включая name)
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/teams/{team_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_team_by_name(server_url: str, token: str, team_name: str) -> dict:
    """
    Получает информацию о team по его имени.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        team_name: Имя команды (из URL)
        
    Returns:
        dict: Информация о team (включая id)
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/teams/name/{team_name}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_channel_by_name(server_url: str, token: str, team_id: str, channel_name: str) -> dict:
    """
    Получает информацию о канале по его имени в рамках team.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        team_id: ID команды
        channel_name: Имя канала (из URL)
        
    Returns:
        dict: Информация о канале (включая id)
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/teams/{team_id}/channels/name/{channel_name}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def resolve_channel_id(server_url: str, token: str, channel_input: str) -> tuple[str, str]:
    """
    Преобразует URL канала или его имя в channel_id.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_input: URL канала, имя канала или channel_id
        
    Returns:
        tuple: (channel_id, error_message). Если успешно - error_message пустая.
    """
    parsed = parse_channel_url(channel_input)
    
    # Если это URL с team и channel name
    if parsed.get('is_url') and parsed.get('team_name'):
        team_name = parsed['team_name']
        channel_name = parsed['channel_name']
        
        # Получаем team_id по имени
        team_info = get_team_by_name(server_url, token, team_name)
        if not team_info or 'id' not in team_info:
            return '', f'Не удалось найти team: {team_name}'
        
        team_id = team_info['id']
        
        # Получаем channel_id по имени
        channel_info = get_channel_by_name(server_url, token, team_id, channel_name)
        if not channel_info or 'id' not in channel_info:
            return '', f'Не удалось найти канал: {channel_name} в team: {team_name}'
        
        return channel_info['id'], ''
    
    # Если это просто строка - пробуем использовать как channel_id
    channel_id = parsed['channel_name']
    
    # Проверяем, что канал существует
    channel_info = get_channel_info(server_url, token, channel_id)
    if not channel_info or 'id' not in channel_info:
        return '', f'Канал не найден. Убедитесь, что вы указали правильный URL или ID канала.'
    
    return channel_id, ''


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
    
    # Дефолтные эмодзи для всех категорий
    default_emojis = [
        'ballot_box_with_check', 'leaves', 'ice_cube',  # Done
        'hammer_and_wrench',  # In Progress
        'loading', 'eyes'  # Control
    ]
    
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


def filter_root_posts_only(posts: list) -> list:
    """
    Фильтрует только root посты (без replies из тредов).
    
    Args:
        posts: Список постов
        
    Returns:
        list: Список только root постов (у которых нет root_id)
    """
    return [post for post in posts if not post.get('root_id')]


def filter_system_messages(posts: list) -> list:
    """
    Фильтрует системные сообщения (присоединение/выход из канала и т.д.).
    
    Args:
        posts: Список постов
        
    Returns:
        list: Список постов без системных сообщений
    """
    return [post for post in posts if not post.get('type')]


def enrich_posts_with_thread_reactions(server_url: str, token: str, posts: list) -> list:
    """
    Обогащает посты канала реакциями из их тредов.
    Для каждого поста получает все реакции из его треда и добавляет к metadata.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        posts: Список постов канала
        
    Returns:
        list: Посты с обогащенными реакциями (root + thread replies)
    """
    enriched_posts = []
    
    for post in posts:
        post_id = post.get('id')
        if not post_id:
            enriched_posts.append(post)
            continue
        
        # Создаем копию поста
        enriched_post = post.copy()
        
        try:
            # Получаем все реакции из треда (включая root пост)
            thread_reactions = get_thread_reactions(server_url, token, post_id, include_replies=True)
            
            if thread_reactions:
                # Обновляем metadata с реакциями из всего треда
                if 'metadata' not in enriched_post:
                    enriched_post['metadata'] = {}
                
                enriched_post['metadata']['reactions'] = thread_reactions
        except:
            # Если не удалось получить тред, оставляем как есть
            pass
        
        enriched_posts.append(enriched_post)
    
    return enriched_posts


# ============================================================================
# Функции для отправки сообщений
# ============================================================================

def get_user_id_by_identifier(server_url: str, token: str, identifier: str) -> Optional[str]:
    """
    Получает user_id по email или username.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        identifier: Email или username пользователя
        
    Returns:
        str: user_id или None, если пользователь не найден
    """
    # Сначала пробуем найти по email
    api_url = f"{server_url.rstrip('/')}/api/v4/users/email/{identifier}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('id')
    except requests.exceptions.RequestException:
        pass
    
    # Если не нашли по email, пробуем по username
    api_url = f"{server_url.rstrip('/')}/api/v4/users/username/{identifier}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('id')
    except requests.exceptions.RequestException:
        pass
    
    return None


def create_direct_channel(server_url: str, token: str, user_id1: str, user_id2: str) -> Optional[str]:
    """
    Создает или получает существующий Direct Message канал между двумя пользователями.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        user_id1: ID первого пользователя (отправитель)
        user_id2: ID второго пользователя (получатель)
        
    Returns:
        str: ID канала или None при ошибке
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/channels/direct"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = [user_id1, user_id2]
    
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json().get('id')
    except requests.exceptions.RequestException:
        return None


def send_message_to_channel(server_url: str, token: str, channel_id: str, message: str) -> bool:
    """
    Отправляет сообщение в указанный канал.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        message: Текст сообщения
        
    Returns:
        bool: True если успешно, False при ошибке
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/posts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "channel_id": channel_id,
        "message": message
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def send_direct_message(server_url: str, token: str, sender_id: str, recipient_identifier: str, message: str) -> dict:
    """
    Отправляет прямое сообщение пользователю.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        sender_id: ID отправителя (ваш user_id)
        recipient_identifier: Email или username получателя
        message: Текст сообщения
        
    Returns:
        dict: {'success': bool, 'recipient': str, 'error': str (опционально)}
    """
    # Получаем user_id получателя
    recipient_id = get_user_id_by_identifier(server_url, token, recipient_identifier)
    
    if not recipient_id:
        return {
            'success': False,
            'recipient': recipient_identifier,
            'error': 'Пользователь не найден'
        }
    
    # Создаем/получаем DM канал
    channel_id = create_direct_channel(server_url, token, sender_id, recipient_id)
    
    if not channel_id:
        return {
            'success': False,
            'recipient': recipient_identifier,
            'error': 'Не удалось создать DM канал'
        }
    
    # Отправляем сообщение
    success = send_message_to_channel(server_url, token, channel_id, message)
    
    return {
        'success': success,
        'recipient': recipient_identifier,
        'error': None if success else 'Не удалось отправить сообщение'
    }


def add_member_to_channel(server_url: str, token: str, channel_id: str, user_id: str) -> dict:
    """
    Добавляет пользователя в канал.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        user_id: ID пользователя
        
    Returns:
        dict: {'success': bool, 'error': str | None}
    """
    api_url = f"{server_url.rstrip('/')}/api/v4/channels/{channel_id}/members"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"user_id": user_id}
    
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return {'success': True, 'error': None}
    except requests.exceptions.HTTPError:
        if response.status_code == 403:
            return {'success': False, 'error': 'Нет прав для добавления пользователя'}
        elif response.status_code == 404:
            return {'success': False, 'error': 'Канал или пользователь не найден'}
        else:
            return {'success': False, 'error': f'Ошибка API: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Ошибка подключения: {str(e)}'}


def add_members_to_channel(server_url: str, token: str, channel_id: str, emails: list[str]) -> dict:
    """
    Добавляет список пользователей в канал по их email.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        channel_id: ID канала
        emails: Список email пользователей
        
    Returns:
        dict: {
            'total': int,
            'successful': int,
            'failed': int,
            'already_member': int,
            'results': list[dict]
        }
    """
    results = []
    successful = 0
    failed = 0
    already_member = 0
    
    for email in emails:
        email = email.strip()
        if not email:
            continue
            
        user_id = get_user_id_by_identifier(server_url, token, email)
        
        if not user_id:
            results.append({
                'email': email,
                'success': False,
                'error': 'Пользователь не найден'
            })
            failed += 1
            continue
        
        result = add_member_to_channel(server_url, token, channel_id, user_id)
        
        if result['success']:
            results.append({'email': email, 'success': True, 'error': None})
            successful += 1
        elif 'уже является' in str(result.get('error', '')).lower() or result.get('error', '').startswith('Ошибка API: 400'):
            results.append({'email': email, 'success': True, 'error': 'Уже в канале'})
            already_member += 1
        else:
            results.append({'email': email, 'success': False, 'error': result.get('error')})
            failed += 1
    
    return {
        'total': len(emails),
        'successful': successful,
        'failed': failed,
        'already_member': already_member,
        'results': results
    }


def broadcast_message(server_url: str, token: str, sender_id: str, recipients: list[str], message: str) -> dict:
    """
    Отправляет сообщение списку пользователей.
    
    Args:
        server_url: URL сервера Mattermost
        token: Токен доступа
        sender_id: ID отправителя (ваш user_id)
        recipients: Список email/username получателей
        message: Текст сообщения для отправки
        
    Returns:
        dict: {
            'total': int,
            'successful': int,
            'failed': int,
            'results': list[dict]  # Детальные результаты для каждого получателя
        }
    """
    results = []
    successful = 0
    failed = 0
    
    for recipient in recipients:
        result = send_direct_message(server_url, token, sender_id, recipient, message)
        results.append(result)
        
        if result['success']:
            successful += 1
        else:
            failed += 1
    
    return {
        'total': len(recipients),
        'successful': successful,
        'failed': failed,
        'results': results
    }
