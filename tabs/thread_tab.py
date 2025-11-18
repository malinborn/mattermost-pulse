"""
Вкладка выгрузки реакций из треда
"""
import streamlit as st
from mattermost_api import (
    parse_post_id,
    get_thread_reactions,
    get_unique_emojis,
    process_reactions,
    get_thread_posts_with_reactions
)


def render_thread_tab(server_url: str, personal_token: str):
    """Отображает вкладку выгрузки треда"""
    st.markdown("**Режим:** Выгрузка реакций из треда с возможностью выборочной фильтрации")
    st.markdown("Объединяет функциональность выгрузки треда и выборочной фильтрации по эмодзи")
    
    post_input_v2 = st.text_input(
        "URL или ID поста",
        placeholder="https://mattermost.com/team/pl/post_id или просто post_id",
        help="Полный URL поста или только его ID",
        key="thread_v2_post_input"
    )
    
    # Опции
    include_replies_v2 = st.checkbox(
        "Включить реакции из replies",
        value=True,
        help="Если отключено, будут собраны реакции только с root поста",
        key="include_replies_v2"
    )
    
    selective_mode = st.checkbox(
        "Выборочная выгрузка по эмодзи",
        value=False,
        help="Если включено, можно выбрать конкретные эмодзи для анализа",
        key="selective_mode_v2"
    )
    
    show_messages_breakdown = st.checkbox(
        "Разбивка по сообщениям",
        value=False,
        help="Показывает детальную информацию по каждому посту с его реакциями",
        key="messages_breakdown_v2"
    )
    
    # Кнопка загрузки
    button_label = "📥 Загрузить список эмодзи" if selective_mode else "🚀 Выгрузить реакции"
    
    if st.button(button_label, type="primary", use_container_width=True, key="thread_v2_load"):
        if not server_url:
            st.error("⚠️ Укажите URL сервера Mattermost")
        elif not personal_token:
            st.error("⚠️ Укажите личный токен доступа")
        elif not post_input_v2:
            st.error("⚠️ Укажите URL или ID поста")
        else:
            _handle_load_thread(
                server_url, personal_token, post_input_v2, 
                include_replies_v2, selective_mode, show_messages_breakdown
            )
    
    # Выборочный режим - мультиселект эмодзи
    if selective_mode and 'unique_emojis_v2' in st.session_state and st.session_state.unique_emojis_v2:
        _render_emoji_selector(
            server_url, personal_token, 
            include_replies_v2, show_messages_breakdown
        )


def _handle_load_thread(server_url, personal_token, post_input, include_replies, selective_mode, show_messages_breakdown):
    """Обработка загрузки треда"""
    with st.spinner("🔄 Получение данных из треда..."):
        try:
            post_id = parse_post_id(post_input)
            st.info(f"📝 Post ID: `{post_id}`")
            
            reactions_v2 = get_thread_reactions(
                server_url, 
                personal_token, 
                post_id, 
                include_replies=include_replies
            )
            
            if not reactions_v2:
                st.warning("ℹ️ Нет реакций")
            else:
                st.success(f"✅ Найдено реакций: {len(reactions_v2)}")
                
                if selective_mode:
                    unique_emojis_v2 = get_unique_emojis(reactions_v2)
                    st.session_state.reactions_v2 = reactions_v2
                    st.session_state.unique_emojis_v2 = unique_emojis_v2
                    st.session_state.post_id_v2 = post_id
                    st.success(f"✅ Найдено уникальных эмодзи: {len(unique_emojis_v2)}")
                else:
                    if show_messages_breakdown and include_replies:
                        _display_messages_breakdown(server_url, personal_token, post_id)
                    else:
                        _display_aggregated_reactions(server_url, personal_token, reactions_v2)
            
        except ValueError as e:
            st.error(f"❌ Ошибка: {str(e)}")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")


