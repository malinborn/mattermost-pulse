"""
Вкладка выгрузки и анализа канала
"""
import os
from datetime import datetime
import streamlit as st
from mattermost_api import (
    parse_channel_id_from_url,
    get_channel_info,
    get_team_info,
    get_channel_posts,
    analyze_channel_emojis,
    get_posts_without_reactions,
    get_posts_by_emoji,
    filter_root_posts_only,
    filter_system_messages,
    enrich_posts_with_thread_reactions,
    generate_post_link,
    get_user_info
)
from ai_helper import generate_channel_summary


def render_channel_tab(server_url: str, personal_token: str, product_name: str = "Mattermost"):
    """Отображает вкладку выгрузки канала"""
    st.markdown("**Режим:** Аналитика активности канала")
    st.markdown("Выгружает все посты из канала за указанный период и анализирует реакции")
    
    channel_input = st.text_input(
        "ID или URL канала",
        placeholder=f"https://{product_name.lower()}-server.com/team/channels/channel_id или просто channel_id",
        help="Полный URL канала или только его ID",
        key="channel_input"
    )
    
    # Date pickers
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Начальная дата",
            value=datetime.now().date(),
            help="Начало периода для анализа"
        )
    
    with col2:
        end_date = st.date_input(
            "Конечная дата",
            value=datetime.now().date(),
            help="Конец периода для анализа"
        )
    
    include_thread_reactions = st.checkbox(
        "Включить сообщения из тредов",
        value=False,
        help="Если включено, будут собраны реакции из рутовых постов и всех ответов в тредах"
    )
    
    if st.button("🔄 Загрузить посты и проанализировать эмодзи", type="primary", use_container_width=True, key="load_channel"):
        if not server_url:
            st.error(f"⚠️ Укажите URL сервера {product_name}")
        elif not personal_token:
            st.error("⚠️ Укажите личный токен доступа")
        elif not channel_input:
            st.error("⚠️ Укажите ID или URL канала")
        elif start_date > end_date:
            st.error("⚠️ Начальная дата не может быть позже конечной")
        else:
            _load_and_analyze_channel(
                server_url, personal_token, channel_input,
                start_date, end_date, include_thread_reactions
            )
    
    # Если посты загружены - показываем AI саммари и категории
    if 'channel_posts' in st.session_state and st.session_state.channel_posts:
        # Используем даты из session_state
        saved_start_date = st.session_state.get('start_date')
        saved_end_date = st.session_state.get('end_date')
        if saved_start_date and saved_end_date:
            _render_ai_summary_section(saved_start_date, saved_end_date)
        _render_categories_and_stats()


def _load_and_analyze_channel(server_url, personal_token, channel_input, start_date, end_date, include_thread_reactions):
    """Загрузка постов из канала и анализ"""
    with st.spinner("🔄 Загрузка постов из канала..."):
        try:
            channel_id = parse_channel_id_from_url(channel_input)
            st.info(f"📝 Channel ID: `{channel_id}`")
            
            # Получаем информацию о канале и team
            channel_info = get_channel_info(server_url, personal_token, channel_id)
            team_id = channel_info.get('team_id', '')
            team_info = get_team_info(server_url, personal_token, team_id) if team_id else {}
            team_name = team_info.get('name', 'team')
            
            # Получаем посты
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            posts = get_channel_posts(
                server_url,
                personal_token,
                channel_id,
                start_datetime,
                end_datetime
            )
            
            if not posts:
                st.warning("ℹ️ Нет постов за указанный период")
            else:
                st.success(f"✅ Загружено постов: {len(posts)}")
                
                # Фильтрация
                posts = filter_system_messages(posts)
                st.info(f"🧹 После фильтрации системных сообщений: {len(posts)}")
                
                if include_thread_reactions:
                    root_posts = filter_root_posts_only(posts)
                    st.info(f"📊 Найдено root постов: {len(root_posts)}")
                    
                    with st.spinner("🔄 Загрузка реакций из тредов..."):
                        posts = enrich_posts_with_thread_reactions(server_url, personal_token, root_posts)
                    st.success("✅ Реакции из тредов добавлены")
                else:
                    posts = filter_root_posts_only(posts)
                    st.info(f"📊 Root постов (без replies): {len(posts)}")
                
                # Анализируем эмодзи
                with st.spinner("🔍 Анализ эмодзи..."):
                    found_emojis = analyze_channel_emojis(posts)
                
                st.success(f"✅ Найдено уникальных эмодзи: {len(found_emojis)}")
                
                # Сохраняем в session_state
                st.session_state.channel_posts = posts
                st.session_state.found_emojis = found_emojis
                st.session_state.channel_id = channel_id
                st.session_state.include_thread_reactions = include_thread_reactions
                st.session_state.team_name = team_name
                st.session_state.start_date = start_date
                st.session_state.end_date = end_date
                
        except ValueError as e:
            st.error(f"❌ Ошибка: {str(e)}")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")


