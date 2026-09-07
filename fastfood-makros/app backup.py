# app.py — Fastfood: wybór produktów i sumy makr „per portion”
# Wymaga: streamlit, pandas, numpy
# Plik CSV: UTF-8/UTF-8-SIG, separator ';'
# Kolumny wymagane (Twoje finalne): 
# 'Kategoria','Produkt','AVG_Weight','kJ_100g','kJ_per_portion','kcal_100g','kcal_per_portion',
# 'kcal_rws','fat_g','fat_per_portion','fat_rws','kwasy_g','kwasy_per_portion','kwasy_rws',
# 'carbs_g','carbs_per_portion','carbs_rws','sugar_g','sugar_per_portion','sugar_rws',
# 'protein_g','protein_per_portion','protein_rws','salt_g','salt_per_portion','salt_rws'

import os
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fastfood – wybór i sumy (per portion)", layout="wide")

# --- USTAWIENIA: ścieżka domyślna (zmień, jeśli chcesz) ---
DEFAULT_PATH = r"C:\Users\PC\Desktop\Projekty\Tabela wartości\fastfood-optimizer-starter-v2\data\items_kfc.csv"

REQUIRED = [
    'Kategoria','Produkt','kJ_per_portion','kcal_per_portion',
    'fat_per_portion','kwasy_per_portion','carbs_per_portion',
    'sugar_per_portion','protein_per_portion','salt_per_portion'
]

NUMERIC_PER_PORTION = [
    'kJ_per_portion','kcal_per_portion',
    'fat_per_portion','kwasy_per_portion',
    'carbs_per_portion','sugar_per_portion',
    'protein_per_portion','salt_per_portion'
]

def load_csv(path_or_buffer):
    """
    Wczytaj CSV (UTF-8/UTF-8-SIG, ';'), oczyść nagłówki, zamień przecinki na kropki w liczbach,
    i upewnij się, że kolumny *_per_portion są numeryczne.
    """
    df = pd.read_csv(path_or_buffer, sep=';', encoding='utf-8-sig')
    # Higiena nagłówków: usuń BOM/spacje
    df.columns = df.columns.str.replace('\ufeff','', regex=False).str.strip()
    # Walidacja kolumn
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Brakuje kolumn: {missing}\n"
                         f"Znaleziona lista kolumn: {list(df.columns)}")
    # Konwersja liczb: przecinki -> kropki, usunięcie spacji/nbsp
    for c in NUMERIC_PER_PORTION:
        df[c] = (df[c].astype(str)
                       .str.replace(',', '.', regex=False)
                       .str.replace('\xa0','', regex=False)
                       .str.replace(' ', '', regex=False))
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


# RWS (mężczyzna) – użyjemy później do pasków
RWS = {
    "kcal": 2500,
    "protein_g": 60,
    "fat_g": 80,
    "carbs_g": 340,
}


# --- UI: wybór źródła danych ---
st.sidebar.header("Źródło danych")
mode = st.sidebar.radio("Wczytaj dane z:", ["Domyślna ścieżka", "Wskaż plik (przeglądarka)"], horizontal=True)

df = None
used_source = None
try:
    if mode == "Domyślna ścieżka":
        path = st.sidebar.text_input("Ścieżka do CSV", value=DEFAULT_PATH)
        if path and os.path.exists(path):
            df = load_csv(path)
            used_source = path
        else:
            st.sidebar.warning("Podana ścieżka nie istnieje. Użyj 'Wskaż plik'.")
    else:
        up = st.sidebar.file_uploader("Wgraj CSV (UTF-8, separator ';')", type=["csv"])
        if up is not None:
            df = load_csv(up)
            used_source = "plik wgrany"

except Exception as e:
    st.error(f"Problem z wczytaniem danych: {e}")

if df is None:
    st.info("➡️ Wskaż CSV po lewej (sidebar), aby kontynuować.")
    st.stop()

st.sidebar.success(f"Wczytano: {used_source}")
st.title("🍟 Fastfood — wybór produktów i sumy 'per portion'")

