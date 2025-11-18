"""
Mattermost Reactions Exporter
Экспортирует реакции из постов Mattermost в YAML-формат.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from mattermost_api import (
    get_reactions, 
    parse_post_id, 
    process_reactions, 
    get_unique_emojis,
    get_thread_reactions,
    get_thread_reactions_separated,
    get_thread_posts,
    get_thread_posts_with_reactions,
    # Функции для работы с каналами
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
    generate_post_link
)


def main():
    st.set_page_config(
        page_title="Mattermost Reactions Exporter",
        page_icon="📊",
        layout="centered"
    )
    
    st.title("📊 Экспортер реакций Mattermost")
    st.markdown("Получает реакции из поста Mattermost и экспортирует в YAML-формат")
    
    # Общие поля ввода данных (вынесены за пределы вкладок)
    st.subheader("Настройки подключения")
    
    server_url = st.text_input(
        "URL сервера Mattermost",
        value="https://dodobrands.loop.ru",
        placeholder="https://your-mattermost-server.com",
        help="URL сервера Mattermost (с https://)"
    )
    
    personal_token = st.text_input(
        "Личный токен доступа",
        type="password",
        placeholder="Введите ваш личный токен",
        help="Личный токен для авторизации в Mattermost API"
    )
    
    st.divider()
    
    # Создаем вкладки для разных режимов работы
    tab1, tab2, tab3 = st.tabs(["📥 Выгрузить тред", "🎯 Выборочно", "📊 Выгрузить канал"])
    
    # Вкладка 1: Выгрузка треда
    with tab1:
        st.markdown("**Режим:** Выгрузка реакций из треда")
        st.markdown("Собирает реакции с root поста и всех replies в треде")
        
        post_input = st.text_input(
            "URL или ID поста",
            placeholder="https://mattermost.com/team/pl/post_id или просто post_id",
            help="Полный URL поста или только его ID",
            key="thread_post_input"
        )
        
        # Опция включения/исключения replies
        include_replies = st.checkbox(
            "Включить реакции из replies",
            value=True,
            help="Если отключено, будут собраны реакции только с root поста"
        )
        
        if st.button("🚀 Выгрузить реакции", type="primary", use_container_width=True, key="thread_reactions"):
            if not server_url:
                st.error("⚠️ Укажите URL сервера Mattermost")
            elif not personal_token:
                st.error("⚠️ Укажите личный токен доступа")
            elif not post_input:
                st.error("⚠️ Укажите URL или ID поста")
            else:
                with st.spinner("🔄 Получение данных из треда..."):
                    try:
                        post_id = parse_post_id(post_input)
                        st.info(f"📝 Post ID: `{post_id}`")
                        
                        # Получаем информацию о треде
                        thread_data = get_thread_posts(server_url, personal_token, post_id)
                        
                        if not thread_data:
                            st.warning("ℹ️ Не удалось получить данные треда")
                        else:
                            posts_count = len(thread_data.get('order', []))
                            st.info(f"📊 Постов в треде: {posts_count}")
                            
                            # Если галка включена - показываем раздельно с деталями
                            if include_replies and posts_count > 1:
                                # Получаем детальную информацию о постах с реакциями
                                with st.spinner("🔄 Получение детальной информации о постах..."):
                                    posts_with_reactions = get_thread_posts_with_reactions(
                                        server_url, 
                                        personal_token, 
                                        post_id
                                    )
                                
                                root_post = posts_with_reactions.get('root')
                                replies_posts = posts_with_reactions.get('replies', [])
                                
                                # Отображаем root пост
                                if root_post:
                                    st.subheader("📌 Root пост")
                                    
                                    if root_post.get('reactions'):
                                        st.markdown(f"**Автор:** {root_post['author']}")
                                        st.markdown(f"**Сообщение:** {root_post['message'][:200]}{'...' if len(root_post['message']) > 200 else ''}")
                                        st.markdown(f"**Реакции:** {len(root_post['reactions'])} уникальных эмодзи")
                                        st.json(root_post['reactions'])
                                    else:
                                        st.info("ℹ️ На root посте нет реакций")
                                else:
                                    st.warning("ℹ️ Не удалось получить данные root поста")
                                
                                st.divider()
                                
                                # Отображаем replies
                                st.subheader("💬 Replies")
                                
                                if replies_posts:
                                    replies_with_reactions = [p for p in replies_posts if p.get('reactions')]
                                    
                                    if replies_with_reactions:
                                        st.success(f"✅ Постов с реакциями: {len(replies_with_reactions)} из {len(replies_posts)}")
                                        
                                        # Формируем список replies для JSON
                                        replies_json = []
                                        for reply in replies_with_reactions:
                                            replies_json.append({
                                                'author': reply['author'],
                                                'message': reply['message'],
                                                'reactions': reply['reactions']
                                            })
                                        
                                        # Отображаем все replies как один JSON
                                        st.json(replies_json)
                                    else:
                                        st.info("ℹ️ В replies нет реакций")
                                else:
                                    st.info("ℹ️ В треде нет replies")
                            else:
                                # Обычный режим - получаем все вместе или только root
                                reactions = get_thread_reactions(
                                    server_url, 
                                    personal_token, 
                                    post_id, 
                                    include_replies=include_replies
                                )
                                
                                if not reactions:
                                    st.warning("ℹ️ Нет реакций")
                                else:
                                    st.success(f"✅ Найдено реакций: {len(reactions)}")
                                    
                                    # Обрабатываем реакции
                                    with st.spinner("🔄 Получение данных пользователей..."):
                                        emoji_data = process_reactions(server_url, personal_token, reactions)
                                    
                                    st.success(f"✅ Обработано уникальных эмодзи: {len(emoji_data)}")
                                    
                                    st.subheader("📊 Результат")
                                    st.json(emoji_data)
                                    
                    except ValueError as e:
                        st.error(f"❌ Ошибка: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Неожиданная ошибка: {str(e)}")
    
    # Вкладка 2: Выборочная выгрузка эмодзи
    with tab2:
        st.markdown("**Режим:** Выборочная выгрузка по выбранным эмодзи")
        st.markdown("Сначала загрузите список эмодзи, затем выберите нужные для анализа")
        
        post_input_selective = st.text_input(
            "URL или ID поста",
            placeholder="https://mattermost.com/team/pl/post_id или просто post_id",
            help="Полный URL поста или только его ID",
            key="selective_post_input"
        )
        
        # Шаг 1: Загрузка списка эмодзи
        if st.button("📥 Загрузить список эмодзи", use_container_width=True, key="load_emojis"):
            if not server_url:
                st.error("⚠️ Укажите URL сервера Mattermost")
            elif not personal_token:
                st.error("⚠️ Укажите личный токен доступа")
            elif not post_input_selective:
                st.error("⚠️ Укажите URL или ID поста")
            else:
                with st.spinner("🔄 Загрузка списка эмодзи..."):
                    try:
                        post_id = parse_post_id(post_input_selective)
                        st.info(f"📝 Post ID: `{post_id}`")
                        
                        reactions = get_reactions(server_url, personal_token, post_id)
                        
                        if not reactions:
                            st.warning("ℹ️ У этого поста нет реакций")
                        else:
                            unique_emojis = get_unique_emojis(reactions)
                            st.session_state.reactions = reactions
                            st.session_state.unique_emojis = unique_emojis
                            st.success(f"✅ Найдено уникальных эмодзи: {len(unique_emojis)}")
                            
                    except ValueError as e:
                        st.error(f"❌ Ошибка: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Неожиданная ошибка: {str(e)}")
        
        # Шаг 2: Выбор эмодзи
        if 'unique_emojis' in st.session_state and st.session_state.unique_emojis:
            st.divider()
            st.markdown("**Выберите эмодзи для анализа:**")
            
            # Используем мультиселект для выбора эмодзи
            selected_emojis = st.multiselect(
                "Эмодзи",
                options=st.session_state.unique_emojis,
                default=st.session_state.unique_emojis,
                help="Выберите один или несколько эмодзи для получения статистики"
            )
            
            # Шаг 3: Обработка выбранных эмодзи
            if st.button("🚀 Получить реакции по выбранным эмодзи", type="primary", use_container_width=True, key="selected_emojis"):
                if not selected_emojis:
                    st.warning("⚠️ Выберите хотя бы один эмодзи")
                else:
                    with st.spinner("🔄 Получение данных пользователей..."):
                        try:
                            emoji_data = process_reactions(
                                server_url, 
                                personal_token, 
                                st.session_state.reactions,
                                emoji_filter=selected_emojis
                            )
                            
                            st.success(f"✅ Обработано эмодзи: {len(emoji_data)}")
                            
                            st.subheader("📊 Результат")
                            st.json(emoji_data)
                            
                        except Exception as e:
                            st.error(f"❌ Ошибка при обработке: {str(e)}")
    
    # Вкладка 3: Выгрузка канала
    with tab3:
        st.markdown("**Режим:** Аналитика активности канала")
        st.markdown("Выгружает все посты из канала за указанный период и анализирует реакции")
        
        # Поле для ID/URL канала
        channel_input = st.text_input(
            "ID или URL канала",
            placeholder="https://mattermost.com/team/channels/channel_id или просто channel_id",
            help="Полный URL канала или только его ID",
            key="channel_input"
        )
        
        # Date pickers для выбора диапазона дат
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
        
        # Checkbox для включения реакций из тредов
        include_thread_reactions = st.checkbox(
            "Включить сообщения из тредов",
            value=False,
            help="Если включено, будут собраны реакции из рутовых постов и всех ответов в тредах"
        )
        
        # Кнопка загрузки постов
        if st.button("🔄 Загрузить посты и проанализировать эмодзи", type="primary", use_container_width=True, key="load_channel"):
            if not server_url:
                st.error("⚠️ Укажите URL сервера Mattermost")
            elif not personal_token:
                st.error("⚠️ Укажите личный токен доступа")
            elif not channel_input:
                st.error("⚠️ Укажите ID или URL канала")
            elif start_date > end_date:
                st.error("⚠️ Начальная дата не может быть позже конечной")
            else:
                with st.spinner("🔄 Загрузка постов из канала..."):
                    try:
                        # Парсим ID канала
                        channel_id = parse_channel_id_from_url(channel_input)
                        st.info(f"📝 Channel ID: `{channel_id}`")
                        
                        # Получаем информацию о канале и team для генерации ссылок
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
                            
                            # Фильтруем системные сообщения
                            posts = filter_system_messages(posts)
                            st.info(f"🧹 После фильтрации системных сообщений: {len(posts)}")
                            
                            # Если включены реакции из тредов, обогащаем посты
                            if include_thread_reactions:
                                # Сначала фильтруем только root посты
                                root_posts = filter_root_posts_only(posts)
                                st.info(f"📊 Найдено root постов: {len(root_posts)}")
                                
                                # Затем обогащаем их реакциями из тредов
                                with st.spinner("🔄 Загрузка реакций из тредов..."):
                                    posts = enrich_posts_with_thread_reactions(server_url, personal_token, root_posts)
                                st.success("✅ Реакции из тредов добавлены")
                            else:
                                # Фильтруем только root посты
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
                            st.session_state.server_url = server_url
                            
                    except ValueError as e:
                        st.error(f"❌ Ошибка: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Неожиданная ошибка: {str(e)}")
        
        # Если посты загружены, показываем опции для выбора эмодзи
        if 'channel_posts' in st.session_state and st.session_state.channel_posts:
            st.divider()
            
            # Показываем информацию о режиме загрузки
            thread_mode = st.session_state.get('include_thread_reactions', False)
            if thread_mode:
                st.info("ℹ️ Данные загружены с учетом реакций из тредов")
            else:
                st.info("ℹ️ Данные загружены только для рутовых постов (без тредов)")
            
            st.markdown("**Настройка категорий статусов:**")
            st.markdown("Распределите эмодзи по категориям для группировки статистики")
            
            # Определяем дефолтные эмодзи для каждой категории
            default_done = ['leaves', 'ice_cube', 'ballot_box_with_check']
            default_in_progress = ['hammer_and_wrench']
            default_control = ['loading']
            
            # Категория: Done
            with st.expander("✅ Done (Завершено)", expanded=True):
                done_default = [e for e in default_done if e in st.session_state.found_emojis]
                done_emojis = st.multiselect(
                    "Эмодзи для категории Done",
                    options=st.session_state.found_emojis,
                    default=done_default,
                    key="done_emojis",
                    help="Эмодзи, обозначающие завершенные задачи"
                )
            
            # Категория: In Progress
            with st.expander("🔧 In Progress (В процессе)", expanded=True):
                in_progress_default = [e for e in default_in_progress if e in st.session_state.found_emojis]
                in_progress_emojis = st.multiselect(
                    "Эмодзи для категории In Progress",
                    options=st.session_state.found_emojis,
                    default=in_progress_default,
                    key="in_progress_emojis",
                    help="Эмодзи, обозначающие задачи в процессе"
                )
            
            # Категория: Control
            with st.expander("👁️ Control (Контроль)", expanded=True):
                control_default = [e for e in default_control if e in st.session_state.found_emojis]
                control_emojis = st.multiselect(
                    "Эмодзи для категории Control",
                    options=st.session_state.found_emojis,
                    default=control_default,
                    key="control_emojis",
                    help="Эмодзи, обозначающие задачи на контроле"
                )
            
            # Кнопка "Показать статистику"
            if st.button("📊 Показать статистику", type="secondary", use_container_width=True, key="show_stats"):
                # Проверяем, что хотя бы в одной категории есть эмодзи
                if not done_emojis and not in_progress_emojis and not control_emojis:
                    st.warning("⚠️ Выберите хотя бы один эмодзи в любой из категорий")
                else:
                    st.divider()
                    st.subheader("📊 Статистика")
                    
                    # Сохраняем категории в session_state
                    categories = {
                        'Done': done_emojis,
                        'In Progress': in_progress_emojis,
                        'Control': control_emojis
                    }
                    st.session_state.categories = categories
                    
                    # Общая статистика
                    total_posts = len(st.session_state.channel_posts)
                    posts_with_reactions = [p for p in st.session_state.channel_posts if p.get('metadata', {}).get('reactions')]
                    posts_without_reactions = get_posts_without_reactions(st.session_state.channel_posts)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Всего постов", total_posts)
                    with col2:
                        st.metric("С реакциями", len(posts_with_reactions))
                    with col3:
                        st.metric("Без реакций", len(posts_without_reactions))
                    
                    st.divider()
                    
                    # Таблица с подсчетом по категориям
                    st.markdown("### Сводка по категориям")
                    
                    category_data = []
                    for category_name, emojis in categories.items():
                        if emojis:  # Только если в категории есть эмодзи
                            # Собираем все посты для всех эмодзи в категории
                            category_posts = set()
                            total_reactions_count = 0
                            
                            for emoji in emojis:
                                posts_with_emoji = get_posts_by_emoji(st.session_state.channel_posts, emoji)
                                for post in posts_with_emoji:
                                    category_posts.add(post['id'])
                                    total_reactions_count += post.get('emoji_count', 0)
                            
                            category_data.append({
                                'Категория': category_name,
                                'Эмодзи': ', '.join([f':{e}:' for e in emojis]),
                                'Постов': len(category_posts),
                                'Всего реакций': total_reactions_count
                            })
                    
                    if category_data:
                        df = pd.DataFrame(category_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        st.divider()
                    
                    # Статистика по каждой категории
                    for category_name, emojis in categories.items():
                        if not emojis:  # Пропускаем пустые категории
                            continue
                        
                        # Собираем уникальные посты для категории
                        category_posts_dict = {}  # post_id -> post data
                        
                        for emoji in emojis:
                            posts_with_emoji = get_posts_by_emoji(st.session_state.channel_posts, emoji)
                            for post in posts_with_emoji:
                                post_id = post.get('id')
                                if post_id not in category_posts_dict:
                                    category_posts_dict[post_id] = post
                        
                        category_posts_list = list(category_posts_dict.values())
                        
                        # Определяем иконку для категории
                        category_icons = {
                            'Done': '✅',
                            'In Progress': '🔧',
                            'Control': '👁️'
                        }
                        icon = category_icons.get(category_name, '📌')
                        
                        with st.expander(f"{icon} {category_name} — {len(category_posts_list)} постов", expanded=True):
                            # Показываем эмодзи в категории
                            st.markdown(f"**Эмодзи:** {', '.join([f':{e}:' for e in emojis])}")
                            st.divider()
                            
                            if not category_posts_list:
                                st.info(f"Нет постов в категории {category_name}")
                            else:
                                for post in category_posts_list[:50]:  # Ограничиваем 50 постами
                                    # Получаем информацию о посте
                                    message = post.get('message', '')
                                    user_id = post.get('user_id', 'unknown')
                                    post_id = post.get('id', '')
                                    create_at = post.get('create_at', 0)
                                    
                                    # Форматируем дату
                                    if create_at:
                                        post_date = datetime.fromtimestamp(create_at / 1000).strftime('%Y-%m-%d %H:%M')
                                    else:
                                        post_date = 'Unknown'
                                    
                                    # Генерируем ссылку на пост
                                    post_link = generate_post_link(
                                        st.session_state.server_url,
                                        st.session_state.team_name,
                                        post_id
                                    )
                                    
                                    # Отображаем информацию
                                    st.markdown(f"**Автор:** `{user_id}` | **Дата:** {post_date}")
                                    st.markdown(f"**Текст:** {message[:200]}{'...' if len(message) > 200 else ''}")
                                    st.markdown(f"**Ссылка:** [{post_id}]({post_link})")
                                    st.markdown("---")
                                
                                if len(category_posts_list) > 50:
                                    st.info(f"Показано первых 50 из {len(category_posts_list)} постов")
                    
                    # Посты без реакций (показываем всегда)
                    with st.expander(f"📭 Посты без реакций — {len(posts_without_reactions)} постов", expanded=False):
                        if not posts_without_reactions:
                            st.info("Нет постов без реакций")
                        else:
                            for post in posts_without_reactions[:50]:  # Ограничиваем 50 постами
                                # Получаем информацию о посте
                                message = post.get('message', '')
                                user_id = post.get('user_id', 'unknown')
                                post_id = post.get('id', '')
                                create_at = post.get('create_at', 0)
                                
                                # Форматируем дату
                                if create_at:
                                    post_date = datetime.fromtimestamp(create_at / 1000).strftime('%Y-%m-%d %H:%M')
                                else:
                                    post_date = 'Unknown'
                                
                                # Генерируем ссылку на пост
                                post_link = generate_post_link(
                                    st.session_state.server_url,
                                    st.session_state.team_name,
                                    post_id
                                )
                                
                                # Отображаем информацию
                                st.markdown(f"**Автор:** `{user_id}` | **Дата:** {post_date}")
                                st.markdown(f"**Текст:** {message[:200]}{'...' if len(message) > 200 else ''}")
                                st.markdown(f"**Ссылка:** [{post_id}]({post_link})")
                                st.markdown("---")
                            
                            if len(posts_without_reactions) > 50:
                                st.info(f"Показано первых 50 из {len(posts_without_reactions)} постов")


if __name__ == "__main__":
    main()
