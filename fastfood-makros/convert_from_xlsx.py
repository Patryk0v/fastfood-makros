
"""
Konwerter XLSX -> CSV (items_kfc.csv) dla aplikacji FastFood Optimizer.

Użycie w Spyderze:
1) Upewnij się, że masz plik źródłowy XLSX (np. kfc_tables_all.xlsx).
2) Uzupełnij poniżej ścieżki i mapowanie kolumn 'COL_MAP' zgodnie z Twoim arkuszem.
3) Uruchom (F5). W folderze 'data/' powstanie items_kfc.csv.
"""

import pandas as pd
from pathlib import Path

# ---- USTAWIENIA ----
SRC_XLSX = r"C:\Users\PC\Desktop\Projekty\Tabela wartości\kfc_tables_all.xlsx"   # <- PODMIEŃ jeśli plik jest gdzie indziej
SHEET_NAME = 0                                # nazwa lub indeks arkusza
OUT_CSV = Path(__file__).resolve().parent / "data" / "items_kfc.csv"

# Mapa kolumn w Twoim XLSX -> wymagane kolumny aplikacji
# Po prawej NAZWY KOLUMN DOCELOWYCH (NIE ZMIENIAJ), po lewej wpisz nazwy kolumn z Twojego pliku.
COL_MAP = {
    "item_name": "item_name",         # Np. "Nazwa"
    "portion_desc": "portion_desc",   # Np. "Porcja"
    "portion_g": "portion_g",         # Np. "g"
    "kcal": "kcal",
    "protein_g": "protein_g",
    "carbs_g": "carbs_g",
    "fat_g": "fat_g",
    "sugar_g": "sugar_g",
    "sodium_mg": "sodium_mg",
    "price_pln": "price_pln",         # jeśli nie masz cen, wpisz ręcznie po eksporcie
}

# ---- LOGIKA ----
df_x = pd.read_excel(SRC_XLSX, sheet_name=SHEET_NAME)
print("Kolumny w XLSX:", list(df_x.columns))

# Jeśli Twoje nagłówki różnią się, podmień wartości w COL_MAP po lewej stronie na istniejące nazwy kolumn
required = list(COL_MAP.keys())
# Odwróć mapowanie: źródło->cel
src_to_target = {}
for target_col in required:
    src_col = COL_MAP[target_col]
    if src_col not in df_x.columns:
        print(f"[!] Brakuje kolumny w XLSX: {src_col}. Zaktualizuj COL_MAP.")
        raise SystemExit(1)
    src_to_target[src_col] = target_col

df_out = df_x[list(src_to_target.keys())].rename(columns=src_to_target)

# Sanitization: zamień przecinki na kropki, na liczby
for c in ["portion_g","kcal","protein_g","carbs_g","fat_g","sugar_g","sodium_mg","price_pln"]:
    if c in df_out.columns:
        df_out[c] = pd.to_numeric(df_out[c].astype(str).str.replace(",", "."), errors="coerce")

# Zapis
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df_out.to_csv(OUT_CSV, index=False, encoding="utf-8")
print(f"Zapisano: {OUT_CSV}")