# --- FILTRY: kategoria + szukajka ---
left, right = st.columns([1,2])
with left:
    cats = ["(wszystkie)"] + sorted(df["Kategoria"].dropna().astype(str).unique().tolist())
    cat = st.selectbox("Kategoria", cats)

with right:
    q = st.text_input("Szukaj produktu (fragment nazwy)", "")

filtered = df.copy()
if cat != "(wszystkie)":
    filtered = filtered[filtered["Kategoria"].astype(str) == cat]
if q.strip():
    filtered = filtered[filtered["Produkt"].astype(str).str.contains(q.strip(), case=False, na=False)]

if filtered.empty:
    st.warning("Brak produktów po zastosowaniu filtrów.")
    st.stop()

# --- LISTA WYBORU: multi-select produktów ---
# przygotuj listę etykiet: "Produkt (kcal_per_portion kcal)"
labels = (filtered["Produkt"].astype(str) + 
          filtered["kcal_per_portion"].apply(lambda x: f"  ({x:.0f} kcal)" if pd.notna(x) else "  (?)")).tolist()
# mapowanie etykieta -> index
label_to_idx = dict(zip(labels, filtered.index))

st.subheader("Wybierz produkty")
selected_labels = st.multiselect("Produkty (możesz zaznaczyć wiele)", labels)

if not selected_labels:
    st.info("Zaznacz przynajmniej jeden produkt, by zobaczyć podsumowanie.")
    st.stop()

sel_idx = [label_to_idx[l] for l in selected_labels]
sel = filtered.loc[sel_idx].copy()


# === ILOC PORCJI (krok 0,5) ===
# Klucz ilości: stabilny i czytelny (kategoria+produkt)
def qty_key(row):
    return f"qty::{row['Kategoria']}::{row['Produkt']}"
# Edytor ilości – po jednej kontroli na produkt
st.markdown("**Ilości porcji (możesz wpisać np. 0.5, 1, 2):**")
quantities = {}
for idx, row in sel.iterrows():
    key = qty_key(row)
    # domyślnie 1.0; step 0.5
    q = st.number_input(
        f"{row['Produkt']}", min_value=0.0, value=1.0, step=0.5, key=key
    )
    quantities[idx] = q

# Zbuduj ramkę z ilościami
sel_q = sel.copy()
sel_q["quantity"] = sel_q.index.map(lambda i: float(quantities.get(i, 0.0)))

# Uporządkuj NaN w kolumnach liczbowych, żeby mnożenie nie wybuchało
for c in ["kJ_per_portion","kcal_per_portion","fat_per_portion","kwasy_per_portion",
          "carbs_per_portion","sugar_per_portion","protein_per_portion","salt_per_portion"]:
    sel_q[c] = pd.to_numeric(sel_q[c], errors="coerce").fillna(0.0)

# --- PODGLĄD WYBORU ---
st.markdown("**Zaznaczone pozycje:**")
st.dataframe(
    sel[["Kategoria","Produkt","kcal_per_portion","kJ_per_portion",
         "fat_per_portion","kwasy_per_portion",
         "carbs_per_portion","sugar_per_portion",
         "protein_per_portion","salt_per_portion"]]
    .rename(columns={
        "kcal_per_portion":"kcal/porcję",
        "kJ_per_portion":"kJ/porcję",
        "fat_per_portion":"tłuszcz/porcję [g]",
        "kwasy_per_portion":"kwasy nasycone/porcję [g]",
        "carbs_per_portion":"węgle/porcję [g]",
        "sugar_per_portion":"cukry/porcję [g]",
        "protein_per_portion":"białko/porcję [g]",
        "salt_per_portion":"sól/porcję [g]",
    }),
    use_container_width=True
)

# --- SUMY PER PORTION ---
totals = {
    "kJ":       np.nansum(sel["kJ_per_portion"].values),
    "kcal":     np.nansum(sel["kcal_per_portion"].values),
    "Tłuszcz [g]": np.nansum(sel["fat_per_portion"].values),
    "Kwasy nasycone [g]": np.nansum(sel["kwasy_per_portion"].values),
    "Węgle [g]": np.nansum(sel["carbs_per_portion"].values),
    "Cukry [g]": np.nansum(sel["sugar_per_portion"].values),
    "Białko [g]": np.nansum(sel["protein_per_portion"].values),
    "Sól [g]":  np.nansum(sel["salt_per_portion"].values),
}

