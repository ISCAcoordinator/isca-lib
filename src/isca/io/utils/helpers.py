"""This module provides a set of helpers to be used by any input/output interfaces

"""
import pathlib
import pandas as pd
import zipfile


def load_excel(file: pathlib.Path, sheet_name: str, names: list[str] | None = None) -> pd.DataFrame:
    """Wrapper to load an excel file (xlsx/xls) to a dataframe

    Parameters
    ----------
    file : pathlib.Path
        The file containing the spreadshit
    sheet_name : str
        the sheet name
    names : list[str], optional
        the list of wanted columns (if None, all of them)

    Returns
    -------
    pd.DataFrame
        the dataframe filled from the excel spreadsheet data
    """

    if names is not None:
        header = None
    else:
        header = 0

    df = None
    try:
        df = pd.read_excel(file, engine="openpyxl", sheet_name=sheet_name, header=header, names=names)  # XLSX
    except zipfile.BadZipFile:
        pass

    if df is None:
        df = pd.read_excel(file, sheet_name=sheet_name, header=header, names=names)  # XLS

    return df
