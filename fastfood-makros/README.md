
# FastFood Optimizer — Starter (Spyder / Miniconda)

## Kroki (po Twoim punkcie 2 — Spyder działa)
1. Pobierz i rozpakuj ten starter w wygodne miejsce (np. `C:\fastfood-optimizer`).
2. W Spyderze: **File → Open Project** → wskaż folder projektu.
3. Jeśli masz dane w **XLSX**, otwórz `convert_from_xlsx.py`, ustaw ścieżkę do swojego pliku (SRC_XLSX), popraw COL_MAP i uruchom (F5). Powstanie `data/items_kfc.csv`.
   - Jeśli masz już gotowy CSV z wymaganymi nagłówkami, po prostu wklej go jako `data/items_kfc.csv`.
4. Uruchom `launch_streamlit.py` (F5). Aplikacja otworzy się w przeglądarce.

## Wymagane nagłówki CSV
```
item_name,portion_desc,portion_g,kcal,protein_g,carbs_g,fat_g,sugar_g,sodium_mg,price_pln
```

## Typowe problemy
- **ModuleNotFoundError** → uruchom Spydera z aktywnego środowiska conda: `conda activate fastfood` → `spyder`.
- **Złe liczby** → użyj kropek zamiast przecinków jako separatora dziesiętnego.
- **Brak cen** → możesz je dopisać później w CSV; optymalizacja ILP wymaga `price_pln`.

Powodzenia!