# --- PODSUMOWANIE ---

# === 4 GŁÓWNE WYNIKI (uwzględniają quantity) ===
kcal_total    = float(np.nansum(sel_q["kcal_per_portion"]    * sel_q["quantity"]))
protein_total = float(np.nansum(sel_q["protein_per_portion"] * sel_q["quantity"]))
fat_total     = float(np.nansum(sel_q["fat_per_portion"]     * sel_q["quantity"]))
carbs_total   = float(np.nansum(sel_q["carbs_per_portion"]   * sel_q["quantity"]))

st.subheader("Podsumowanie – kluczowe (z ilościami)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Kcal",            f"{kcal_total:.0f}")
c2.metric("Białko [g]",      f"{protein_total:.1f}")
c3.metric("Tłuszcze [g]",    f"{fat_total:.1f}")
c4.metric("Węglowodany [g]", f"{carbs_total:.1f}")



# === DETALE – mniejsza czcionka (nie rzuca się w oczy) ===
kj_total     = float(np.nansum(sel_q["kJ_per_portion"]     * sel_q["quantity"]))
sugar_total  = float(np.nansum(sel_q["sugar_per_portion"]  * sel_q["quantity"]))
satfat_total = float(np.nansum(sel_q["kwasy_per_portion"]  * sel_q["quantity"]))
salt_total   = float(np.nansum(sel_q["salt_per_portion"]   * sel_q["quantity"]))

st.caption("Szczegóły (z ilościami):")
st.caption(f"• Energia: {kj_total:.0f} kJ")
st.caption(f"• Kwasy nasycone: {satfat_total:.1f} g")
st.caption(f"• Cukry: {sugar_total:.1f} g")
st.caption(f"• Sól: {salt_total:.2f} g")


# === PASKI RWS (kolorowe, pod metrykami) ===

#2a) prosty CSS dla pasków 
st.markdown("""
<style>
.rws-wrap { margin-top: 6px; }
.rws-track { background: #bcbcbc; border-radius: 8px; height: 10px; width: 100%; }
.rws-fill { height: 10px; border-radius: 8px; }
.rws-text { font-size: 0.9rem; margin-top: 4px; color: #666; }
</style>
""", unsafe_allow_html=True)

# 2b) Pomocnik: rysuje pasek i podpis "X / RWS (Y%)"
def render_rws_bar(container, current, target, color, unit):
    # zabezpieczenie: target > 0
    target = float(target) if target and target > 0 else 1.0
    pct = max(0.0, min(current / target, 1.0)) * 100.0  # 0–100%
    # opis pod paskiem: np. "23.0 g / 60 g (38%)"
    txt = f"{current:.1f}{unit} / {target:.0f}{unit} ({(current/target)*100:.0f}%)"
    html = f'''
    <div class="rws-wrap">
      <div class="rws-track">
        <div class="rws-fill" style="width:{pct:.1f}%; background:{color};"></div>
      </div>
      <div class="rws-text">{txt}</div>
    </div>
    '''
    container.markdown(html, unsafe_allow_html=True)
    
# Kolory: wybierzemy kontrastowe i czytelne
render_rws_bar(c1, kcal_total,    RWS["kcal"],      color="#FF6B6B", unit=" kcal")
render_rws_bar(c2, protein_total, RWS["protein_g"], color="#4CAF50", unit=" g")
render_rws_bar(c3, fat_total,     RWS["fat_g"],     color="#FFC107", unit=" g")
render_rws_bar(c4, carbs_total,   RWS["carbs_g"],   color="#42A5F5", unit=" g")

    

# --- DODATKOWO: eksport wyboru ---
st.download_button(
    "Pobierz zaznaczone (CSV)",
    data=sel.to_csv(index=False).encode("utf-8"),
    file_name="wybrane_produkty.csv",
    mime="text/csv"
)
