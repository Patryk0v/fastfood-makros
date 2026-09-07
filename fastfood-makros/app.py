# app.py — Fastfood: wybór produktów i sumy makr „per portion”
# Wymaga: streamlit, pandas, numpy
# CSV: UTF-8/UTF-8-SIG, separator ';'
# Kolumny wymagane:
# 'Kategoria','Produkt','kJ_per_portion','kcal_per_portion',
# 'fat_per_portion','kwasy_per_portion','carbs_per_portion',
# 'sugar_per_portion','protein_per_portion','salt_per_portion'
# Opcjonalnie: 'price_pln'

import os
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fastfood – wybór i sumy (per portion)", layout="wide")

# --- KONFIG / STAŁE ---

LOCAL_PATH = r"C:\Users\PC\Desktop\Projekty\Tabela wartości\github\fastfood-makros\data\items_kfc.csv"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_PATH = os.path.join(BASE_DIR, "data", "items_kfc.csv")

DEFAULT_PATH = LOCAL_PATH if os.path.exists(LOCAL_PATH) else CLOUD_PATH

PRICE_COL = "price_pln"

REQUIRED = [
    "Kategoria","Produkt","kJ_per_portion","kcal_per_portion",
    "fat_per_portion","kwasy_per_portion","carbs_per_portion",
    "sugar_per_portion","protein_per_portion","salt_per_portion"
]
NUMERIC_PER_PORTION = [
    "kJ_per_portion","kcal_per_portion",
    "fat_per_portion","kwasy_per_portion",
    "carbs_per_portion","sugar_per_portion",
    "protein_per_portion","salt_per_portion"
]
RWS = {"kcal": 2500, "protein_g": 60, "fat_g": 80, "carbs_g": 340}

# --- IO / DANE ---
def load_csv(path_or_buffer):
    """Wczytaj CSV (UTF-8/UTF-8-SIG, ';'), oczyść nagłówki, liczby i cenę."""
    df = pd.read_csv(path_or_buffer, sep=';', encoding='utf-8-sig')
    df.columns = df.columns.str.replace('\ufeff','', regex=False).str.strip()

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Brakuje kolumn: {missing}\nMasz: {list(df.columns)}")

    # liczby per_portion
    for c in NUMERIC_PER_PORTION:
        s = (df[c].astype(str)
                 .str.replace(',', '.', regex=False)
                 .str.replace('\xa0','', regex=False)
                 .str.replace(' ', '', regex=False))
        df[c] = pd.to_numeric(s, errors='coerce')

    # cena (opcjonalna)
if PRICE_COL not in df.columns:
    df[PRICE_COL] = np.nan
