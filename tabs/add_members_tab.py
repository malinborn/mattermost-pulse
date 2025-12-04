"""
Вкладка для добавления участников в канал
"""
import json
import streamlit as st
from mattermost_api import resolve_channel_id, get_channel_info, add_members_to_channel


def render_add_members_tab(server_url: str, personal_token: str, product_name: str = "Mattermost"):
    """Отображает вкладку добавления участников в канал"""
    st.markdown("**Режим:** Добавление участников в канал")
    st.markdown("Добавьте пользователей в канал по их email адресам")
    
    channel_input = st.text_input(
        "URL или ID канала",
        placeholder=f"https://{product_name.lower()}-server.com/team/channels/channel_id",
        help="Полный URL канала или только его ID",
        key="add_members_channel_input"
    )
    
    st.markdown("### 📧 Список email адресов")
    st.markdown("""
    Введите email адреса в одном из форматов:
    - **Список столбиком** — каждый email на новой строке
    - **JSON** — объект с ключами и массивами email (дубликаты будут удалены автоматически)
    """)
    
    emails_input = st.text_area(
        "Email адреса",
        height=200,
        placeholder="""Формат 1 (список):
i.ivanov@example.com
p.divanov@example.com

Формат 2 (JSON):
{"team1": ["a@example.com", "b@example.com"], "team2": ["b@example.com", "c@example.com"]}""",
        help="Введите email адреса столбиком или в формате JSON",
        key="add_members_emails_input"
    )
    
    if emails_input:
        emails, parse_error = _parse_emails(emails_input)
        
        if parse_error:
            st.error(f"❌ Ошибка парсинга: {parse_error}")
        else:
            st.success(f"✅ Распознано уникальных email: **{len(emails)}**")
            
            with st.expander("👀 Просмотр списка email", expanded=False):
                for idx, email in enumerate(sorted(emails), 1):
                    st.text(f"{idx}. {email}")
    
    if st.button("➕ Добавить участников в канал", type="primary", use_container_width=True, key="add_members_submit"):
        if not server_url:
            st.error(f"⚠️ Укажите URL сервера {product_name}")
        elif not personal_token:
            st.error("⚠️ Укажите личный токен доступа")
        elif not channel_input:
            st.error("⚠️ Укажите URL или ID канала")
        elif not emails_input:
            st.error("⚠️ Введите email адреса")
        else:
            emails, parse_error = _parse_emails(emails_input)
            
            if parse_error:
                st.error(f"❌ Ошибка парсинга: {parse_error}")
            elif not emails:
                st.error("⚠️ Не найдено ни одного email адреса")
            else:
                _add_members(server_url, personal_token, channel_input, emails)


def _parse_emails(input_text: str) -> tuple[list[str], str | None]:
    """
    Парсит входной текст и извлекает уникальные email.
    
    Поддерживает:
    - Список email столбиком
    - JSON с ключами и массивами email
    
    Returns:
        tuple: (список уникальных email, сообщение об ошибке или None)
    """
    input_text = input_text.strip()
    
    if not input_text:
        return [], None
    
    # Пробуем парсить как JSON
    if input_text.startswith('{'):
        try:
            data = json.loads(input_text)
            
            if not isinstance(data, dict):
                return [], "JSON должен быть объектом с ключами"
            
            all_emails = set()
            for key, value in data.items():
                if isinstance(value, list):
                    for email in value:
                        if isinstance(email, str) and '@' in email:
                            all_emails.add(email.strip().lower())
                elif isinstance(value, str) and '@' in value:
                    all_emails.add(value.strip().lower())
            
            return list(all_emails), None
            
        except json.JSONDecodeError as e:
            return [], f"Некорректный JSON: {str(e)}"
    
    # Парсим как список столбиком
    lines = input_text.split('\n')
    emails = set()
    
    for line in lines:
        line = line.strip()
        if line and '@' in line:
            emails.add(line.lower())
    
    return list(emails), None


def _add_members(server_url: str, personal_token: str, channel_input: str, emails: list[str]):
    """Добавление пользователей в канал"""
    with st.spinner("🔄 Подготовка..."):
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
            
        except ValueError as e:
            st.error(f"❌ Ошибка: {str(e)}")
            return
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
            return
    
    # Добавляем пользователей
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner(f"➕ Добавление {len(emails)} пользователей в канал..."):
        result = add_members_to_channel(server_url, personal_token, channel_id, emails)
    
    progress_bar.progress(100)
    status_text.empty()
    
    # Отображаем результаты
    _display_results(result)


def _display_results(result: dict):
    """Отображение результатов добавления"""
    st.divider()
    st.subheader("📊 Результаты")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего", result['total'])
    with col2:
        st.metric("✅ Добавлено", result['successful'], delta=None)
    with col3:
        st.metric("ℹ️ Уже в канале", result['already_member'], delta=None)
    with col4:
        st.metric("❌ Ошибки", result['failed'], delta=None, delta_color="inverse")
    
    # Детализация
    if result['results']:
        # Успешные
        successful_results = [r for r in result['results'] if r['success'] and not r.get('error')]
        if successful_results:
            with st.expander(f"✅ Успешно добавлены ({len(successful_results)})", expanded=False):
                for r in successful_results:
                    st.text(r['email'])
        
        # Уже в канале
        already_in_channel = [r for r in result['results'] if r.get('error') == 'Уже в канале']
        if already_in_channel:
            with st.expander(f"ℹ️ Уже были в канале ({len(already_in_channel)})", expanded=False):
                for r in already_in_channel:
                    st.text(r['email'])
        
        # Ошибки
        failed_results = [r for r in result['results'] if not r['success']]
        if failed_results:
            with st.expander(f"❌ Ошибки ({len(failed_results)})", expanded=True):
                for r in failed_results:
                    st.markdown(f"- `{r['email']}` — {r.get('error', 'Неизвестная ошибка')}")
