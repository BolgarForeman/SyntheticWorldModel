"""A minimal OpenDocument spreadsheet: one sheet, every cell a string (as the real H6 file).

The zip entries are stored uncompressed with a fixed date and a fixed host system, so the
bytes are the same on every platform; the mimetype entry comes first, as ODF requires.

Spec: Work Order 8, answer 1 (the institution register, modelled on H6).
"""

import io
import zipfile
from collections.abc import Sequence
from xml.sax.saxutils import escape

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
)
MANIFEST = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
    'manifest:version="1.2">\n'
    f' <manifest:file-entry manifest:full-path="/" manifest:media-type="{MIMETYPE}"/>\n'
    ' <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>\n'
    ' <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>\n'
    "</manifest:manifest>\n"
)
STYLES = (
    f'<?xml version="1.0" encoding="UTF-8"?>\n<office:document-styles {NS} office:version="1.2"/>\n'
)


def ods_bytes(sheet: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> bytes:
    """Return a one-sheet spreadsheet with a header row, every cell a string.

    Parameters
    ----------
    sheet : str
        The sheet's name.
    header : sequence of str
        The column names.
    rows : sequence of sequences of str
        The rows; an empty string is an empty cell.

    Returns
    -------
    bytes
        The .ods file.

    Spec: Work Order 8, answer 1.
    """
    table = "".join(_row(row) for row in [list(header), *rows])
    content = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n<office:document-content {NS} '
        f'office:version="1.2"><office:body><office:spreadsheet>'
        f'<table:table table:name="{escape(sheet)}">'
        f'<table:table-column table:number-columns-repeated="{len(header)}"/>'
        f"{table}</table:table></office:spreadsheet></office:body></office:document-content>\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name, data in (
            ("mimetype", MIMETYPE),
            ("META-INF/manifest.xml", MANIFEST),
            ("content.xml", content),
            ("styles.xml", STYLES),
        ):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            info.external_attr = 0
            archive.writestr(info, data.encode("utf-8"))
    return buffer.getvalue()


def _row(values: Sequence[str]) -> str:
    cells = "".join(
        '<table:table-cell office:value-type="string">'
        f"<text:p>{escape(value)}</text:p></table:table-cell>"
        if value
        else "<table:table-cell/>"
        for value in values
    )
    return f"<table:table-row>{cells}</table:table-row>"
