"""The facility register of the island: three real-style file types on one code (answer 1).

Modelled on the files the pipeline lands, with their headers copied exactly (Chinese where the
real ones are) and the values in English:
- **the institution register** (H6, the health ministry's register): every healthcare
  facility, as a one-sheet ODS with every cell a string;
- **the hospital lists** (H2-H4, the national health insurance lists): hospitals only, one file
  per level, the level being which list a hospital is in (medical centre, regional, district);
  UTF-8 with a byte order mark, LF, quoted only where needed;
- **the beds table** (H1): one row per hospital; byte order mark, CRLF, unquoted.

Institution codes are register-style with an ``XS`` prefix (``XS00000001`` …), the same in all
three, so the pipeline's join on the code is exercised. Latitude and longitude stand in the
address column (a declared departure; addresses and a gazetteer come in Phase 6).

Spec: structure v0.11 §4.6 (corrected); Work Order 8, B4 and answer 1; Emission ruling sheet
v0.2, E3-E6.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from swm.emit.delimited import Idiom, delimited
from swm.emit.headers import BEDS, HOSPITAL_LISTS, INSTITUTION_REGISTER
from swm.emit.observed import ObservedNode, ObservedWorld
from swm.emit.ods import ods_bytes
from swm.recipe.schema import SOURCE_SCOPES, Layer, NodeClass, Source

C = NodeClass
REGISTER_FILE = "medical_institution_register.ods"
"""CHOICE: an ASCII stand-in for the real 醫療機構與人員基本資料_20241231.ods."""
SHEET = "medical_institution_register"
LIST_FILES: Mapping[str, str] = {
    "1": "A21030000I-D21001-003.csv",
    "2": "A21030000I-D21002-005.csv",
    "3": "A21030000I-D21003-003.csv",
}
"""The hospital lists by contract class (1 medical centre, 2 regional, 3 district): the real
files' names."""
BEDS_FILE = "A21030000I-D02001-018.csv"
LEVEL = {C.TERTIARY: "1", C.REGIONAL: "2"}
"""Contract class (特約類別) by hospital class. CHOICE: tertiary hospitals are medical centres,
regional ones regional; the world has no district hospitals, so that list is header only."""
FORMAL = {C.TERTIARY: "Medical Centre", C.REGIONAL: "Regional Hospital", C.CLINIC: "Clinic",
          C.BLOOD_BANK: "Blood Centre"}  # fmt: skip
"""The register's formal name words (E4)."""
DEPARTMENTS = {C.TERTIARY: "General Medicine,", C.REGIONAL: "General Medicine,",
               C.CLINIC: "General Medicine,", C.BLOOD_BANK: "Blood Services,"}  # fmt: skip
"""科別, with the real file's trailing comma."""
DECIMALS = 6
"""CHOICE: the register's real files carry addresses, not coordinates, so there is no precision to
measure; its stand-in coordinates take OurAirports' measured 6 decimals (about 0.1 m), the other
point source the pipeline reads, and close to what a geocoder returns for an address (§4.1a)."""
STATISTICS_MONTH = "11412"
"""統計年月 in the real form (Republic of China year and month): CHOICE, December 2025."""

LISTS = Idiom(line_ending="\n", bom=True, quote_text=False)
BEDS_IDIOM = Idiom(line_ending="\r\n", bom=True, quote_text=False)


@dataclass(frozen=True)
class RegisterRecord:
    """One facility's institution code and the files that list it."""

    node_id: str
    code: str
    files: tuple[str, ...]


def register_files(world: ObservedWorld) -> tuple[dict[str, bytes], tuple[RegisterRecord, ...]]:
    """Return the register's files and each facility's code and files.

    Parameters
    ----------
    world : ObservedWorld
        The observed world.

    Returns
    -------
    files : dict of str to bytes
        The institution register, the three hospital lists and the beds table.
    records : tuple of RegisterRecord
        One per facility, in code order.

    Spec: Work Order 8, B4 and answer 1.
    """
    if Source.FACILITY_REGISTER not in world.sources_of(Layer.HEALTHCARE):
        return {}, ()
    scope = SOURCE_SCOPES[Source.FACILITY_REGISTER].classes
    facilities = [n for n in world.nodes if n.layer == Layer.HEALTHCARE and n.node_class in scope]
    codes = {n.node_id: f"XS{i:08d}" for i, n in enumerate(facilities, start=1)}
    hospitals = [n for n in facilities if n.node_class in LEVEL]
    files = {REGISTER_FILE: _institutions(facilities, codes)}
    for level, name in LIST_FILES.items():
        listed = [n for n in hospitals if LEVEL[n.node_class] == level]
        files[name] = delimited(HOSPITAL_LISTS.columns, [_listed(n, codes) for n in listed], LISTS)
    beds = [n for n in hospitals if n.attribute("bed_count") is not None]
    files[BEDS_FILE] = delimited(BEDS.columns, [_beds(n, codes) for n in beds], BEDS_IDIOM)
    records = []
    for node in facilities:
        held = [REGISTER_FILE]
        if node.node_class in LEVEL:
            held.append(LIST_FILES[LEVEL[node.node_class]])
            if node in beds:
                held.append(BEDS_FILE)
        records.append(RegisterRecord(node.node_id, codes[node.node_id], tuple(held)))
    return files, tuple(records)


def _name(node: ObservedNode) -> str:
    return node.name(FORMAL[node.node_class])


def _coordinates(node: ObservedNode) -> str:
    return f"{node.location[1]:.{DECIMALS}f},{node.location[0]:.{DECIMALS}f}"


def _institutions(facilities: list[ObservedNode], codes: Mapping[str, str]) -> bytes:
    columns = INSTITUTION_REGISTER.columns
    rows = []
    for node in facilities:
        values = dict.fromkeys(columns, "")
        values |= {
            "機構代碼": codes[node.node_id],
            "機構名稱": _name(node),
            "縣市區名": node.town,
            "地址": _coordinates(node),
            "科別": DEPARTMENTS[node.node_class],
        }
        rows.append([values[c] for c in columns])
    return ods_bytes(SHEET, columns, rows)


def _listed(node: ObservedNode, codes: Mapping[str, str]) -> list[str | None]:
    values: dict[str, str | None] = dict.fromkeys(HOSPITAL_LISTS.columns)
    values |= {
        "醫事機構代碼": codes[node.node_id],
        "醫事機構名稱": _name(node),
        "醫事機構種類": "General Hospital",
        "地址": _coordinates(node),
        "分區業務組": f"{node.town} Division",
        "特約類別": LEVEL[node.node_class],
        "備註": "-",
        "縣市別代碼": node.district,
    }
    return [values[c] for c in HOSPITAL_LISTS.columns]


def _beds(node: ObservedNode, codes: Mapping[str, str]) -> list[str | int | None]:
    beds = int(str(node.attribute("bed_count")))
    # CHOICE: every bed is an acute, insured bed; the world carries no split.
    values: dict[str, str | int | None] = {
        "機構代碼": codes[node.node_id],
        "統計年月": STATISTICS_MONTH,
        "特約類別": LEVEL[node.node_class],
        "機構名稱": _name(node),
        "急性保險病床數": beds,
        "急性病床數": beds,
        "急性比率": 100,
        "慢性保險病床數": 0,
        "慢性病床數": 0,
        "慢性比率": None,
    }
    return [values[c] for c in BEDS.columns]