else:
    s = df[PRICE_COL].astype(str)

    s = s.str.replace(",", ".", regex=False)
    s = s.str.replace("\xa0", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.replace(r"[^0-9.\-()]", "", regex=True)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    s = s.replace({
        "": np.nan,
        ".": np.nan,
        "-": np.nan
    })

    df[PRICE_COL] = pd.to_numeric(s, errors="coerce")

return df
    
# --- AUTOMATYCZNE WCZYTANIE DANYCH ---

try:
    df = load_csv(DEFAULT_PATH)
except Exception as e:
    st.error(f"Problem z wczytaniem danych: {e}")
    st.stop()
    
st.title("🍟 Fastfood — wybór produktów i sumy 'per portion'")

# --- STAN GLOBALNY ---
if "selected_ids" not in st.session_state:
    st.session_state["selected_ids"] = []
if "ms_global" not in st.session_state:
    st.session_state["ms_global"] = []

# --- FILTR KATEGORII + RESET ---
left, right = st.columns([3,1])
with left:
    cats = ["(wszystkie)"] + sorted(df["Kategoria"].dropna().astype(str).unique().tolist())
    cat = st.selectbox("Kategoria", cats, key="cat_select")
with right:
    st.write("")
    if st.button("Reset", use_container_width=True):
        st.session_state["selected_ids"] = []
        st.session_state["ms_global"] = []
        for k in list(st.session_state.keys()):
            if str(k).startswith("qty::") or str(k).startswith("price::"):
                del st.session_state[k]
        if hasattr(st, "rerun"): st.rerun()
        else: st.experimental_rerun()

# --- FILTR PO KATEGORII ---
filtered = df.copy()
if cat != "(wszystkie)":
    filtered = filtered[filtered["Kategoria"].astype(str) == cat]
if filtered.empty:
    st.warning("Brak produktów po zastosowaniu filtrów dla tej kategorii.")
    filtered = df.iloc[0:0]  # pusta ramka, ale kontynuujemy

# --- MULTISELECT (zachowuje wybrane spoza kategorii; 'X' usuwa globalnie) ---
cat_options = set(filtered.index)
options = sorted(cat_options | set(st.session_state["selected_ids"]))

def _fmt(i):
    kcal = df.at[i, "kcal_per_portion"]
    kcal_txt = f"({kcal:.0f} kcal)" if pd.notna(kcal) else "(?)"
    return f"{df.at[i, 'Produkt']}  {kcal_txt}"

current_value = [i for i in st.session_state["ms_global"] if i in options]
chosen_now = st.multiselect("Zaznacz w tej kategorii", options=options,
                            default=current_value, format_func=_fmt, key="ms_global")

st.session_state["selected_ids"] = sorted(set(chosen_now))

# --- ZAKŁADKI (widoczne zawsze) ---
tab_creator, tab_bundles, tab_coupons, tab_rank = st.tabs(
    ["Creator", "Zestawy", "Kupony", "Ranking opłacalności"]
)

# =========================
#       ZAKŁADKA: CREATOR
# =========================
with tab_creator:
    if not st.session_state["selected_ids"]:
        st.info("Zaznacz produkty powyżej, aby zobaczyć podsumowanie (ilości, ceny, paski RWS).")
    else:
        sel = df.loc[st.session_state["selected_ids"]].copy()

        # Ilości porcji
        def qty_key(row): return f"qty::{row['Kategoria']}::{row['Produkt']}"
        st.markdown("**Ilości porcji (np. 0.5, 1, 2):**")
        quantities = {}
        for idx, row in sel.iterrows():
            key = qty_key(row)
            qv = st.number_input(f"{row['Produkt']}", min_value=0.0, max_value=100.0,
                                 value=1.0, step=0.5, key=key)
            quantities[idx] = qv

        sel_q = sel.copy()
        sel_q["quantity"] = sel_q.index.map(lambda i: float(quantities.get(i, 0.0)))
        sel_q["quantity"] = sel_q["quantity"].clip(lower=0.0, upper=100.0)

        # Ceny: baza + nadpisy
        def price_key(row): return f"price::{row['Kategoria']}::{row['Produkt']}"
        st.markdown("**Ceny (PLN) — możesz nadpisać swoją cenę dla każdej pozycji:**")
        user_prices, base_prices = {}, {}
        for idx, row in sel.iterrows():
            key = price_key(row)
            base = float(sel.loc[idx, PRICE_COL]) if pd.notna(sel.loc[idx, PRICE_COL]) else np.nan
            base_prices[idx] = base
            default_val = float(base) if pd.notna(base) else 0.0
            up = st.number_input(f"{row['Produkt']} — cena [PLN]", min_value=0.0, max_value=1000.0,
                                 value=default_val, step=0.5, key=key)
            user_prices[idx] = float(up)

        sel_q["base_price"] = sel_q.index.map(lambda i: base_prices.get(i, np.nan))
        sel_q["user_price"] = sel_q.index.map(lambda i: user_prices.get(i, np.nan))
        sel_q.loc[(sel_q["base_price"].isna()) & (sel_q["user_price"] == 0.0), "user_price"] = np.nan
        sel_q["effective_price"] = np.where(sel_q["user_price"].notna(), sel_q["user_price"], sel_q["base_price"])
        sel_q["cost_total"] = sel_q["effective_price"] * sel_q["quantity"]

        # Higiena liczb
        for c in NUMERIC_PER_PORTION:
            sel_q[c] = pd.to_numeric(sel_q[c], errors="coerce").fillna(0.0)

        # Podgląd zaznaczonych
        preview_cols = [
            "Kategoria","Produkt","quantity",
            "kcal_per_portion","kJ_per_portion",
            "protein_per_portion","fat_per_portion","carbs_per_portion",
            "sugar_per_portion","kwasy_per_portion","salt_per_portion",
            "effective_price"
        ]
        view = sel_q[preview_cols].copy()
        view["kcal_total"]    = view["kcal_per_portion"]    * view["quantity"]
        view["kJ_total"]      = view["kJ_per_portion"]      * view["quantity"]
        view["protein_total"] = view["protein_per_portion"] * view["quantity"]
        view["fat_total"]     = view["fat_per_portion"]     * view["quantity"]
        view["carbs_total"]   = view["carbs_per_portion"]   * view["quantity"]
        view["sugar_total"]   = view["sugar_per_portion"]   * view["quantity"]
        view["kwasy_total"]   = view["kwasy_per_portion"]   * view["quantity"]
        view["salt_total"]    = view["salt_per_portion"]    * view["quantity"]
        view["cost_total"]    = sel_q["cost_total"]

        view["eff_pln_per_kcal"] = np.where(
            view["kcal_per_portion"] > 0,
            view["effective_price"] / view["kcal_per_portion"], np.nan
        )
        view["eff_pln_per_g_protein"] = np.where(
            view["protein_per_portion"] > 0,
            view["effective_price"] / view["protein_per_portion"], np.nan
        )

        st.dataframe(
            view[[
                "Kategoria","Produkt","quantity","effective_price",
                "kcal_total","protein_total","fat_total","carbs_total",
                "sugar_total","kwasy_total","salt_total","cost_total",
                "eff_pln_per_kcal","eff_pln_per_g_protein"
            ]],
            use_container_width=True
        )

        # Metryki główne
        total_cost   = float(np.nansum(view["cost_total"].values))
        kcal_total   = float(np.nansum(sel_q["kcal_per_portion"]    * sel_q["quantity"]))
        protein_total= float(np.nansum(sel_q["protein_per_portion"] * sel_q["quantity"]))
        fat_total    = float(np.nansum(sel_q["fat_per_portion"]     * sel_q["quantity"]))
        carbs_total  = float(np.nansum(sel_q["carbs_per_portion"]   * sel_q["quantity"]))

        st.subheader("Podsumowanie – kluczowe (z ilościami)")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Kcal",            f"{kcal_total:.0f}")
        c2.metric("Białko [g]",      f"{protein_total:.1f}")
        c3.metric("Tłuszcze [g]",    f"{fat_total:.1f}")
        c4.metric("Węglowodany [g]", f"{carbs_total:.1f}")
        c5.metric("Koszt [PLN]",     f"{total_cost:.2f}")
        # --- WSKAŹNIKI OPŁACALNOŚCI (globalne dla całego wyboru) ---
        from streamlit.components.v1 import html as st_html

        def deal_label(pln_per_kcal: float):
            if np.isnan(pln_per_kcal):
                return "Brak danych", "#999999"
            if pln_per_kcal <= 0.015:
                return "Dobry deal", "#2e7d32"
            elif pln_per_kcal <= 0.03:
                return "Średni deal", "#f9a825"
            else:
                return "Słaby deal", "#c62828"

        pln_per_kcal_total = (total_cost / kcal_total) if kcal_total > 0 else np.nan
        pln_per_g_protein_total = (total_cost / protein_total) if protein_total > 0 else np.nan
        protein_text = f"{pln_per_g_protein_total:.3f}" if not np.isnan(pln_per_g_protein_total) else "—"
        label, color = deal_label(pln_per_kcal_total)

        # Skala 0.010–0.050
        min_v, max_v = 0.010, 0.050
        if np.isnan(pln_per_kcal_total):
            pct = 0.0
            value_text = "—"
        else:
            v = float(np.clip(pln_per_kcal_total, min_v, max_v))
            pct = (v - min_v) / (max_v - min_v) * 100.0
            value_text = f"{pln_per_kcal_total:.3f}"

        # HTML + CSS panelu (kompaktowy)
        panel_html = f"""
<style>
.deal-wrap   {{ max-width: 560px; margin: 10px auto 0; }}
.deal-card   {{ padding: 12px 14px; border-radius: 12px; background: #f5f5f5; box-shadow: 0 1px 6px rgba(0,0,0,.06); }}
.deal-row    {{ display:flex; gap:16px; align-items:center; flex-wrap:wrap; }}
.deal-badge  {{ padding:4px 10px; border-radius: 999px; color: #fff; font-weight:600; }}
.deal-track  {{ position: relative; height: 12px; width: 100%; background: #eee; border-radius: 999px; margin-top: 10px; border:1px solid #ddd; }}
.deal-fill   {{ height: 12px; border-radius: 999px; }}
.deal-marks  {{ position: absolute; left:0; right:0; top:0; height:12px; pointer-events:none; }}
.deal-mark   {{ position:absolute; top:-2px; width:2px; height:16px; background:#aaa; }}
.deal-pointer{{ position:absolute; top:6px; width:14px; height:14px; border-radius:50%; border:2px solid #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.15); transform: translate(-50%,-50%); }}
.deal-tip    {{ position:absolute; top:-28px; transform: translateX(-50%); background:#333; color:#fff; padding:2px 6px; border-radius:6px; font-size:0.80rem; white-space:nowrap; }}
.deal-scale  {{ display:flex; justify-content:space-between; font-size: 0.80rem; color:#666; margin-top: 6px; }}
.deal-note   {{ font-size:0.80rem; color:#666; margin-top: 2px; }}
</style>

<div class="deal-wrap">
  <div class="deal-card">
    <div class="deal-row">
      <div><b>Opłacalność (globalnie)</b></div>
      <div>PLN/kcal: <b>{value_text}</b></div>
      <div>PLN/g białka: <b>{protein_text}</b></div>
      <div class="deal-badge" style="background:{color};">{label}</div>
    </div>

    <div class="deal-track">
      <div class="deal-fill" style="width:{pct:.1f}%; background:{color};"></div>
      <div class="deal-marks">
        <div class="deal-mark" style="left:{(0.015 - min_v) / (max_v - min_v) * 100:.1f}%;"></div>
        <div class="deal-mark" style="left:{(0.030 - min_v) / (max_v - min_v) * 100:.1f}%;"></div>
      </div>
      <div class="deal-pointer" style="left:{pct:.1f}%; background:{color};"></div>
      <div class="deal-tip" style="left:{pct:.1f}%;">{value_text} PLN/kcal</div>
    </div>

    <div class="deal-scale">
      <div>0.010</div>
      <div>0.050</div>
    </div>
    <div class="deal-note">Kreseczki: 0.015 (granica „Dobry”) i 0.030 (granica „Średni”). Niżej = lepiej.</div>
  </div>
</div>
"""
        # Render stabilnie jako komponent HTML
        st_html(panel_html, height=200)
  

        # Paski RWS
        st.markdown("""
        <style>
        .rws-wrap { margin-top: 6px; }
        .rws-track { background: #bcbcbc; border-radius: 8px; height: 10px; width: 100%; }
        .rws-fill { height: 10px; border-radius: 8px; }
        .rws-text { font-size: 0.9rem; margin-top: 4px; color: #666; }
        </style>
        """, unsafe_allow_html=True)

        def render_rws_bar(container, current, target, color, unit):
            target = float(target) if target and target > 0 else 1.0
            pct = max(0.0, min(current / target, 1.0)) * 100.0
            txt = f"{current:.1f}{unit} / {target:.0f}{unit} ({(current/target)*100:.0f}%)"
            html = f'''
            <div class="rws-wrap">
              <div class="rws-track">
                <div class="rws-fill" style="width:{pct:.1f}%; background:{color};"></div>
              </div>
              <div class="rws-text">{txt}</div>
            </div>'''
            container.markdown(html, unsafe_allow_html=True)

        render_rws_bar(c1, kcal_total,    RWS["kcal"],      color="#FF6B6B", unit=" kcal")
        render_rws_bar(c2, protein_total, RWS["protein_g"], color="#4CAF50", unit=" g")
        render_rws_bar(c3, fat_total,     RWS["fat_g"],     color="#FFC107", unit=" g")
        render_rws_bar(c4, carbs_total,   RWS["carbs_g"],   color="#42A5F5", unit=" g")

        # Detale
        kj_total     = float(np.nansum(sel_q["kJ_per_portion"]     * sel_q["quantity"]))
        sugar_total  = float(np.nansum(sel_q["sugar_per_portion"]  * sel_q["quantity"]))
        satfat_total = float(np.nansum(sel_q["kwasy_per_portion"]  * sel_q["quantity"]))
        salt_total   = float(np.nansum(sel_q["salt_per_portion"]   * sel_q["quantity"]))
        st.caption("Szczegóły (z ilościami):")
        st.caption(f"• Energia: {kj_total:.0f} kJ")
        st.caption(f"• Kwasy nasycone: {satfat_total:.1f} g")
        st.caption(f"• Cukry: {sugar_total:.1f} g")
        st.caption(f"• Sól: {salt_total:.2f} g")

        # Eksport
        st.download_button(
            "Pobierz zaznaczone (CSV)",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="wybrane_produkty.csv",
            mime="text/csv"
        )

# =========================
#       ZAKŁADKA: ZESTAWY
# =========================
with tab_bundles:
    st.subheader("Zestawy — wybór pozycji i cena końcowa")

    # --- STAN LOKALNY ---
    if "bund_sel_ids" not in st.session_state:
        st.session_state["bund_sel_ids"] = []
    if "bund_ms" not in st.session_state:
        st.session_state["bund_ms"] = []
    if "bund_order" not in st.session_state:
        st.session_state["bund_order"] = []
    if "bundle_total_price" not in st.session_state:
        st.session_state["bundle_total_price"] = 0.0

    # --- FILTR KATEGORII + RESET ---
    b_left, b_mid, b_right = st.columns([3,1,1])
    with b_left:
        cats2 = ["(wszystkie)"] + sorted(df["Kategoria"].dropna().astype(str).unique().tolist())
        cat_bund = st.selectbox("Kategoria (Zestawy)", cats2, key="cat_bund_select")
    with b_mid:
        st.write("")
        if st.button("Reset (Zestawy)", use_container_width=True):
            # czyścimy tylko tab 'Zestawy'
            st.session_state["bund_sel_ids"] = []
            st.session_state["bund_ms"] = []
            st.session_state["bund_order"] = []
            for k in list(st.session_state.keys()):
                if str(k).startswith("bundqty::"):
                    del st.session_state[k]
            st.session_state["bundle_total_price"] = 0.0
            st.rerun()
    with b_right:
        st.write("")
        st.caption("Dodaj pozycje, ustaw ilości (min 1, max 99) i podaj cenę zestawu.")

    # --- OPCJE wg kategorii ---
    bund_filtered = df.copy()
    if cat_bund != "(wszystkie)":
        bund_filtered = bund_filtered[bund_filtered["Kategoria"].astype(str) == cat_bund]
    cat_options2 = set(bund_filtered.index)

    # (A) OBSŁUGA USUWANIA – MUSI BYĆ PRZED multiselect
    if "__to_remove" in st.session_state:
        rid = st.session_state.pop("__to_remove")
        # usuń z list stanowych
        st.session_state["bund_sel_ids"] = [x for x in st.session_state["bund_sel_ids"] if x != rid]
        st.session_state["bund_order"]   = [x for x in st.session_state["bund_order"] if x != rid]
        st.session_state["bund_ms"]      = [x for x in st.session_state.get("bund_ms", []) if x != rid]
        # usuń klucz ilości, żeby po ponownym dodaniu startować od 1
        qkey_del = f"bundqty::{df.at[rid,'Kategoria']}::{df.at[rid,'Produkt']}"
        if qkey_del in st.session_state:
            del st.session_state[qkey_del]

    # pokaż także już wybrane spoza bieżącej kategorii
    options2 = sorted(cat_options2 | set(st.session_state["bund_sel_ids"]))

    def _fmt_b(i: int) -> str:
        kcal = df.at[i, "kcal_per_portion"]
        kcal_txt = f"({kcal:.0f} kcal)" if pd.notna(kcal) else "(?)"
        return f"{df.at[i, 'Produkt']}  {kcal_txt}"

    prev_set = set(st.session_state["bund_sel_ids"])
    current_b = [i for i in st.session_state["bund_ms"] if i in options2]
    chosen_b = st.multiselect(
        "Zaznacz pozycje do zestawu (możesz wybierać w wielu kategoriach)",
        options=options2, default=current_b, format_func=_fmt_b, key="bund_ms"
    )
    st.session_state["bund_sel_ids"] = sorted(set(chosen_b))
    new_ids     = [i for i in st.session_state["bund_sel_ids"] if i not in prev_set]
    removed_ids = [i for i in prev_set if i not in st.session_state["bund_sel_ids"]]

    # dodane nowo/ponownie → ilość zawsze = 1.0
    for i in new_ids:
        if i not in st.session_state["bund_order"]:
            st.session_state["bund_order"].append(i)
        qkey_new = f"bundqty::{df.at[i,'Kategoria']}::{df.at[i,'Produkt']}"
        st.session_state[qkey_new] = 1.0

    # porządek po usunięciach
    if removed_ids:
        st.session_state["bund_order"] = [i for i in st.session_state["bund_order"] if i not in removed_ids]

    if not st.session_state["bund_sel_ids"]:
        st.info("Zaznacz produkty, aby ustawić ilości i policzyć wskaźniki dla zestawu.")
        st.stop()

    # --- STYL (kontrast + czytelne przyciski) ---
    st.markdown("""
<style>
.qpill{
  display:inline-block; min-width:44px; text-align:center; padding:4px 8px;
  border-radius:10px; background:#ffffff; color:#111; font-weight:700;
  border:1px solid #8a8a8a;
}
.rowline{ padding:6px 0; border-bottom:1px solid #2a2a2a; }
.ctrlwrap .stButton>button{
  color:#111 !important; background:#ffffff !important;
  border:1px solid #8a8a8a !important; border-radius:10px !important;
  font-weight:700; padding:2px 0 !important;
}
.ctrlwrap .stButton>button:hover{ filter:brightness(0.95); }
</style>
""", unsafe_allow_html=True)

    # --- LISTA WYBRANYCH: nazwa | [➖] [qty] [➕] [🗑️] ; najnowsze u góry ---
    display_ids = [i for i in reversed(st.session_state["bund_order"])
                   if i in st.session_state["bund_sel_ids"]]

    def qty_key_b(i: int) -> str:
        return f"bundqty::{df.at[i,'Kategoria']}::{df.at[i,'Produkt']}"

    for i in display_ids:
        name = df.at[i, "Produkt"]
        qkey = qty_key_b(i)
        if qkey not in st.session_state:
            st.session_state[qkey] = 1.0  # gwarancja startu od 1

        col_name, col_ctrl = st.columns([0.65, 0.35])
        with col_name:
            st.markdown(f'<div class="rowline"><b>{name}</b></div>', unsafe_allow_html=True)

        with col_ctrl:
            st.markdown('<div class="ctrlwrap">', unsafe_allow_html=True)
            b_minus, b_qty, b_plus, b_trash = st.columns([1,1,1,1])

            with b_minus:
                if st.button("➖", key=f"bund_minus::{i}", help="Zmniejsz o 1", use_container_width=True):
                    st.session_state[qkey] = max(1.0, min(99.0, float(st.session_state[qkey]) - 1.0))
                    st.rerun()
            with b_qty:
                qty_txt = int(max(1, min(99, round(float(st.session_state[qkey])))))
                st.markdown(f'<div class="qpill">{qty_txt}</div>', unsafe_allow_html=True)
            with b_plus:
                if st.button("➕", key=f"bund_plus::{i}", help="Zwiększ o 1", use_container_width=True):
                    st.session_state[qkey] = max(1.0, min(99.0, float(st.session_state[qkey]) + 1.0))
                    st.rerun()
            with b_trash:
                if st.button("🗑️", key=f"bund_del::{i}", help="Usuń z zestawu", use_container_width=True):
                    st.session_state["__to_remove"] = i
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # --- PRZELICZENIA SUM ---
    sel_bq = df.loc[st.session_state["bund_sel_ids"]].copy()
    quantities_b = []
    for i in sel_bq.index:
        qv = float(st.session_state.get(qty_key_b(i), 1.0))
        quantities_b.append(max(1.0, min(99.0, qv)))
    sel_bq["quantity"] = quantities_b
    for c in NUMERIC_PER_PORTION:
        sel_bq[c] = pd.to_numeric(sel_bq[c], errors="coerce").fillna(0.0)

    kcal_b_total    = float(np.nansum(sel_bq["kcal_per_portion"]    * sel_bq["quantity"]))
    protein_b_total = float(np.nansum(sel_bq["protein_per_portion"] * sel_bq["quantity"]))
    fat_b_total     = float(np.nansum(sel_bq["fat_per_portion"]     * sel_bq["quantity"]))
    carbs_b_total   = float(np.nansum(sel_bq["carbs_per_portion"]   * sel_bq["quantity"]))

    # --- CENA ZESTAWU (stabilna, nie resetuje się) ---
    bundle_price = st.number_input(
        "Cena zestawu [PLN]",
        min_value=0.0, max_value=5000.0,
        step=0.5,
        value=float(st.session_state["bundle_total_price"]),
        format="%.2f"
    )
    st.session_state["bundle_total_price"] = float(bundle_price)

    # --- PODSUMOWANIE (główne metryki) ---
    st.subheader("Podsumowanie zestawu")
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Kcal",            f"{kcal_b_total:.0f}")
    d2.metric("Białko [g]",      f"{protein_b_total:.1f}")
    d3.metric("Tłuszcze [g]",    f"{fat_b_total:.1f}")
    d4.metric("Węglowodany [g]", f"{carbs_b_total:.1f}")
    d5.metric("Cena zestawu [PLN]", f"{bundle_price:.2f}")

    # --- PASKI RWS (dokładnie pod kafelkami Kcal/Białko/Tłuszcze/Węglowodany) ---
    st.markdown("""
<style>
.rws-wrap { margin-top: 6px; }
.rws-track { background: #bcbcbc; border-radius: 10px; height: 10px; width: 100%; }
.rws-fill { height: 10px; border-radius: 10px; }
.rws-text { font-size: 0.9rem; margin-top: 4px; color: #666; }
</style>
""", unsafe_allow_html=True)

    def render_rws_bar_b(container, current, target, color, unit):
        target = float(target) if target and target > 0 else 1.0
        pct = max(0.0, min(current / target, 1.0)) * 100.0
        txt = f"{current:.1f}{unit} / {target:.0f}{unit} ({(current/target)*100:.0f}%)"
        html = f'''
<div class="rws-wrap">
  <div class="rws-track">
    <div class="rws-fill" style="width:{pct:.1f}%; background:{color};"></div>
  </div>
  <div class="rws-text">{txt}</div>
</div>'''
        container.markdown(html, unsafe_allow_html=True)

    # render w TYCH SAMYCH kolumnach (będzie dokładnie pod metrykami)
    render_rws_bar_b(d1, kcal_b_total,    RWS["kcal"],      color="#FF6B6B", unit=" kcal")
    render_rws_bar_b(d2, protein_b_total, RWS["protein_g"], color="#4CAF50", unit=" g")
    render_rws_bar_b(d3, fat_b_total,     RWS["fat_g"],     color="#FFC107", unit=" g")
    render_rws_bar_b(d4, carbs_b_total,   RWS["carbs_g"],   color="#42A5F5", unit=" g")

    # --- WSKAŹNIKI OPŁACALNOŚCI (panel) ---
    from streamlit.components.v1 import html as st_html

    def deal_label(pln_per_kcal: float):
        if np.isnan(pln_per_kcal):
            return "Brak danych", "#999999"
        if pln_per_kcal <= 0.015:
            return "Dobry deal", "#2e7d32"
        elif pln_per_kcal <= 0.030:
            return "Średni deal", "#f9a825"
        else:
            return "Słaby deal", "#c62828"

    pln_per_kcal_b      = (bundle_price / kcal_b_total)      if kcal_b_total      > 0 else np.nan
    pln_per_g_protein_b = (bundle_price / protein_b_total)   if protein_b_total   > 0 else np.nan

    protein_text_b = f"{pln_per_g_protein_b:.3f}" if not np.isnan(pln_per_g_protein_b) else "—"
    label_b, color_b = deal_label(pln_per_kcal_b)

    min_v, max_v = 0.010, 0.050
    if np.isnan(pln_per_kcal_b):
        pct_b = 0.0
        value_text_b = "—"
    else:
        v = float(np.clip(pln_per_kcal_b, min_v, max_v))
        pct_b = (v - min_v) / (max_v - min_v) * 100.0
        value_text_b = f"{pln_per_kcal_b:.3f}"

    panel_html_b = f"""
<style>
.deal-wrap   {{ max-width: 560px; margin: 10px auto 0; }}
.deal-card   {{ padding: 12px 14px; border-radius: 12px; background: #f5f5f5; box-shadow: 0 1px 6px rgba(0,0,0,.06); }}
.deal-row    {{ display:flex; gap:16px; align-items:center; flex-wrap:wrap; }}
.deal-badge  {{ padding:4px 10px; border-radius: 999px; color: #fff; font-weight:600; }}
.deal-track  {{ position: relative; height: 12px; width: 100%; background: #eee; border-radius: 999px; margin-top: 10px; border:1px solid #ddd; }}
.deal-fill   {{ height: 12px; border-radius: 999px; }}
.deal-marks  {{ position: absolute; left:0; right:0; top:0; height:12px; pointer-events:none; }}
.deal-mark   {{ position:absolute; top:-2px; width:2px; height:16px; background:#aaa; }}
.deal-pointer{{ position:absolute; top:6px; width:14px; height:14px; border-radius:50%; border:2px solid #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.15); transform: translate(-50%,-50%); }}
.deal-tip    {{ position:absolute; top:-28px; transform: translateX(-50%); background:#333; color:#fff; padding:2px 6px; border-radius:6px; font-size:0.80rem; white-space:nowrap; }}
.deal-scale  {{ display:flex; justify-content:space-between; font-size: 0.80rem; color:#666; margin-top: 6px; }}
.deal-note   {{ font-size:0.80rem; color:#666; margin-top: 2px; }}
</style>

<div class="deal-wrap">
  <div class="deal-card">
    <div class="deal-row">
      <div><b>Opłacalność zestawu</b></div>
      <div>PLN/kcal: <b>{value_text_b}</b></div>
      <div>PLN/g białka: <b>{protein_text_b}</b></div>
      <div class="deal-badge" style="background:{color_b};">{label_b}</div>
    </div>

    <div class="deal-track">
      <div class="deal-fill" style="width:{pct_b:.1f}%; background:{color_b};"></div>
      <div class="deal-marks">
        <div class="deal-mark" style="left:{(0.015 - min_v) / (max_v - min_v) * 100:.1f}%;"></div>
        <div class="deal-mark" style="left:{(0.030 - min_v) / (max_v - min_v) * 100:.1f}%;"></div>
      </div>
      <div class="deal-pointer" style="left:{pct_b:.1f}%; background:{color_b};"></div>
      <div class="deal-tip" style="left:{pct_b:.1f}%;">{value_text_b} PLN/kcal</div>
    </div>

    <div class="deal-scale">
      <div>0.010</div>
      <div>0.050</div>
    </div>
    <div class="deal-note">Kreseczki: 0.015 (granica „Dobry”) i 0.030 (granica „Średni”). Niżej = lepiej.</div>
  </div>
</div>
"""
    st_html(panel_html_b, height=200)

    # --- EKSPORT (prosty CSV z listą i ilościami) ---
    export_cols = ["Kategoria", "Produkt", "quantity"]
    export_df = sel_bq[export_cols].copy()
    st.download_button(
        "Pobierz zestaw (CSV)",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="zestaw_wybor.csv",
        mime="text/csv"
    )


# ===== kupony ========

with tab_coupons:
    st.subheader("Kupony")
    st.info("Tu pokażemy aktualne kupony/promocje z CSV (np. numer kuponu, opis, cena, warunki). Wkrótce.")

# =========================
#       ZAKŁADKA: RANKING
# =========================
with tab_rank:
    st.subheader("Ranking opłacalności")

    # Ustawienia rankingu
    rank_metric = st.radio(
        "Metryka", ["kcal/PLN", "PLN/kcal", "PLN/białko"],
        horizontal=True, key="rank_metric"
    )
    rank_scope = st.radio(
        "Zakres", ["Bieżąca kategoria", "Wszystkie kategorie"],
        horizontal=True, key="rank_scope"
    )

    # Ramka do rankingu z ceną efektywną (CSV jako baza)
    df_rank = df.copy()
    df_rank["effective_price"] = df_rank[PRICE_COL]

    # Jeśli w Creator nadpisałeś ceny – uwzględnij
    if "sel_q" in locals():
        overrides = sel_q.get("effective_price", pd.Series(dtype=float)).dropna()
        if len(overrides):
            df_rank.loc[overrides.index, "effective_price"] = overrides

    # Metryki
    df_rank["kcal_per_pln"] = np.where(
        df_rank["effective_price"] > 0,
        df_rank["kcal_per_portion"] / df_rank["effective_price"], np.nan
    )
    df_rank["pln_per_kcal"] = np.where(
        df_rank["kcal_per_portion"] > 0,
        df_rank["effective_price"] / df_rank["kcal_per_portion"], np.nan
    )
    df_rank["pln_per_g_protein"] = np.where(
        df_rank["protein_per_portion"] > 0,
        df_rank["effective_price"] / df_rank["protein_per_portion"], np.nan
    )

    # Zakres
    if rank_scope == "Bieżąca kategoria" and cat != "(wszystkie)":
        subset = df_rank[df_rank["Kategoria"].astype(str) == cat].copy()
    else:
        subset = df_rank.copy()

    # Sort
    if rank_metric == "kcal/PLN":
        metric_col, ascending = "kcal_per_pln", False
    elif rank_metric == "PLN/kcal":
        metric_col, ascending = "pln_per_kcal", True
    else:
        metric_col, ascending = "pln_per_g_protein", True

    rank_cols = ["Kategoria","Produkt","effective_price","kcal_per_portion","protein_per_portion", metric_col]
    table = (subset[rank_cols]
             .dropna(subset=["effective_price", metric_col])
             .sort_values(metric_col, ascending=ascending)
             .head(50))

    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Pobierz ranking (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="ranking_oplacalnosci.csv",
        mime="text/csv"
    )
    st.caption("Pozycje bez ceny (CSV lub nadpisu) mają metrykę NaN i nie trafiają do rankingu.")
