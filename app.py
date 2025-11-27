"""
Mattermost Reactions Exporter
Экспортирует реакции из постов Mattermost в YAML-формат.
"""
import os
import streamlit as st
from streamlit_local_storage import LocalStorage
from tabs.thread_tab import render_thread_tab
from tabs.channel_tab import render_channel_tab
from tabs.broadcast_tab import render_broadcast_tab


def main():
    st.set_page_config(
        page_title="Mattermost Reactions Exporter",
        page_icon="📊",
        layout="wide"
    )
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Настройки подключения")
        
        # Инициализируем Local Storage
        ls = LocalStorage()
        
        # Проверяем переменную среды для токена и других настроек
        env_token = os.getenv("MATTERMOST_PERSONAL_TOKEN", "")
        env_server_url = os.getenv("MATTERMOST_URL", "")
        product_name = os.getenv("PRODUCT_NAME", "Mattermost")
        
        # Получаем сохраненные значения (если нет переменных окружения)
        # ВАЖНО: ls.getItem может вернуть None при первом рендере
        ls_token = ls.getItem("mm_token") or ""
        ls_url = ls.getItem("mm_url") or ""
        
        # Определяем дефолтные значения: Env Var > Local Storage > Empty
        default_url = env_server_url if env_server_url else ls_url
        default_token = env_token if env_token else ls_token
        
        server_url = st.text_input(
            f"URL сервера {product_name}",
            value=default_url,
            placeholder=f"https://your-{product_name.lower()}-server.com",
            help=f"URL сервера {product_name} (с https://)",
            key="server_url_input"
        )
        
        # Сохраняем в LS при изменении (если значение отличается от сохраненного)
        if server_url and server_url != ls_url:
            ls.setItem("mm_url", server_url)
        
        personal_token = st.text_input(
            "Личный токен доступа",
            value=default_token,
            type="password",
            placeholder="Введите ваш личный токен",
            help=f"Личный токен для авторизации в {product_name} API (или установите переменную среды MATTERMOST_PERSONAL_TOKEN)",
            key="personal_token_input"
        )

        # Сохраняем токен в LS
        if personal_token and personal_token != ls_token:
            ls.setItem("mm_token", personal_token)
        
        with st.expander("ℹ️ Как получить токен?"):
            st.markdown(f"""
            1. Нажмите на фото профиля (справа сверху).
            2. Выберите **Profile** -> **Security**.
            3. В **Personal Access Tokens** нажмите **Create Token**.
            4. Введите описание и **Save**.
            5. Скопируйте токен.
            
            *Если нет раздела, обратитесь к администратору.*
            """)

    # Main area
    st.title(f"📊 {product_name} post analyzer")
    st.markdown(f"Получает реакции из поста или канала {product_name} и показывает данные в удобном формате")
    
    # Сохраняем в session_state для использования во всех вкладках
    st.session_state.server_url = server_url
    st.session_state.personal_token = personal_token
    st.session_state.product_name = product_name
    
    st.divider()
    
    # Вкладки
    tab1, tab2, tab3 = st.tabs(["📥 Выгрузить тред", "📊 Выгрузить канал", "✉️ Рассылка"])
    
    with tab1:
        render_thread_tab(server_url, personal_token, product_name)
    
    with tab2:
        render_channel_tab(server_url, personal_token, product_name)
    
    with tab3:
        render_broadcast_tab(server_url, personal_token, product_name)


if __name__ == "__main__":
    main()
