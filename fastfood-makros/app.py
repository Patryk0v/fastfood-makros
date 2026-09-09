# app.py — Fastfood Makros: kafelki produktów + szczegółowa edycja ilości
# Wymaga: streamlit, pandas, numpy
# CSV: UTF-8/UTF-8-SIG, separator ';'
#
# Kolumny wymagane:
# 'Kategoria','Produkt','kJ_per_portion','kcal_per_portion',
# 'fat_per_portion','kwasy_per_portion','carbs_per_portion',
# 'sugar_per_portion','protein_per_portion','salt_per_portion'
#
# Opcjonalnie:
# 'price_pln'
# 'popularity'  -> jeśli istnieje, produkty są sortowane malejąco po popularności.
#                  jeśli nie istnieje, sortujemy malejąco po kcal.

import os
import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# KONFIGURACJA
# =========================================================

st.set_page_config(
    page_title="Fastfood Makros",
    page_icon="🍔",
    layout="wide"
)

LOCAL_PATH = r"C:\Users\PC\Desktop\Projekty\Tabela wartości\github\fastfood-makros\data\items_kfc.csv"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_PATH = os.path.join(BASE_DIR, "data", "items_kfc.csv")

DEFAULT_PATH = LOCAL_PATH if os.path.exists(LOCAL_PATH) else CLOUD_PATH

PRICE_COL = "price_pln"
POPULARITY_COL = "popularity"

REQUIRED = [
    "Kategoria",
    "Produkt",
    "kJ_per_portion",
    "kcal_per_portion",
    "fat_per_portion",
    "kwasy_per_portion",
    "carbs_per_portion",
    "sugar_per_portion",
    "protein_per_portion",
    "salt_per_portion",
]

NUMERIC_PER_PORTION = [
    "kJ_per_portion",
    "kcal_per_portion",
    "fat_per_portion",
    "kwasy_per_portion",
    "carbs_per_portion",
    "sugar_per_portion",
    "protein_per_portion",
    "salt_per_portion",
]

RWS = {
    "kcal": 2500,
    "protein_g": 60,
    "fat_g": 80,
    "carbs_g": 340,
}


# =========================================================
# DANE
# =========================================================

@st.cache_data
def load_csv(path_or_buffer):
    """Wczytuje CSV i czyści kolumny liczbowe."""
    df = pd.read_csv(path_or_buffer, sep=";", encoding="utf-8-sig")

    df.columns = (
        df.columns
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"Brakuje kolumn: {missing}\n"
            f"Dostępne kolumny: {list(df.columns)}"
        )

    for c in NUMERIC_PER_PORTION:
        s = (
            df[c]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("\xa0", "", regex=False)
            .str.replace(" ", "", regex=False)
        )
        df[c] = pd.to_numeric(s, errors="coerce")

    if PRICE_COL not in df.columns:
        df[PRICE_COL] = np.nan
    else:
        s = df[PRICE_COL].astype(str)
        s = s.str.replace(",", ".", regex=False)
        s = s.str.replace("\xa0", "", regex=False)
        s = s.str.replace(" ", "", regex=False)
        s = s.str.replace(r"[^0-9.\-()]", "", regex=True)
        s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
        s = s.replace({"": np.nan, ".": np.nan, "-": np.nan})
        df[PRICE_COL] = pd.to_numeric(s, errors="coerce")

    if POPULARITY_COL in df.columns:
        df[POPULARITY_COL] = pd.to_numeric(
            df[POPULARITY_COL],
            errors="coerce"
        )

    # Zapewniamy prosty, stabilny indeks liczbowy.
    df = df.reset_index(drop=True)

    return df


try:
    df = load_csv(DEFAULT_PATH)
except Exception as e:
    st.error(f"Problem z wczytaniem danych: {e}")
    st.stop()


# =========================================================
# HELPERY
# =========================================================

def qty_key(product_id: int) -> str:
    return f"product_qty::{product_id}"


def detail_qty_key(product_id: int) -> str:
    return f"detail_qty::{product_id}"


def price_key(product_id: int) -> str:
    return f"user_price::{product_id}"


def get_qty(product_id: int) -> float:
    return float(st.session_state.get(qty_key(product_id), 0.0))


def set_qty(product_id: int, value: float):
    """Ustawia ilość produktu i synchronizuje edytor szczegółowy."""
    value = max(0.0, min(99.0, float(value)))
    st.session_state[qty_key(product_id)] = value
    st.session_state[detail_qty_key(product_id)] = value


def add_one(product_id: int):
    current = get_qty(product_id)
    set_qty(product_id, current + 1.0)


