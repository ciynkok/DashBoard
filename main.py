import streamlit as st
import pandas as pd
import re
import pymorphy3

morph = pymorphy3.MorphAnalyzer() # Для фильтра по ключевому слову

def highlight_all(text, query, color):
    if not isinstance(text, str):
        return ""

    # леммы запроса
    query_words = re.findall(r"[а-яА-ЯёЁ]+", query.lower())
    query_lemmas = {morph.parse(w)[0].normal_form for w in query_words}

    def replacer(match):
        word = match.group(0)
        lemma = morph.parse(word.lower())[0].normal_form
        if lemma in query_lemmas:
            return f'<mark style="background-color:{color}">{word}</mark>'
        return word

    return re.sub(r"[а-яА-ЯёЁ]+", replacer, text)

def lemmatize(text):
    return {
        morph.parse(w)[0].normal_form
        for w in re.findall(r"[а-яА-ЯёЁ]+", str(text).lower())
    }

def keywords_search(text, query):
    text_lemmas = lemmatize(text)
    query_lemmas = lemmatize(query)
    return query_lemmas.issubset(text_lemmas)

# ---- Заголовок ----

st.set_page_config(page_title="BI Дашборд Отзывов", layout="wide")
st.title("📊 BI-Дашборд: Аналитика отзывов")
# ---- Загрузка данных ----
@st.cache_data
def load_data():
    doctors = pd.read_csv("doctors.csv")
    reviews = pd.read_csv("reviews.csv")
    return doctors, reviews

doctors, reviews = load_data()

st.sidebar.header("Фильтры врачей")

name_query = st.sidebar.text_input(
    "Имя:",
    value=""
)

specialities = st.sidebar.text_input("Специальность:", value="")

degree = st.sidebar.multiselect(
    "Ученая степень:",
    options=doctors["Ученая степень"].unique(),
    default=doctors["Ученая степень"].unique()
)

work_places = st.sidebar.text_input(
    "Учереждение:",
    value=""
)

# Фильтр по минимальному стажу
min_exp = st.sidebar.number_input(
    "Минимальный стаж (лет):",
    min_value=0,
    max_value=int(doctors["Сумма Стаж"].max()),
    value=0,
    step=1
)

# Фильтр по минимальному рейтингу
min_rating = st.sidebar.number_input(
    "Минимальный рейтинг:",
    min_value=float(0),
    max_value=doctors["Сумма Рейтинг"].max(),
    value=float(0),
    step=doctors["Сумма Рейтинг"].max() / 10
)

search_text = st.text_input("Поиск по отзывам (введите ключевые слова):")

filtered_reviews = reviews.copy()
def fast_and(lemmas, query):
    return lemmatize(query).issubset(lemmas)

if search_text:
    filtered_reviews = filtered_reviews[filtered_reviews["lemmas"].apply(lambda x: fast_and(set(x[2:-2].split("', '")), search_text))]

filtered = doctors.copy()
# фильтр по имени врача (поиск подстроки)
if name_query.strip() != "":
    filtered = filtered[filtered["Имя врача"].str.contains(name_query, case=False, na=False)]

#if specialities.strip() != "": filtered_reviews = reviews[reviews["Отзыв"].str.contains(specialities, case=False, na=False)]

if specialities: 
    filtered_reviews = filtered_reviews[filtered_reviews["lemmas"].apply(lambda x: fast_and(set(x[2:-2].split("', '")), specialities))]

if work_places.strip() != "":
    filtered = filtered[filtered["Работает в клиниках"].str.contains(work_places, case=False, na=False)]

# ---------------- Применение фильтров ----------------
if len(filtered["Ученая степень"].isin(degree).unique()) != 1 or min_exp != 0 or min_rating != 0: #len(filtered["Ученая степень"].isin(degree).unique()) != 1
    filtered = filtered[
        (filtered["Ученая степень"].isin(degree)) &
        (filtered["Сумма Стаж"] >= min_exp) &
        (filtered["Сумма Рейтинг"] >= min_rating)
    ]


# ---------------- Кнопки "Показать отзывы" ----------------

output_placeholder = st.empty()

rows_per_page = st.sidebar.number_input(
    "Врачей на странице:",
    min_value=5,
    max_value=100,
    value=10,
    step=5
)