def _render_ai_summary_section(start_date, end_date):
    """Отображение секции AI-саммари канала"""
    st.divider()
    st.subheader("🤖 AI Саммари канала")
    
    # Инициализируем хранилище для саммари
    if 'ai_channel_summary' not in st.session_state:
        st.session_state.ai_channel_summary = None
    if 'show_ai_summary' not in st.session_state:
        st.session_state.show_ai_summary = False
    
    col1, col2 = st.columns([2, 5])
    
    with col1:
        if st.button("✨ Сгенерировать AI саммари", help="Создать краткое саммари активности канала за период", key="generate_summary_btn"):
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if not openai_api_key:
                st.error("🔑 Не найден API ключ OpenAI. Установите переменную окружения OPENAI_API_KEY")
            else:
                with st.spinner("🤖 Подготовка данных..."):
                    try:
                        posts = st.session_state.channel_posts
                        
                        # Собираем уникальных пользователей из первых 100 постов
                        unique_users = set()
                        for post in posts[:100]:
                            user_id = post.get('user_id')
                            if user_id:
                                unique_users.add(user_id)
                        
                        # Создаем кеш пользователей (один запрос на пользователя)
                        users_cache = {}
                        if unique_users:
                            st.info(f"Загрузка информации о {len(unique_users)} авторах...")
                            for user_id in unique_users:
                                try:
                                    user_info = get_user_info(
                                        st.session_state.server_url,
                                        st.session_state.personal_token,
                                        user_id
                                    )
                                    users_cache[user_id] = user_info
                                except:
                                    # Если не удалось получить инфо, используем ID
                                    users_cache[user_id] = {'username': f"User-{user_id[:8]}"}
                        
                        st.info("Генерация AI саммари...")
                        summary = generate_channel_summary(
                            posts,
                            str(start_date),
                            str(end_date),
                            openai_api_key,
                            users_cache
                        )
                        st.session_state.ai_channel_summary = summary
                        st.session_state.show_ai_summary = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ошибка при генерации саммари: {str(e)}")
    
    with col2:
        if st.session_state.show_ai_summary:
            if st.button("❌ Скрыть саммари", help="Скрыть AI саммари", key="hide_summary_btn"):
                st.session_state.show_ai_summary = False
                st.rerun()
    
    # Показываем саммари
    if st.session_state.show_ai_summary and st.session_state.ai_channel_summary:
        st.markdown("---")
        st.markdown("### 📊 Результат анализа")
        
        with st.container():
            st.markdown(st.session_state.ai_channel_summary)
        
        st.markdown("---")
        
        # Копирование в буфер обмена
        with st.expander("📋 Саммари в текстовом виде (для копирования)"):
            st.text_area(
                "Саммари",
                value=st.session_state.ai_channel_summary,
                height=300,
                key="summary_text_area",
                label_visibility="collapsed"
            )


def _render_categories_and_stats():
    """Отображение категорий эмодзи и статистики"""
    st.divider()
    
    thread_mode = st.session_state.get('include_thread_reactions', False)
    if thread_mode:
        st.info("ℹ️ Данные загружены с учетом реакций из тредов")
    else:
        st.info("ℹ️ Данные загружены только для рутовых постов (без тредов)")
    
    st.markdown("**Настройка категорий статусов:**")
    st.markdown("Распределите эмодзи по категориям для группировки статистики")
    
    # Дефолтные эмодзи для всех категорий
    default_done = ['leaves', 'ice_cube', 'ballot_box_with_check']
    default_in_progress = ['hammer_and_wrench']
    default_control = ['loading', 'eyes']
    
    # Подготавливаем дефолты, которые есть в найденных эмодзи
    done_default = [e for e in default_done if e in st.session_state.found_emojis]
    in_progress_default = [e for e in default_in_progress if e in st.session_state.found_emojis]
    control_default = [e for e in default_control if e in st.session_state.found_emojis]
    
    # Категория: Done
    # Исключаем из options дефолты последующих категорий
    reserved_for_later = set(in_progress_default + control_default)
    available_for_done = [e for e in st.session_state.found_emojis if e not in reserved_for_later]
    
    with st.expander("✅ Done (Завершено)", expanded=True):
        done_emojis = st.multiselect(
            "Эмодзи для категории Done",
            options=available_for_done,
            default=done_default,
            key="done_emojis",
            help="Эмодзи, обозначающие завершенные задачи"
        )
    
    # Категория: In Progress
    # Исключаем уже выбранные в Done и дефолты Control
    reserved_for_control = set(control_default)
    available_for_in_progress = [
        e for e in st.session_state.found_emojis 
        if e not in done_emojis and e not in reserved_for_control
    ]
    
    with st.expander("🔧 In Progress (В процессе)", expanded=True):
        in_progress_emojis = st.multiselect(
            "Эмодзи для категории In Progress",
            options=available_for_in_progress,
            default=[e for e in in_progress_default if e in available_for_in_progress],
            key="in_progress_emojis",
            help="Эмодзи, обозначающие задачи в процессе"
        )
    
    # Категория: Control
    # Исключаем уже выбранные в Done и In Progress
    used_emojis = set(done_emojis) | set(in_progress_emojis)
    available_for_control = [e for e in st.session_state.found_emojis if e not in used_emojis]
    
    with st.expander("👁️ Control (Контроль)", expanded=True):
        control_emojis = st.multiselect(
            "Эмодзи для категории Control",
            options=available_for_control,
            default=[e for e in control_default if e in available_for_control],
            key="control_emojis",
            help="Эмодзи, обозначающие задачи на контроле"
        )
    
    if st.button("📊 Показать статистику", type="secondary", use_container_width=True, key="show_stats"):
        if not done_emojis and not in_progress_emojis and not control_emojis:
            st.warning("⚠️ Выберите хотя бы один эмодзи в любой из категорий")
        else:
            _display_statistics(done_emojis, in_progress_emojis, control_emojis)