def _display_messages_breakdown(server_url, personal_token, post_id, emoji_filter=None):
    """Отображение разбивки по сообщениям"""
    with st.spinner("🔄 Получение детальной информации о постах..."):
        posts_with_reactions = get_thread_posts_with_reactions(server_url, personal_token, post_id)
    
    root_post = posts_with_reactions.get('root')
    replies_posts = posts_with_reactions.get('replies', [])
    
    # Root пост
    if root_post:
        st.subheader("📌 Root пост")
        
        if root_post.get('reactions'):
            reactions = root_post['reactions']
            if emoji_filter:
                reactions = {emoji: users for emoji, users in reactions.items() if emoji in emoji_filter}
            
            if reactions:
                st.markdown(f"**Автор:** {root_post['author']}")
                st.markdown(f"**Сообщение:** {root_post['message'][:200]}{'...' if len(root_post['message']) > 200 else ''}")
                st.markdown(f"**Реакции:** {len(reactions)} {'выбранных ' if emoji_filter else 'уникальных '}эмодзи")
                st.json(reactions)
            else:
                st.info("ℹ️ На root посте нет выбранных эмодзи" if emoji_filter else "ℹ️ На root посте нет реакций")
        else:
            st.info("ℹ️ На root посте нет реакций")
    else:
        st.warning("ℹ️ Не удалось получить данные root поста")
    
    st.divider()
    
    # Replies
    st.subheader("💬 Replies")
    
    if replies_posts:
        replies_json = []
        for reply in replies_posts:
            if reply.get('reactions'):
                reactions = reply['reactions']
                if emoji_filter:
                    reactions = {emoji: users for emoji, users in reactions.items() if emoji in emoji_filter}
                
                if reactions:
                    replies_json.append({
                        'author': reply['author'],
                        'message': reply['message'],
                        'reactions': reactions
                    })
        
        if replies_json:
            st.success(f"✅ Постов с {'выбранными ' if emoji_filter else ''}реакциями: {len(replies_json)} из {len(replies_posts)}")
            st.json(replies_json)
        else:
            st.info("ℹ️ В replies нет выбранных эмодзи" if emoji_filter else "ℹ️ В replies нет реакций")
    else:
        st.info("ℹ️ В треде нет replies")


def _display_aggregated_reactions(server_url, personal_token, reactions):
    """Отображение агрегированных реакций"""
    with st.spinner("🔄 Получение данных пользователей..."):
        emoji_data = process_reactions(server_url, personal_token, reactions)
    
    st.success(f"✅ Обработано уникальных эмодзи: {len(emoji_data)}")
    st.subheader("📊 Результат")
    st.json(emoji_data)


def _render_emoji_selector(server_url, personal_token, include_replies, show_messages_breakdown):
    """Отображение селектора эмодзи"""
    st.divider()
    st.markdown("**Выберите эмодзи для анализа:**")
    
    selected_emojis_v2 = st.multiselect(
        "Эмодзи",
        options=st.session_state.unique_emojis_v2,
        default=st.session_state.unique_emojis_v2,
        help="Выберите один или несколько эмодзи для получения статистики",
        key="selected_emojis_v2"
    )
    
    if st.button("🚀 Получить реакции по выбранным эмодзи", type="primary", use_container_width=True, key="process_selected_v2"):
        if not selected_emojis_v2:
            st.warning("⚠️ Выберите хотя бы один эмодзи")
        else:
            try:
                if show_messages_breakdown and include_replies:
                    _display_messages_breakdown(
                        server_url, personal_token, 
                        st.session_state.post_id_v2, 
                        emoji_filter=selected_emojis_v2
                    )
                else:
                    with st.spinner("🔄 Получение данных пользователей..."):
                        emoji_data = process_reactions(
                            server_url, 
                            personal_token, 
                            st.session_state.reactions_v2,
                            emoji_filter=selected_emojis_v2
                        )
                    
                    st.success(f"✅ Обработано эмодзи: {len(emoji_data)}")
                    st.subheader("📊 Результат")
                    st.json(emoji_data)
            
            except Exception as e:
                st.error(f"❌ Ошибка при обработке: {str(e)}")
