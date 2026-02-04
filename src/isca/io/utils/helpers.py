"""This module provides a set of helpers to be used by any input/output interfaces"""

import pathlib
from typing import Callable, Sequence
import pandas as pd
import zipfile


def load_excel(
    file: pathlib.Path,
    sheet_name: str,
    names: list[str] | None = None,
    skiprows: Sequence[int] | int | Callable[[int], object] | None = None,
) -> pd.DataFrame:
    """Wrapper to load an excel file (xlsx/xls) to a dataframe

    Parameters
    ----------
    file : pathlib.Path
        The file containing the spreadshit
    sheet_name : str
        The sheet name
    names : list[str], optional
        The list of wanted columns (if None, all of them)
    skiprows : Sequence[int] | int | Callable[[int], object] | None, optional
        The number of rows to skip

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
        df = pd.read_excel(file, engine="openpyxl", sheet_name=sheet_name, header=header, names=names, skiprows=skiprows)  # XLSX
    except zipfile.BadZipFile:
        pass

    if df is None:
        df = pd.read_excel(file, sheet_name=sheet_name, header=header, names=names, skiprows=skiprows)  # XLS

    return df