def gen_pagination(filt):
    total_rows = len(filt)
    total_pages = (total_rows - 1) // rows_per_page + 1

    st.subheader(f"Страниц найдено : {total_pages}")

    if total_pages <= 0:
        return

    if "page" not in st.session_state:
        st.session_state.page = 1

    # Ограничить в пределах
    st.session_state.page = min(max(1, st.session_state.page), total_pages)

    # ---------- РАСЧЁТ ОКНА ПАГИНАЦИИ ----------
    window = 9  # максимальное число отображаемых страниц
    half = window // 2

    if total_pages <= window:
        pages = list(range(1, total_pages + 1))
    else:
        start = max(1, st.session_state.page - half)
        end = min(total_pages, start + window - 1)

        # Коррекция начала окна
        if end - start < window - 1:
            start = max(1, end - window + 1)

        pages = list(range(start, end + 1))


    # ---------- ОТРИСОВКА ПАГИНАЦИИ ----------
    col_prev_up, col_prev, col_pages, col_next, col_next_up = st.columns([1, 1, 10, 1, 1])

    # ← НАЗАД
    with col_prev:
        st.markdown("<div class='arrow-btn'>", unsafe_allow_html=True)
        if st.button("←", key="prev") and st.session_state.page > 1:
            st.session_state.page -= 1 
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_prev_up:
        st.markdown("<div class='arrow-btn'>", unsafe_allow_html=True)
        if st.button("←←", key="prev_up") and st.session_state.page != 1:
            st.session_state.page -= window 
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Номера страниц
    with col_pages:
        cols = st.columns(len(pages))
        for idx, p in enumerate(pages):

            if p == st.session_state.page:
                cols[idx].markdown("<div>", unsafe_allow_html=True)
                if cols[idx].button(f"->{str(p)}", key=f"page_{p}"):
                    pass
                cols[idx].markdown("</div>", unsafe_allow_html=True)
                
            else:
                cols[idx].markdown("<div>", unsafe_allow_html=True)
                if cols[idx].button(str(p), key=f"page_{p}"):
                    st.session_state.page = p
                    st.rerun()
                    
                cols[idx].markdown("</div>", unsafe_allow_html=True)

    # → ВПЕРЁД
    with col_next:
        st.markdown("<div class='arrow-btn'>", unsafe_allow_html=True)
        if st.button("→", key="next") and st.session_state.page < total_pages:
            st.session_state.page += 1 
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_next_up:
        st.markdown("<div class='arrow-btn'>", unsafe_allow_html=True)
        if st.button("→→", key="next_up") and st.session_state.page < total_pages:
            st.session_state.page += window 
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


    # ---------- Срез данных текущей страницы ----------
    start = (st.session_state.page - 1) * rows_per_page
    end = start + rows_per_page

    filtered_page = filt.iloc[start:end]

    return filtered_page



