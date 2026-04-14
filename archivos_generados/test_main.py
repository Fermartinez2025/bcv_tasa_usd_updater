# File: test_main.py
import sys
import types
import datetime
import pandas as pd
import pytest
from pathlib import Path
from main import extraer_tasa_usd, truncar_decimal_desde_texto

def test_extraer_tasa_usd_pandas_success(tmp_path, monkeypatch):
    # Crear archivo dummy (contenido no usado por el fake ExcelFile)
    fp = tmp_path / "dummy.xls"
    fp.write_bytes(b"dummy content")

    # Construir DataFrame con estructura esperada por el código
    # Debe tener al menos 8 filas para poder ubicar la fila de fecha en indice 5
    rows = []
    for i in range(10):
        # crear 7 columnas (0..6)
        rows.append([ "" for _ in range(7) ])

    # fila índice 5 -> Fecha Operacion en columna 0 y fecha en columna 2
    rows[5][0] = "Fecha Operacion"
    rows[5][2] = "12/12/2025"

    # fila con USD en columna 1 y valores en columnas 5 y 6
    rows[7][1] = "USD"
    rows[7][5] = "123.4567"
    rows[7][6] = "125,4321"  # usar coma para probar reemplazo

    df = pd.DataFrame(rows)

    class FakeExcelFile:
        def __init__(self, file_like):
            # ignore file_like; parse will return our df
            self.sheet_names = ["Hoja1"]
        def parse(self, sheet, header=None):
            return df

    # Monkeypatch pandas.ExcelFile used in main
    monkeypatch.setattr("main.pd.ExcelFile", FakeExcelFile)

    compra, venta, fecha = extraer_tasa_usd(str(fp))

    assert isinstance(fecha, datetime.date)
    assert fecha == datetime.date(2025, 12, 12)
    # truncar_decimal_desde_texto rounds to 4 decimals
    assert round(compra, 4) == 123.4567
    # venta string used comma; function should handle it and round
    assert round(venta, 4) == 125.4321

def test_extraer_tasa_usd_pandas_no_usd_raises(tmp_path, monkeypatch):
    fp = tmp_path / "dummy2.xls"
    fp.write_bytes(b"dummy content")

    # DataFrame sin USD
    rows = []
    for i in range(6):
        rows.append(["" for _ in range(7)])
    df = pd.DataFrame(rows)

    class FakeExcelFile:
        def __init__(self, file_like):
            self.sheet_names = ["Hoja1"]
        def parse(self, sheet, header=None):
            return df

    monkeypatch.setattr("main.pd.ExcelFile", FakeExcelFile)

    with pytest.raises(Exception) as exc:
        extraer_tasa_usd(str(fp))
    assert "No se encontraron USD" in str(exc.value)

def test_extraer_tasa_usd_xlrd_fallback(tmp_path, monkeypatch):
    fp = tmp_path / "dummy3.xls"
    fp.write_bytes(b"dummy content")

    # Simular pandas.ExcelFile fallando para forzar fallback a xlrd
    def raise_on_excelfile(file_like):
        raise Exception("pandas cannot read")

    monkeypatch.setattr("main.pd.ExcelFile", raise_on_excelfile)

    # Crear un módulo falso 'xlrd' y colocarlo en sys.modules
    fake_xlrd = types.SimpleNamespace()

    class FakeSheet:
        def __init__(self):
            # crear 8 filas y 7 cols
            self.nrows = 8
            self.ncols = 7
            # crear una matriz de celdas
            self.data = [["" for _ in range(self.ncols)] for _ in range(self.nrows)]
            # fila con FECHA en fila 2 (index 2)
            self.data[2][0] = "Fecha Operacion"
            self.data[2][2] = "13/12/2025"
            # fila con USD en fila 4
            self.data[4][1] = "USD"
            self.data[4][5] = "200.1234"
            self.data[4][6] = "210.5678"
        def cell_value(self, r, c):
            try:
                return self.data[r][c]
            except Exception:
                return ""
    class FakeWB:
        def __init__(self):
            self.sheet = FakeSheet()
        def sheet_by_index(self, idx):
            return self.sheet

    def fake_open_workbook(file_contents=None):
        return FakeWB()

    fake_xlrd.open_workbook = fake_open_workbook

    # Insert fake xlrd into sys.modules under name 'xlrd'
    sys.modules['xlrd'] = fake_xlrd

    try:
        compra, venta, fecha = extraer_tasa_usd(str(fp))
    finally:
        # limpiar sys.modules
        del sys.modules['xlrd']

    assert fecha == datetime.date(2025, 12, 13)
    assert round(compra, 4) == 200.1234
    assert round(venta, 4) == 210.5678

def test_truncar_decimal_desde_texto_variants():
    assert truncar_decimal_desde_texto("123,456789", 4) == round(123.4567, 4)
    assert truncar_decimal_desde_texto("100", 4) == 100.0
    assert truncar_decimal_desde_texto("", 4) == 0.0