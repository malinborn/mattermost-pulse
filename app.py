"""
Mattermost Reactions Exporter
Экспортирует реакции из постов Mattermost в YAML-формат.
"""
import os
import streamlit as st
from tabs.thread_tab import render_thread_tab
from tabs.channel_tab import render_channel_tab
from tabs.broadcast_tab import render_broadcast_tab


def main():
    st.set_page_config(
        page_title="Mattermost Reactions Exporter",
        page_icon="📊",
        layout="centered"
    )
    
    st.title("📊 Mattermost post analyzer")
    st.markdown("Получает реакции из поста или канала Mattermost и показывает данные в удобном формате")
    
    with st.expander("ℹ️ Как получить токен доступа (Personal Access Token)?"):
        st.markdown("""
        1. Нажмите на свое фото профиля в правом верхнем углу Mattermost.
        2. Выберите **Profile** (Профиль).
        3. Перейдите в раздел **Security** (Безопасность).
        4. Найдите раздел **Personal Access Tokens** и нажмите **Create Token**.
        5. Введите описание токена и нажмите **Save**.
        6. Скопируйте полученный токен и вставьте его в поле ниже.
        
        *Если вы не видите раздел Personal Access Tokens, обратитесь к администратору сервера.*
        """)
    
    # Проверяем переменную среды для токена
    env_token = os.getenv("MATTERMOST_PERSONAL_TOKEN", "")
    
    # Общие настройки подключения
    st.subheader("Настройки подключения")
    
    server_url = st.text_input(
        "URL сервера Mattermost",
        value="https://dodobrands.loop.ru",
        placeholder="https://your-mattermost-server.com",
        help="URL сервера Mattermost (с https://)"
    )
    
    personal_token = st.text_input(
        "Личный токен доступа",
        value=env_token,
        type="password",
        placeholder="Введите ваш личный токен",
        help="Личный токен для авторизации в Mattermost API (или установите переменную среды MATTERMOST_PERSONAL_TOKEN)"
    )
    
    # Сохраняем в session_state для использования во всех вкладках
    st.session_state.server_url = server_url
    st.session_state.personal_token = personal_token
    
    st.divider()
    
    # Вкладки
    tab1, tab2, tab3 = st.tabs(["📥 Выгрузить тред", "📊 Выгрузить канал", "✉️ Рассылка"])
    
    with tab1:
        render_thread_tab(server_url, personal_token)
    
    with tab2:
        render_channel_tab(server_url, personal_token)
    
    with tab3:
        render_broadcast_tab(server_url, personal_token)


if __name__ == "__main__":
    main()
