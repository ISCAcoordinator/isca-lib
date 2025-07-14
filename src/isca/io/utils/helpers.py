import pathlib
import pandas as pd
import zipfile


def load_excel(file: pathlib.Path, sheet_name: str, names: list[str] | None = None) -> pd.DataFrame:

    df = None
    try:
        df = pd.read_excel(file, engine="openpyxl", sheet_name=sheet_name, names=names)  # XLSX
    except zipfile.BadZipFile:
        pass

    if df is None:
        df = pd.read_excel(file, sheet_name=sheet_name, names=names)  # XLS

    return df
