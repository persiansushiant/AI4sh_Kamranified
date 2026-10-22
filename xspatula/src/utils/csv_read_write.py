"""
@file csv_read_write.py

@brief Utilities for reading and writing CSV, Excel, and text files.

@author thomasgumbricht
@date Created on 4 Jan 2024
"""

# Standard library imports
import csv
import json
from os import path

# Third-party imports
import pandas as pd

# Application imports
from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


def Read_csv(FPN, mode='r'):
    """
    Read a CSV file and return its headers and data rows.

    Return None if the file does not exist.
    Other reading errors propagate to the caller.
    """
    if not path.exists(FPN):
        msg = ' ❌ ERROR - csv file not found:\n     %s' % FPN

        print(msg)

        return None

    with open(FPN, mode) as csv_file:
        csvreader = csv.reader(csv_file)

        column_L = next(csvreader)
        data_L_L = [row for row in csvreader]

    return column_L, data_L_L


def Read_excel(FPN):
    """
    Read an Excel workbook and return its columns and row values.

    Return None when reading fails.
    Replace missing cell values with the string "null".
    """
    services().log(
        section="excel",
        status="info",
        message=_format_trace_message(
            "Checking Excel source file",
            {
                "source_file": FPN,
                "file_exists": path.exists(FPN),
            },
        ),
    )

    if not path.exists(FPN):
        services().log(
            section="excel",
            status="error",
            message=_format_trace_message(
                "Excel source file was not found",
                {
                    "source_file": FPN,
                    "file_exists": False,
                },
            ),
        )
        return None

    try:
        file_size_bytes = path.getsize(FPN)

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Reading Excel workbook",
                {
                    "source_file": FPN,
                    "file_type": path.splitext(
                        FPN
                    )[1].lower().lstrip("."),
                    "file_size_bytes": file_size_bytes,
                },
            ),
        )

        result = pd.read_excel(FPN)

        column_L = list(result.columns.values)

        data_L_L = [
            [
                value if pd.notna(value) else "null"
                for value in row
            ]
            for row in result.values.tolist()
        ]

        services().log(
            section="excel",
            status="success",
            message=_format_trace_message(
                "Excel workbook read successfully",
                {
                    "source_file": FPN,
                    "rows": len(data_L_L),
                    "columns": len(column_L),
                    "column_names": column_L,
                    "preview": result.head(3).where(
                        pd.notna(result.head(3)),
                        None,
                    ).to_dict(orient="records"),
                },
            ),
        )

        return column_L, data_L_L

    except Exception as error:
        services().log(
            section="excel",
            status="error",
            message=_format_trace_message(
                "Excel workbook could not be read",
                {
                    "source_file": FPN,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None


def Write_txt_L(FPN, data_L):
    """
    Write strings exactly as supplied, without adding line breaks.

    Overwrite the destination file.
    Parent directories must already exist.
    """
    with open(FPN, 'w') as txt_file:
        for line in data_L:
            txt_file.write(line)


def Write_csv_header_data(
    FPN,
    column_L,
    data_L_L,
    mode='w',
    lineterminator='\n',
):
    """
    Write a CSV header followed by data rows.

    Parent directories must already exist.
    The default mode overwrites the destination file.
    """
    with open(FPN, mode, newline='') as csv_file:
        csvwriter = csv.writer(
            csv_file,
            lineterminator=lineterminator,
        )

        csvwriter.writerow(column_L)
        csvwriter.writerows(data_L_L)