if search_text or specialities:

    st.subheader("📋 Список отзывов")

    filtered = filtered_reviews.merge(filtered, on="Ссылка", how="left")
    filtered = filtered.sort_values(by=["Имя врача"])


    filtered["Имя врача"] = filtered.groupby("Ссылка")["Имя врача"] \
        .transform(lambda x: [x.iloc[0]] + [""] * (len(x)-1))

    # --- То же для специальности ---
    # Перед этим сохраняем специальность (у врача она одна)
    filtered["Специальность"] = filtered.groupby("Ссылка")["Специальность"] \
        .transform(lambda x: [x.iloc[0]] + [""] * (len(x)-1))

    filtered["Ссылка"] = filtered.groupby("Ссылка")["Ссылка"] \
        .transform(lambda x: [x.iloc[0]] + [""] * (len(x)-1))

    filtered_page = gen_pagination(filtered)


    header_cols = st.columns([2, 2, 2, 1, 6])

    with header_cols[0]:
        st.markdown("**Ссылка**")
    with header_cols[1]:
        st.markdown("**Имя врача**")
    #with header_cols[2]:
    #   st.markdown("**Стаж (лет)**")
    with header_cols[2]:
        st.markdown("**Специальность**")
    with header_cols[3]:
        st.markdown("**Оценка**")
    with header_cols[4]:
        st.markdown("**Отзывы**")
    #with header_cols[4]:
    #    st.markdown("**Клиники**")
    #with header_cols[5]:
    #    st.markdown("**Отзывов**")
    #with header_cols[6]:
    #    st.markdown("**Рейтинг**")

    if filtered_page is not None:
        for idx, row in filtered_page.iterrows():
            with st.container():
                st.markdown("""
                <div style="padding:10px; border-bottom:1px solid #ccc;">
                """, unsafe_allow_html=True)

                columns = st.columns([2, 2, 2, 1, 6])
                with columns[0]:
                    st.write(row['Ссылка'])
                with columns[1]:
                    if row["Имя врача"]:
                        st.write(f"**{row['Имя врача']}**")
                        with st.expander("Подробнее о враче"):
                            st.write(f"**Стаж:** {row.get('Сумма Стаж', '—')} лет")
                            st.write(f"**Ученая степень:** {row.get('Ученая степень', '—')}")
                            st.write(f"**Учереждения:** {row.get('Работает в клиниках', '—')}")
                            st.write(f"**Отзывов:** {row.get('Сумма Отзывов', '—')}")
                            st.write(f"**Рейтинг:** {row.get('Сумма Рейтинг', '—')}")
                with columns[2]:
                    st.write(row["Специальность"])
                with columns[3]:
                    st.write(row.get("Рейтинг_1", "—"))
                with columns[4]:
                    if search_text.strip() == "" and specialities.strip() == "":
                        st.write(row["Отзыв"])
                    elif search_text.strip() != "" and specialities.strip() == "":
                        highlighted = highlight_all(row['Отзыв'], search_text, 'yellow')
                        st.markdown(highlighted, unsafe_allow_html=True)
                    elif specialities.strip() != "" and search_text.strip() == "":
                        highlighted = highlight_all(row['Отзыв'], specialities, '#B3E5FC')
                        st.markdown(highlighted, unsafe_allow_html=True)
                    else:
                        highlighted = highlight_all(row['Отзыв'], search_text, 'yellow')
                        highlighted = highlight_all(highlighted, specialities, '#B3E5FC')
                        st.markdown(highlighted, unsafe_allow_html=True)
                    with st.expander("Подробнее об отзыве"):
                        st.write(f"**Имя клиента:** {row.get('Имя клиента', '—')}")
                        st.write(f"**Дата отзыва:** {row.get('Дата отзыва', '—')}")
                        st.write(f"**Оценка:** {row.get('Рейтинг_1', '—')}")
                        st.write(f"**Подтверждение записи:** {row.get('Подтверждение записи', '—')}")

                st.markdown("</div>", unsafe_allow_html=True)
else:

    filtered_page = gen_pagination(filtered)

    st.subheader("📋 Список врачей")

    st.divider()

    output_placeholder = st.empty()

    if filtered_page is not None:
        for idx, row in filtered_page.iterrows():
            columns = st.columns([3, 3, 2, 2, 4, 2, 2, 2])

            with columns[0]:
                st.write(row['Ссылка'])
            with columns[1]:
                st.write(f"**{row['Имя врача']}**")
            with columns[2]:
                st.write(f"**Стаж:** {row.get('Сумма Стаж', '—')} лет")
            with columns[3]:
                st.write(f"**Ученая степень:** {row.get('Ученая степень', '—')}")
            with columns[4]:
                st.write(f"**Учереждения:** {row.get('Работает в клиниках', '—')}")
            with columns[5]:
                st.write(f"**Отзывов:** {row.get('Сумма Отзывов', '—')}")
            with columns[6]:
                st.write(f"**Рейтинг:** {row.get('Сумма Рейтинг', '—')}")
            with columns[7]:
                if st.button("Отзывы", key=f"rev_{row['Ссылка']}"):
                    dr_reviews = reviews[reviews["Ссылка"] == row["Ссылка"]][['Рейтинг_1', 'Отзыв']]
                    
                    with output_placeholder.container():
                        st.markdown(f"### 📝 Отзывы о враче: {row['Имя врача']}")

                        st.dataframe(
                            dr_reviews,
                            width='stretch',
                            column_config={
                                "Рейтинг": st.column_config.NumberColumn("Рейтнг_1", width="50px"),
                                "Отзыв": st.column_config.TextColumn("Отзыв"),
                            }
                        )

                        st.divider()

