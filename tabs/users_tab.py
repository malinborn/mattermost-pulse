"""
Вкладка для отображения пользователей канала
"""
import streamlit as st
import pandas as pd
from mattermost_api import resolve_channel_id, get_channel_members, get_channel_info


def render_users_tab(server_url: str, personal_token: str, product_name: str = "Mattermost"):
    """Отображает вкладку со списком пользователей канала"""
    st.markdown("**Режим:** Получение списка пользователей канала")
    st.markdown("Введите ссылку на канал, чтобы получить таблицу всех его участников")
    
    channel_input = st.text_input(
        "URL или ID канала",
        placeholder=f"https://{product_name.lower()}-server.com/team/channels/channel_id или просто channel_id",
        help="Полный URL канала или только его ID",
        key="users_channel_input"
    )
    
    if st.button("👥 Загрузить пользователей", type="primary", use_container_width=True, key="users_load"):
        if not server_url:
            st.error(f"⚠️ Укажите URL сервера {product_name}")
        elif not personal_token:
            st.error("⚠️ Укажите личный токен доступа")
        elif not channel_input:
            st.error("⚠️ Укажите URL или ID канала")
        else:
            _handle_load_users(server_url, personal_token, channel_input, product_name)


def _handle_load_users(server_url, personal_token, channel_input, product_name):
    """Обработка загрузки пользователей канала"""
    with st.spinner("🔄 Получение данных о пользователях канала..."):
        try:
            # Разрешаем URL/имя канала в channel_id
            channel_id, error = resolve_channel_id(server_url, personal_token, channel_input)
            
            if error:
                st.error(f"❌ {error}")
                return
            
            st.info(f"📝 Channel ID: `{channel_id}`")
            
            # Получаем информацию о канале
            channel_info = get_channel_info(server_url, personal_token, channel_id)
            channel_name = channel_info.get('display_name') or channel_info.get('name') or channel_id
            
            st.success(f"📢 Канал: **{channel_name}**")
            
            # Получаем список пользователей
            members = get_channel_members(server_url, personal_token, channel_id)
            
            if not members:
                st.warning("ℹ️ В канале нет пользователей или не удалось получить данные")
            else:
                st.success(f"✅ Найдено пользователей: {len(members)}")
                _display_users_table(members)
            
        except ValueError as e:
            st.error(f"❌ Ошибка: {str(e)}")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")


def _display_users_table(members):
    """Отображение таблицы пользователей"""
    st.subheader("📊 Список пользователей канала")
    
    # Формируем данные для таблицы
    table_data = []
    for idx, user in enumerate(members, start=1):
        email = user.get('email', '')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        username = user.get('username', '')
        position = user.get('position', '')
        
        # Формируем full name
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = username or email
        
        table_data.append({
            '№': idx,
            'Email': email,
            'Full Name': full_name,
            'Position': position
        })
    
    # Создаем DataFrame
    df = pd.DataFrame(table_data)
    
    # Отображаем таблицу
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            '№': st.column_config.NumberColumn(
                '№',
                width='small',
                help='Порядковый номер'
            ),
            'Email': st.column_config.TextColumn(
                'Email',
                width='medium',
                help='Email пользователя'
            ),
            'Full Name': st.column_config.TextColumn(
                'Full Name',
                width='medium',
                help='Полное имя пользователя'
            ),
            'Position': st.column_config.TextColumn(
                'Position',
                width='medium',
                help='Должность пользователя'
            )
        }
    )
    
    # Добавляем возможность скачать CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Скачать CSV",
        data=csv,
        file_name="channel_users.csv",
        mime="text/csv",
        use_container_width=True
    )
