"""
Вкладка для массовой рассылки сообщений пользователям
"""
import os
import time
import streamlit as st
from mattermost_api import broadcast_message
from ai_helper import improve_message_text


def render_broadcast_tab(server_url: str, personal_token: str, product_name: str = "Mattermost"):
    """Отображает вкладку массовой рассылки сообщений"""
    st.markdown("**Режим:** Массовая рассылка личных сообщений")
    st.markdown("Отправляет личные сообщения списку пользователей от вашего имени")
    
    # Получаем информацию о текущем пользователе (sender_id)
    if 'sender_id' not in st.session_state and personal_token:
        with st.spinner("Получаем информацию о вашем аккаунте..."):
            try:
                import requests
                api_url = f"{server_url.rstrip('/')}/api/v4/users/me"
                headers = {"Authorization": f"Bearer {personal_token}"}
                response = requests.get(api_url, headers=headers, timeout=10)
                response.raise_for_status()
                user_data = response.json()
                st.session_state.sender_id = user_data.get('id')
                st.session_state.sender_username = user_data.get('username')
            except Exception as e:
                st.error(f"Не удалось получить информацию об аккаунте: {str(e)}")
    
    if 'sender_username' in st.session_state:
        st.info(f"📤 Отправитель: **@{st.session_state.sender_username}**")
    
    st.divider()
    
    # Список получателей
    st.subheader("1️⃣ Список получателей")
    
    recipients_text = st.text_area(
        "Введите список email или username",
        placeholder='user1@example.com\nuser2@example.com\n\nили\n\n["user1@example.com","user2@example.com"]',
        height=150,
        help="Поддерживаются форматы: список в столбик (по одному на строку) или JSON-массив",
        key="recipients_input"
    )
    
    # Умный парсинг списка получателей
    recipients_list = []
    if recipients_text:
        text = recipients_text.strip()
        
        # Проверяем, это JSON-массив или обычный список
        if text.startswith('[') and text.endswith(']'):
            # Пытаемся распарсить как JSON
            try:
                import json
                recipients_list = json.loads(text)
                # Убеждаемся, что это список строк
                recipients_list = [str(item).strip() for item in recipients_list if item]
            except json.JSONDecodeError:
                st.error("Ошибка парсинга JSON. Проверьте формат списка.")
        else:
            # Парсим как обычный список (по одному на строку)
            recipients_list = [line.strip() for line in text.split('\n') if line.strip()]
        
        if recipients_list:
            st.success(f"Найдено получателей: **{len(recipients_list)}**")
        
        with st.expander("👥 Просмотр списка получателей"):
            for i, recipient in enumerate(recipients_list, 1):
                st.text(f"{i}. {recipient}")
    
    st.divider()
    
    # Сообщение
    st.subheader("2️⃣ Текст сообщения")
    
    # Инициализируем хранилище для улучшенного текста
    if 'ai_improved_text' not in st.session_state:
        st.session_state.ai_improved_text = None
    if 'show_ai_result' not in st.session_state:
        st.session_state.show_ai_result = False
    
    message_text = st.text_area(
        "Напишите сообщение для отправки",
        placeholder="Введите текст сообщения...",
        height=200,
        help="Это сообщение будет отправлено в личные сообщения каждому получателю",
        key="message_text_input"
    )
    
    # AI улучшение текста
    if message_text:
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("✨ Улучшить с AI", help="Улучшить текст сообщения с помощью AI", key="improve_ai_btn"):
                openai_api_key = os.getenv("OPENAI_API_KEY")
                
                if not openai_api_key:
                    st.error("🔑 Не найден API ключ OpenAI. Установите переменную окружения OPENAI_API_KEY")
                else:
                    with st.spinner("🤖 AI улучшает ваше сообщение..."):
                        try:
                            improved_text = improve_message_text(message_text, openai_api_key)
                            st.session_state.ai_improved_text = improved_text
                            st.session_state.show_ai_result = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ошибка при улучшении текста: {str(e)}")
    
    # Показываем результат AI-улучшения
    if st.session_state.show_ai_result and st.session_state.ai_improved_text:
        st.markdown("---")
        st.markdown("### 🤖 AI-улучшенная версия")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("**📋 Markdown (для копирования)**")
            # Используем уникальный ключ с timestamp для обновления при каждом изменении
            unique_key = f"ai_improved_markdown_{int(time.time() * 1000)}"
            st.text_area(
                "Улучшенный текст",
                value=st.session_state.ai_improved_text,
                height=250,
                key=unique_key,
                label_visibility="collapsed"
            )
            
            # Кнопка закрытия
            if st.button("❌ Закрыть", help="Скрыть результат AI", key="close_ai_btn"):
                st.session_state.show_ai_result = False
                st.session_state.ai_improved_text = None
                st.rerun()
        
        with col_right:
            st.markdown("**👁️ Предпросмотр (как в Mattermost)**")
            # Рендерим markdown напрямую без лишних контейнеров
            st.markdown(st.session_state.ai_improved_text)
        
        st.markdown("---")
    
    # Предпросмотр
    if message_text:
        with st.expander("👁️ Предпросмотр сообщения"):
            st.markdown(message_text)
    
    st.divider()
    
    # Отправка
    st.subheader("3️⃣ Отправка")
    
    if not recipients_list:
        st.warning("Введите список получателей")
    elif not message_text:
        st.warning("Напишите текст сообщения")
    elif 'sender_id' not in st.session_state:
        st.error("Не удалось получить информацию об аккаунте. Проверьте токен.")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            confirm_send = st.checkbox(
                "Подтвердить отправку",
                value=False,
                help="Отметьте, чтобы активировать кнопку отправки",
                key="confirm_send_checkbox"
            )
        
        with col2:
            send_button = st.button(
                f"✉️ Отправить {len(recipients_list)} сообщений",
                disabled=not confirm_send,
                type="primary",
                key="send_messages_btn"
            )
        
        if send_button:
            with st.spinner("Отправляем сообщения..."):
                try:
                    result = broadcast_message(
                        server_url=server_url,
                        token=personal_token,
                        sender_id=st.session_state.sender_id,
                        recipients=recipients_list,
                        message=message_text
                    )
                    
                    # Показываем результаты
                    st.success("🎉 Рассылка завершена!")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Всего", result['total'])
                    col2.metric("✅ Успешно", result['successful'])
                    col3.metric("❌ Ошибок", result['failed'])
                    
                    # Детальные результаты
                    if result['failed'] > 0:
                        with st.expander("❌ Ошибки при отправке", expanded=True):
                            for res in result['results']:
                                if not res['success']:
                                    st.error(f"**{res['recipient']}**: {res['error']}")
                    
                    # Успешные отправки
                    if result['successful'] > 0:
                        with st.expander("✅ Успешно отправлено"):
                            for res in result['results']:
                                if res['success']:
                                    st.text(f"• {res['recipient']}")
                    
                except Exception as e:
                    st.error(f"Ошибка при отправке сообщений: {str(e)}")
    
    # Инструкции
    with st.expander("ℹ️ Как использовать"):
        st.markdown("""
        ### Инструкция по использованию
        
        1. **Получите список пользователей**
           - Перейдите в другую вкладку (Выгрузить тред / Выгрузить канал)
           - Получите список пользователей с нужными реакциями
           - Скопируйте список email/username
        
        2. **Вставьте список**
           - Вставьте список в поле "Список получателей"
           - Поддерживаемые форматы:
             * По одному на строку: `user1@example.com\\nuser2@example.com`
             * JSON-массив: `["user1@example.com","user2@example.com"]`
        
        3. **Напишите сообщение**
           - Введите текст в поле "Текст сообщения"
           - Проверьте предпросмотр
        
        4. **Отправьте**
           - Отметьте чекбокс "Подтвердить отправку"
           - Нажмите кнопку "Отправить сообщения"
        
        **Примечание:** Сообщения отправляются в личные сообщения (Direct Messages) от вашего имени.
        """)
