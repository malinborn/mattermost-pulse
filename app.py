"""
Mattermost Reactions Exporter
Экспортирует реакции из постов Mattermost в YAML-формат.
"""
import os
import streamlit as st
import extra_streamlit_components as stx
from tabs.thread_tab import render_thread_tab
from tabs.channel_tab import render_channel_tab
from tabs.broadcast_tab import render_broadcast_tab
from tabs.users_tab import render_users_tab


def main():
    st.set_page_config(
        page_title="Mattermost Reactions Exporter",
        page_icon="📊",
        layout="wide"
    )
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Настройки подключения")
        
        # Инициализируем Cookie Manager
        # ВАЖНО: Используем session_state, а не cache_resource!
        # cache_resource сделал бы менеджер общим для всех пользователей (это дыра в безопасности).
        # session_state создает уникальный менеджер для каждого пользователя.
        if 'cookie_manager' not in st.session_state:
            st.session_state.cookie_manager = stx.CookieManager()

        cookie_manager = st.session_state.cookie_manager
        
        # Проверяем переменную среды для токена и других настроек
        env_token = os.getenv("MATTERMOST_PERSONAL_TOKEN", "")
        env_server_url = os.getenv("MATTERMOST_URL", "")
        product_name = os.getenv("PRODUCT_NAME", "Mattermost")
        
        # Получаем сохраненные значения из кук
        # ВАЖНО: get() возвращает куки, но может вернуть None пока они грузятся
        cookies = cookie_manager.get_all()
        
        # --- FIX: Логика синхронизации ---
        # Мы должны один раз при старте сессии перенести данные из кук в поля ввода.
        # Иначе Streamlit будет использовать пустое значение первого прогона.
        
        if "cookies_loaded" not in st.session_state:
            st.session_state.cookies_loaded = False
            
        # Если куки подгрузились, а мы их еще не применили -> применяем
        if cookies and not st.session_state.cookies_loaded:
            mm_url = cookies.get("mm_url")
            mm_token = cookies.get("mm_token")
            
            if mm_url is not None:
                st.session_state["server_url_input"] = str(mm_url)
            
            if mm_token is not None:
                st.session_state["personal_token_input"] = str(mm_token)
                
            st.session_state.cookies_loaded = True
            # Делаем rerun, чтобы инпуты сразу обновились с новыми значениями
            st.rerun()
            
        # --- Конец FIX ---
        
        ls_token = cookies.get("mm_token") if cookies else ""
        ls_url = cookies.get("mm_url") if cookies else ""
        
        # Если куки еще не загрузились, считаем их пустыми (избегаем None)
        if ls_token is None: ls_token = ""
        if ls_url is None: ls_url = ""
        
        # Убеждаемся, что это строки (защита от TypeError)
        ls_token = str(ls_token)
        ls_url = str(ls_url)
        
        # Определяем дефолтные значения: Env Var > Cookies > Empty
        default_url = env_server_url if env_server_url else ls_url
        default_token = env_token if env_token else ls_token
        
        server_url = st.text_input(
            f"URL сервера {product_name}",
            value=default_url,
            placeholder=f"https://your-{product_name.lower()}-server.com",
            help=f"URL сервера {product_name} (с https://)",
            key="server_url_input"
        )
        
        # Сохраняем в куки при изменении с защитными флагами
        if server_url and server_url != ls_url:
            cookie_manager.set(
                "mm_url", 
                server_url, 
                key="set_url_cookie",
                max_age=86400 * 30,  # 30 дней
                same_site='Strict'
            )
        
        personal_token = st.text_input(
            "Личный токен доступа",
            value=default_token,
            type="password",
            placeholder="Введите ваш личный токен",
            help=f"Личный токен для авторизации в {product_name} API (или установите переменную среды MATTERMOST_PERSONAL_TOKEN)",
            key="personal_token_input"
        )

        # Сохраняем токен в куки с максимальной защитой
        if personal_token and personal_token != ls_token:
            cookie_manager.set(
                "mm_token", 
                personal_token, 
                key="set_token_cookie",
                max_age=86400 * 30,  # 30 дней
                same_site='Strict'
            )
        
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
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Выгрузить тред", "📊 Выгрузить канал", "✉️ Рассылка", "👥 Пользователи канала"])
    
    with tab1:
        render_thread_tab(server_url, personal_token, product_name)
    
    with tab2:
        render_channel_tab(server_url, personal_token, product_name)
    
    with tab3:
        render_broadcast_tab(server_url, personal_token, product_name)
    
    with tab4:
        render_users_tab(server_url, personal_token, product_name)


if __name__ == "__main__":
    main()
