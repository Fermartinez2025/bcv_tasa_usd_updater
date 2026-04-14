import pandas as pd
import xlrd
import sys

filepath = r'c:\Users\fmartinez\Documents\bcv_tasa_usd_updater\logs\2_1_2b26_smc.xls'

print("--- INSPECCIONANDO CON PANDAS ---")
try:
    df = pd.read_excel(filepath, header=None).fillna("")
    for i in range(min(15, len(df))):
        print(f"Fila {i}: {df.iloc[i].tolist()[:10]}")
except Exception as e:
    print(f"Error con Pandas: {e}")

print("\n--- INSPECCIONANDO CON XLRD ---")
try:
    wb = xlrd.open_workbook(filepath)
    sheet = wb.sheet_by_index(0)
    for r in range(min(15, sheet.nrows)):
        row = [sheet.cell_value(r, c) for c in range(min(10, sheet.ncols))]
        print(f"Fila {r}: {row}")
except Exception as e:
    print(f"Error con xlrd: {e}")