def _display_statistics(done_emojis, in_progress_emojis, control_emojis):
    """Отображение статистики по категориям"""
    st.divider()
    st.subheader("📊 Статистика")
    
    categories = {
        'Done': done_emojis,
        'In Progress': in_progress_emojis,
        'Control': control_emojis
    }
    st.session_state.categories = categories
    
    # Подсчет статистики
    total_posts = len(st.session_state.channel_posts)
    posts_without_reactions = get_posts_without_reactions(st.session_state.channel_posts)
    
    category_counts = {}
    for category_name, emojis in categories.items():
        category_posts = set()
        if emojis:
            for emoji in emojis:
                posts_with_emoji = get_posts_by_emoji(st.session_state.channel_posts, emoji)
                for post in posts_with_emoji:
                    category_posts.add(post['id'])
        category_counts[category_name] = len(category_posts)
    
    # Метрики
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Всего постов", total_posts)
    with col2:
        st.metric("✅ Done", category_counts.get('Done', 0))
    with col3:
        st.metric("🔧 In Progress", category_counts.get('In Progress', 0))
    with col4:
        st.metric("👁️ Control", category_counts.get('Control', 0))
    with col5:
        st.metric("📭 Нет реакций", len(posts_without_reactions))
    
    st.divider()
    
    # Детализация по категориям
    _display_category_details(categories)
    
    # Посты без реакций
    _display_posts_without_reactions(posts_without_reactions)


def _display_category_details(categories):
    """Отображение детализации по категориям"""
    category_order = ['Done', 'In Progress', 'Control']
    category_icons = {
        'Done': '✅',
        'In Progress': '🔧',
        'Control': '👁️'
    }
    
    for category_name in category_order:
        emojis = categories.get(category_name, [])
        
        if not emojis:
            continue
        
        # Собираем уникальные посты для категории
        category_posts_dict = {}
        
        for emoji in emojis:
            posts_with_emoji = get_posts_by_emoji(st.session_state.channel_posts, emoji)
            for post in posts_with_emoji:
                post_id = post.get('id')
                if post_id not in category_posts_dict:
                    category_posts_dict[post_id] = post
        
        category_posts_list = list(category_posts_dict.values())
        icon = category_icons.get(category_name, '📌')
        
        with st.expander(f"{icon} {category_name} — {len(category_posts_list)} постов", expanded=True):
            st.markdown(f"**Эмодзи:** {', '.join([f':{e}:' for e in emojis])}")
            st.divider()
            
            if not category_posts_list:
                st.info(f"Нет постов в категории {category_name}")
            else:
                _display_posts_list(category_posts_list)


def _display_posts_without_reactions(posts_without_reactions):
    """Отображение постов без реакций"""
    with st.expander(f"📭 Посты без реакций — {len(posts_without_reactions)} постов", expanded=False):
        if not posts_without_reactions:
            st.info("Нет постов без реакций")
        else:
            _display_posts_list(posts_without_reactions)


def _display_posts_list(posts_list):
    """Отображение списка постов"""
    for post in posts_list[:50]:
        message = post.get('message', '')
        user_id = post.get('user_id', 'unknown')
        post_id = post.get('id', '')
        create_at = post.get('create_at', 0)
        
        # Получаем информацию о пользователе
        user_info = get_user_info(
            st.session_state.server_url,
            st.session_state.personal_token,
            user_id
        )
        author_name = user_info.get('username') or user_info.get('email') or user_id
        
        if create_at:
            post_date = datetime.fromtimestamp(create_at / 1000).strftime('%Y-%m-%d %H:%M')
        else:
            post_date = 'Unknown'
        
        post_link = generate_post_link(
            st.session_state.server_url,
            st.session_state.team_name,
            post_id
        )
        
        st.markdown(f"`{author_name}` | **Дата:** {post_date}")
        st.markdown(f"**Текст:** {message[:200]}{'...' if len(message) > 200 else ''}")
        st.markdown(f"**Ссылка:** [{post_id}]({post_link})")
        st.markdown("---")
    
    if len(posts_list) > 50:
        st.info(f"Показано первых 50 из {len(posts_list)} постов")