def subtract_one(product_id: int):
    current = get_qty(product_id)
    set_qty(product_id, max(0.0, current - 1.0))


def reset_menu():
    for key in list(st.session_state.keys()):
        if (
            str(key).startswith("product_qty::")
            or str(key).startswith("detail_qty::")
            or str(key).startswith("user_price::")
        ):
            del st.session_state[key]

    st.session_state["search_product"] = ""
    st.session_state["selected_category"] = None


def selected_ids():
    ids = []
    for i in df.index:
        if get_qty(i) > 0:
            ids.append(i)
    return ids


def product_sort(frame: pd.DataFrame) -> pd.DataFrame:
    """Popularność malejąco; jeśli jej brak, kcal malejąco."""
    if POPULARITY_COL in frame.columns and frame[POPULARITY_COL].notna().any():
        return frame.sort_values(
            by=[POPULARITY_COL, "kcal_per_portion", "Produkt"],
            ascending=[False, False, True],
            na_position="last",
        )

    return frame.sort_values(
        by=["kcal_per_portion", "Produkt"],
        ascending=[False, True],
        na_position="last",
    )


def format_qty(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}".replace(".", ",")


def metric_value(value, digits=1, suffix=""):
    if pd.isna(value):
        return "—"
    return f"{value:.{digits}f}{suffix}"


def render_rws_bar(container, current, target, color, unit):
    target = float(target) if target and target > 0 else 1.0
    current = float(current)

    pct_fill = max(0.0, min(current / target, 1.0)) * 100.0
    pct_text = (current / target) * 100.0

    html = f"""
    <div class="rws-wrap">
        <div class="rws-track">
            <div
                class="rws-fill"
                style="width:{pct_fill:.1f}%; background:{color};"
            ></div>
        </div>
        <div class="rws-text">
            {current:.1f}{unit} / {target:.0f}{unit}
            ({pct_text:.0f}%)
        </div>
    </div>
    """
    container.markdown(html, unsafe_allow_html=True)


# =========================================================
# STAN
# =========================================================

if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = None

if "search_product" not in st.session_state:
    st.session_state["search_product"] = ""


# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }

    .small-muted {
        color: #777;
        font-size: 0.86rem;
    }

    .product-selected-title {
        text-align: center;
        font-size: 1rem;
        font-weight: 700;
        color: #777;
        margin-top: 0.15rem;
        margin-bottom: 0.1rem;
        line-height: 1.15;
        min-height: 2.3rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .product-selected-meta {
        text-align: center;
        color: #999;
        font-size: 0.8rem;
        margin-bottom: 0.2rem;
    }

    .selected-inline-name {
        min-height: 42px;
        border: 1px solid rgba(128,128,128,.22);
        background: rgba(128,128,128,.08);
        border-radius: 12px;
        color: #8a8a8a;
        font-weight: 700;
        display: flex;
        align-items: center;
        padding: 0 0.7rem;
        line-height: 1.1;
    }

    div[data-testid="stButton"] > button {
        border-radius: 12px;
        min-height: 42px;
        font-weight: 650;
    }

    .rws-wrap {
        margin-top: 6px;
    }

    .rws-track {
        background: #bcbcbc;
        border-radius: 8px;
        height: 10px;
        width: 100%;
    }

    .rws-fill {
        height: 10px;
        border-radius: 8px;
    }

    .rws-text {
        font-size: 0.85rem;
        margin-top: 4px;
        color: #777;
    }

    .summary-card {
        padding: 0.9rem 1rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 14px;
        margin-bottom: 0.65rem;
    }

    .summary-name {
        font-weight: 700;
        font-size: 1rem;
    }

    .summary-meta {
        color: #777;
        font-size: 0.85rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# NAGŁÓWEK
# =========================================================

title_col, reset_col = st.columns([5, 1])

with title_col:
    st.title("🍔 Fastfood Makros")
    st.caption(
        "Dodaj produkty, które zjadłeś. "
        "Kliknij kafelek produktu, aby dodać pierwszą porcję."
    )

with reset_col:
    st.write("")
    st.write("")
    if st.button(
        "🗑️ Wyczyść",
        use_container_width=True,
        help="Usuń wszystkie produkty z aktualnego menu",
    ):
        reset_menu()
        st.rerun()


# =========================================================
# WYSZUKIWARKA
# =========================================================

st.subheader("🔎 Znajdź produkt")

search_term = st.text_input(
    "Wpisz nazwę produktu",
    key="search_product",
    placeholder="Np. Zinger, frytki, strips...",
    label_visibility="collapsed",
)

search_term = search_term.strip()

if search_term:
    search_df = df[
        df["Produkt"]
        .astype(str)
        .str.contains(search_term, case=False, na=False)
    ].copy()

    search_df = product_sort(search_df)

    if search_df.empty:
        st.info("Nie znaleziono produktu o takiej nazwie.")
    else:
        st.caption(f"Znaleziono: {len(search_df)}")
        search_result_ids = search_df.index.tolist()

        # maksymalnie 4 kolumny
        for start in range(0, len(search_result_ids), 4):
            row_ids = search_result_ids[start:start + 4]
            cols = st.columns(4)

            for col, product_id in zip(cols, row_ids):
                row = df.loc[product_id]
                qty = get_qty(product_id)
                with col:
                    if qty <= 0:
                        if st.button(
                            f"{row['Produkt']}",
                            key=f"search_add::{product_id}",
                            use_container_width=True,
                        ):
                            set_qty(product_id, 1.0)
                            st.rerun()
                    else:
                        name_col, minus_col, qty_col, plus_col = st.columns([3.8, 1, 1, 1])

                        with name_col:
                            st.markdown(
                                f'<div class="selected-inline-name">{row["Produkt"]}</div>',
                                unsafe_allow_html=True,
                            )

                        with minus_col:
                            if st.button(
                                "−",
                                key=f"search_minus::{product_id}",
                                use_container_width=True,
                            ):
                                subtract_one(product_id)
                                st.rerun()

                        with qty_col:
                            st.button(
                                format_qty(qty),
                                key=f"search_qty_display::{product_id}",
                                disabled=True,
                                use_container_width=True,
                            )

                        with plus_col:
                            if st.button(
                                "+",
                                key=f"search_plus::{product_id}",
                                use_container_width=True,
                            ):
                                add_one(product_id)
                                st.rerun()

    st.divider()


# =========================================================
# KATEGORIE
# =========================================================

st.subheader("Kategorie")

categories = sorted(
    df["Kategoria"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

# 4 kategorie -> cztery kafelki.
# Jeśli kiedyś będzie więcej, automatycznie powstaną kolejne wiersze.
for start in range(0, len(categories), 4):
    row_categories = categories[start:start + 4]
    cols = st.columns(4)

    for col, category in zip(cols, row_categories):
        selected = st.session_state["selected_category"] == category

        label = (
            f"✓ {category}"
            if selected
            else f"{category}"
        )

        with col:
            if st.button(
                label,
                key=f"category::{category}",
                use_container_width=True,
            ):
                if selected:
                    st.session_state["selected_category"] = None
                else:
                    st.session_state["selected_category"] = category
                st.rerun()


# =========================================================
# PRODUKTY Z WYBRANEJ KATEGORII
# =========================================================

active_category = st.session_state["selected_category"]

if active_category:
    st.divider()
    st.subheader(active_category)

    category_df = df[
        df["Kategoria"].astype(str) == str(active_category)
    ].copy()

    category_df = product_sort(category_df)

    if POPULARITY_COL in category_df.columns and category_df[POPULARITY_COL].notna().any():
        st.caption("Produkty posortowane według pola „popularity”.")
    else:
        st.caption(
            "Produkty posortowane od najwyższej kaloryczności. "
            "Później możemy dodać osobną kolejność popularności."
        )

    category_ids = category_df.index.tolist()

    for start in range(0, len(category_ids), 4):
        row_ids = category_ids[start:start + 4]
        cols = st.columns(4)

        for col, product_id in zip(cols, row_ids):
            row = df.loc[product_id]

            qty = get_qty(product_id)
            with col:
                if qty <= 0:
                    if st.button(
                        f"{row['Produkt']}",
                        key=f"product_add::{product_id}",
                        use_container_width=True,
                        help="Kliknij, aby dodać 1 porcję",
                    ):
                        set_qty(product_id, 1.0)
                        st.rerun()

                else:
                    # Wybrany produkt: nazwa i sterowanie ilością w jednej linii.
                    name_col, minus_col, qty_col, plus_col = st.columns([3.8, 1, 1, 1])

                    with name_col:
                        st.markdown(
                            f'<div class="selected-inline-name">{row["Produkt"]}</div>',
                            unsafe_allow_html=True,
                        )

                    with minus_col:
                        if st.button(
                            "−",
                            key=f"product_minus::{product_id}",
                            use_container_width=True,
                            help="Odejmij 1 porcję",
                        ):
                            subtract_one(product_id)
                            st.rerun()

                    with qty_col:
                        st.button(
                            format_qty(qty),
                            key=f"product_qty_display::{product_id}",
                            disabled=True,
                            use_container_width=True,
                        )

                    with plus_col:
                        if st.button(
                            "+",
                            key=f"product_plus::{product_id}",
                            use_container_width=True,
                            help="Dodaj 1 porcję",
                        ):
                            add_one(product_id)
                            st.rerun()


# =========================================================
# PODSUMOWANIE
# =========================================================

menu_ids = selected_ids()

st.divider()
st.subheader("🛒 Twoje menu")

if not menu_ids:
    st.info(
        "Nie masz jeszcze żadnych produktów. "
        "Wybierz kategorię albo użyj wyszukiwarki."
    )
else:
    menu = df.loc[menu_ids].copy()

    menu["quantity"] = [
        get_qty(product_id)
        for product_id in menu.index
    ]

    for c in NUMERIC_PER_PORTION:
        menu[c] = pd.to_numeric(
            menu[c],
            errors="coerce"
        ).fillna(0.0)

    menu["price_effective"] = menu[PRICE_COL]

    menu["kcal_total"] = (
        menu["kcal_per_portion"] * menu["quantity"]
    )
    menu["kJ_total"] = (
        menu["kJ_per_portion"] * menu["quantity"]
    )
    menu["protein_total"] = (
        menu["protein_per_portion"] * menu["quantity"]
    )
    menu["fat_total"] = (
        menu["fat_per_portion"] * menu["quantity"]
    )
    menu["carbs_total"] = (
        menu["carbs_per_portion"] * menu["quantity"]
    )
    menu["sugar_total"] = (
        menu["sugar_per_portion"] * menu["quantity"]
    )
    menu["satfat_total"] = (
        menu["kwasy_per_portion"] * menu["quantity"]
    )
    menu["salt_total"] = (
        menu["salt_per_portion"] * menu["quantity"]
    )
    menu["cost_total"] = (
        menu["price_effective"] * menu["quantity"]
    )

    kcal_total = float(menu["kcal_total"].sum())
    protein_total = float(menu["protein_total"].sum())
    fat_total = float(menu["fat_total"].sum())
    carbs_total = float(menu["carbs_total"].sum())
    sugar_total = float(menu["sugar_total"].sum())
    satfat_total = float(menu["satfat_total"].sum())
    salt_total = float(menu["salt_total"].sum())
    kj_total = float(menu["kJ_total"].sum())

    # Jeżeli żadna pozycja nie ma ceny, nie pokazujemy sztucznego 0 zł.
    has_any_price = menu["price_effective"].notna().any()

    if has_any_price:
        total_cost = float(menu["cost_total"].fillna(0).sum())
    else:
        total_cost = np.nan

    # -----------------------------------------------------
    # GŁÓWNE METRYKI
    # -----------------------------------------------------

    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Kcal", f"{kcal_total:.0f}")
    m2.metric("Białko", f"{protein_total:.1f} g")
    m3.metric("Tłuszcze", f"{fat_total:.1f} g")
    m4.metric("Węglowodany", f"{carbs_total:.1f} g")

    if pd.notna(total_cost):
        m5.metric("Koszt", f"{total_cost:.2f} zł")
    else:
        m5.metric("Koszt", "—")

    render_rws_bar(
        m1,
        kcal_total,
        RWS["kcal"],
        "#FF6B6B",
        " kcal",
    )
    render_rws_bar(
        m2,
        protein_total,
        RWS["protein_g"],
        "#4CAF50",
        " g",
    )
    render_rws_bar(
        m3,
        fat_total,
        RWS["fat_g"],
        "#FFC107",
        " g",
    )
    render_rws_bar(
        m4,
        carbs_total,
        RWS["carbs_g"],
        "#42A5F5",
        " g",
    )

    st.caption(
        f"Energia: {kj_total:.0f} kJ  •  "
        f"Cukry: {sugar_total:.1f} g  •  "
        f"Kwasy nasycone: {satfat_total:.1f} g  •  "
        f"Sól: {salt_total:.2f} g"
    )

    # -----------------------------------------------------
    # SZCZEGÓŁOWA EDYCJA
    # -----------------------------------------------------

    st.markdown("### Dokładna edycja")

    st.caption(
        "Tutaj możesz skorygować ilość dokładniej — "
        "np. ustawić 0,5 Zingera zamiast całej sztuki."
    )

    # Najpierw synchronizujemy klucze widgetów.
    for product_id in menu.index:
        dkey = detail_qty_key(product_id)
        if dkey not in st.session_state:
            st.session_state[dkey] = get_qty(product_id)

    # Callback number_input.
    def sync_detail_qty(product_id: int):
        dkey = detail_qty_key(product_id)
        value = float(st.session_state.get(dkey, 0.0))
        st.session_state[qty_key(product_id)] = max(
            0.0,
            min(99.0, value)
        )

    for product_id, row in menu.iterrows():
        product_name = str(row["Produkt"])

        with st.container():
            name_col, minus_col, qty_col, plus_col, remove_col = st.columns([4.6, 0.8, 1.5, 0.8, 1.2])

            with name_col:
                st.markdown(
                    f"**{product_name}**  \n"
                    f"<span class='small-muted'>{row['Kategoria']}</span>",
                    unsafe_allow_html=True,
                )

            with minus_col:
                if st.button(
                    "−",
                    key=f"detail_minus::{product_id}",
                    use_container_width=True,
                    help="Odejmij 0,5 porcji",
                ):
                    set_qty(product_id, max(0.0, get_qty(product_id) - 0.5))
                    st.rerun()

            with qty_col:
                st.number_input(
                    f"Ilość — {product_name}",
                    min_value=0.0,
                    max_value=99.0,
                    step=0.5,
                    key=detail_qty_key(product_id),
                    on_change=sync_detail_qty,
                    args=(product_id,),
                    label_visibility="collapsed",
                )

            with plus_col:
                if st.button(
                    "+",
                    key=f"detail_plus::{product_id}",
                    use_container_width=True,
                    help="Dodaj 0,5 porcji",
                ):
                    set_qty(product_id, min(99.0, get_qty(product_id) + 0.5))
                    st.rerun()

            with remove_col:
                if st.button(
                    "Usuń",
                    key=f"detail_remove::{product_id}",
                    use_container_width=True,
                ):
                    set_qty(product_id, 0.0)
                    st.rerun()

        st.divider()

    # -----------------------------------------------------
    # CENY — OPCJONALNA EDYCJA
    # -----------------------------------------------------

    with st.expander("💰 Edytuj ceny", expanded=False):
        st.caption(
            "Ceny z CSV są używane domyślnie. "
            "Tutaj możesz wprowadzić własną cenę produktu."
        )

        price_changed = False

        for product_id, row in menu.iterrows():
            base_price = row[PRICE_COL]

            if pd.notna(base_price):
                default_price = float(base_price)
            else:
                default_price = 0.0

            pkey = price_key(product_id)

            if pkey not in st.session_state:
                st.session_state[pkey] = default_price

            new_price = st.number_input(
                f"{row['Produkt']} — cena [PLN]",
                min_value=0.0,
                max_value=5000.0,
                step=0.5,
                format="%.2f",
                key=pkey,
            )

            if pd.notna(base_price):
                if abs(float(new_price) - float(base_price)) > 1e-9:
                    price_changed = True
            elif new_price > 0:
                price_changed = True

        if price_changed:
            st.info(
                "Własne ceny są uwzględniane w dodatkowym "
                "podsumowaniu poniżej."
            )

        custom_cost = 0.0
        custom_has_price = False

        for product_id, row in menu.iterrows():
            pkey = price_key(product_id)
            entered_price = float(st.session_state.get(pkey, 0.0))
            base_price = row[PRICE_COL]

            if entered_price > 0:
                effective_price = entered_price
                custom_has_price = True
            elif pd.notna(base_price):
                effective_price = float(base_price)
                custom_has_price = True
            else:
                effective_price = np.nan

            if pd.notna(effective_price):
                custom_cost += (
                    effective_price * get_qty(product_id)
                )

        if custom_has_price:
            st.metric(
                "Koszt po uwzględnieniu własnych cen",
                f"{custom_cost:.2f} zł"
            )

    # -----------------------------------------------------
    # TABELA / EKSPORT
    # -----------------------------------------------------

    with st.expander("📋 Szczegółowe dane", expanded=False):
        display = menu[
            [
                "Kategoria",
                "Produkt",
                "quantity",
                "kcal_total",
                "protein_total",
                "fat_total",
                "carbs_total",
                "sugar_total",
                "satfat_total",
                "salt_total",
            ]
        ].copy()

        display.columns = [
            "Kategoria",
            "Produkt",
            "Ilość",
            "Kcal",
            "Białko [g]",
            "Tłuszcze [g]",
            "Węglowodany [g]",
            "Cukry [g]",
            "Kwasy nasycone [g]",
            "Sól [g]",
        ]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )

        export_df = display.copy()

        st.download_button(
            "Pobierz menu (CSV)",
            data=export_df.to_csv(
                index=False,
                sep=";",
            ).encode("utf-8-sig"),
            file_name="moje_menu.csv",
            mime="text/csv",
        )


# =========================================================
# STOPKA
# =========================================================

st.caption(
    "Wartości odżywcze są liczone na podstawie danych z pliku CSV."
)
