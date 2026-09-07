# -*- coding: utf-8 -*-
"""
Created on Sun Aug 31 19:28:29 2025

@author: PC
"""

import pandas as pd
import matplotlib.pyplot as plt

p = r"C:\Users\PC\Desktop\Projekty\Tabela wartości\fastfood-optimizer-starter-v2\data\items_kfc.csv"

df = pd.read_csv(p, sep=';',encoding='utf-8-sig')

# 3) Higiena nagłówków (BOM/spacje)
df.columns = df.columns.str.replace('\ufeff', '', regex=False).str.strip()

# 4) Opcjonalne mapowanie nazw, jeśli w Twoim pliku są inne etykiety
rename_map = {}
if 'Produkt' not in df.columns:
    for cand in ['product', 'Product', 'Nazwa', 'item_name']:
        if cand in df.columns:
            rename_map[cand] = 'Produkt'
            break

if 'kcal_per_portion' not in df.columns:
    for cand in ['kcal', 'kcal_na_porcję', 'kcal_na_porcje', 'kcal_na_porcji', 'kcal_per_portion ']:
        if cand in df.columns:
            rename_map[cand] = 'kcal_per_portion'
            break

df = df.rename(columns=rename_map)

# 5) Twarda walidacja: te dwie kolumny muszą istnieć
missing = {'Produkt', 'kcal_per_portion'} - set(df.columns)
if missing:
    raise ValueError(f"Brakuje kolumn: {missing}. Sprawdź nagłówki albo zaktualizuj 'rename_map' powyżej.")

# 6) Konwersja kolumny kcal_per_portion na liczby (kropki zamiast przecinków, usunięcie spacji)
df['kcal_per_portion'] = (df['kcal_per_portion'].astype(str)
                          .str.replace(',', '.', regex=False)
                          .str.replace('\xa0', '', regex=False)
                          .str.replace(' ', '', regex=False))
df['kcal_per_portion'] = pd.to_numeric(df['kcal_per_portion'], errors='coerce')

# 7) Dane do wykresu: top 15 po kcal
plot_df = (df[['Produkt', 'kcal_per_portion']]
           .dropna()
           .sort_values('kcal_per_portion', ascending=False)
           .head(15))

# 8) Wykres (czysty matplotlib, bez kolorów specjalnych)
plt.figure(figsize=(10, 6))
plt.bar(plot_df['Produkt'], plot_df['kcal_per_portion'])
plt.xticks(rotation=45, ha='right')
plt.xlabel('Produkt')
plt.ylabel('kcal na porcję')
plt.title('Top 15 produktów wg kcal na porcję')
plt.tight_layout()
plt.show()

# (opcjonalnie) zapis do pliku:
# plt.savefig('kcal_top15.png', dpi=150)



print(df.columns.tolist())



#import sys
#print(sys.executable)
#!"{sys.executable}" -m pip install -U matplotlib
