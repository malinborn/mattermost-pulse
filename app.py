"""
Mattermost Reactions Exporter
Экспортирует реакции из постов Mattermost в YAML-формат.
"""

import streamlit as st

from mattermost_api import (
    get_reactions, 
    parse_post_id, 
    process_reactions, 
    get_unique_emojis,
    get_thread_reactions,
    get_thread_reactions_separated,
    get_thread_posts,
    get_thread_posts_with_reactions
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
    
    st.subheader("Пост для экспорта")
    
    post_input = st.text_input(
        "URL или ID поста",
        placeholder="https://mattermost.com/team/pl/post_id или просто post_id",
        help="Полный URL поста или только его ID"
    )
    
    st.divider()
    
    # Создаем вкладки для разных режимов работы
    tab1, tab2 = st.tabs(["📥 Выгрузить тред", "🎯 Выборочно"])
    
    # Вкладка 1: Выгрузка треда
    with tab1:
        st.markdown("**Режим:** Выгрузка реакций из треда")
        st.markdown("Собирает реакции с root поста и всех replies в треде")
        
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
        
        # Шаг 1: Загрузка списка эмодзи
        if st.button("📥 Загрузить список эмодзи", use_container_width=True, key="load_emojis"):
            if not server_url:
                st.error("⚠️ Укажите URL сервера Mattermost")
            elif not personal_token:
                st.error("⚠️ Укажите личный токен доступа")
            elif not post_input:
                st.error("⚠️ Укажите URL или ID поста")
            else:
                with st.spinner("🔄 Загрузка списка эмодзи..."):
                    try:
                        post_id = parse_post_id(post_input)
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


if __name__ == "__main__":
    main()
