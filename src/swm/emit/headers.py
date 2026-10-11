"""The real files' column headers, recorded as schema (Work Order 8, B1).

A header is schema, not data: each is copied from the real file the pipeline lands, with its
source and version, and checked against the file once through ``machine.toml``
(``tools/check_source_headers.py``). No real row enters the repository.

Spec: Work Order 8, B1 and answer 1; CLAUDE.md §9.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordedHeader:
    """A real file's header and where it was recorded from."""

    source: str
    real_file: str
    """Path under the data root (``machine.toml``)."""
    version: str
    columns: tuple[str, ...]
    coordinate_columns: tuple[str, ...] = ()
    """The latitude and longitude columns, if the real file carries coordinates."""
    coordinate_decimals: int | None = None
    """Decimal places of those coordinates, measured from the real file (the most common count)."""
    decimals_measured: str | None = None
    """When the count was measured, through ``machine.toml`` (``tools/check_source_headers.py``)."""


WRI_GPPD = RecordedHeader(
    "WRI Global Power Plant Database v1.3 (global_power_plant_database.csv)",
    "WRI_GPPD/raw/global_power_plant_database_20260220.csv",
    "master, downloaded 2026-02-20",
    (
        "country", "country_long", "name", "gppd_idnr", "capacity_mw", "latitude", "longitude",
        "primary_fuel", "other_fuel1", "other_fuel2", "other_fuel3", "commissioning_year",
        "owner", "source", "url", "geolocation_source", "wepp_id", "year_of_capacity_data",
        "generation_gwh_2013", "generation_gwh_2014", "generation_gwh_2015",
        "generation_gwh_2016", "generation_gwh_2017", "generation_gwh_2018",
        "generation_gwh_2019", "generation_data_source", "estimated_generation_gwh_2013",
        "estimated_generation_gwh_2014", "estimated_generation_gwh_2015",
        "estimated_generation_gwh_2016", "estimated_generation_gwh_2017",
        "estimated_generation_note_2013", "estimated_generation_note_2014",
        "estimated_generation_note_2015", "estimated_generation_note_2016",
        "estimated_generation_note_2017",
    ),
    ("latitude", "longitude"),
    4,
    "2026-10-10: every coordinate in the file has 4 decimals",
)  # fmt: skip

OURAIRPORTS = RecordedHeader(
    "OurAirports airports.csv",
    "OURAIRPORTS/airports.csv",
    "as landed by the pipeline, 2026-02-19",
    (
        "id", "ident", "type", "name", "latitude_deg", "longitude_deg", "elevation_ft",
        "continent", "iso_country", "iso_region", "municipality", "scheduled_service",
        "icao_code", "iata_code", "gps_code", "local_code", "home_link", "wikipedia_link",
        "keywords",
    ),
    ("latitude_deg", "longitude_deg"),
    6,
    "2026-10-10: 6 is the most common count, worldwide and for Taiwan; trailing zeros are "
    "dropped, so shorter values occur",
)  # fmt: skip

INSTITUTION_REGISTER = RecordedHeader(
    "Ministry of Health and Welfare, 醫療機構與人員基本資料 (H6, data.gov.tw 15393)",
    "TW_GOV/MOHW/H6_15393_medical_institution_register/raw/醫療機構與人員基本資料_20241231.ods",
    "2024-12-31",
    (
        "機構代碼", "機構名稱", "電話", "縣市區名", "地址", "科別", "1語言治療師", "2牙體技術師",
        "3聽力師", "4牙體技術士", "5驗光師", "6驗光生", "A醫師", "B中醫師", "C牙醫師", "D藥師",
        "E藥劑生", "F護理師", "G護士", "H助產士", "I助產師", "J醫事檢驗師", "K醫事檢驗生",
        "Q物理治療師", "R職能治療師", "S醫事放射師", "T醫事放射士", "U物理治療生", "W職能治療生",
        "V呼吸治療師", "X諮商心理師", "Y臨床心理師", "Z營養師",
    ),
)  # fmt: skip

HOSPITAL_LISTS = RecordedHeader(
    "National Health Insurance Administration hospital lists (H2-H4, data.gov.tw 39280-39282)",
    "TW_GOV/NHIA/H2_39280_nhi_medical_centers/raw/A21030000I-D21001-003.csv",
    "as landed 2026-09-27; the same header in H3 and H4",
    (
        "醫事機構代碼", "醫事機構名稱", "醫事機構種類", "電話", "地址", "分區業務組", "特約類別",
        "服務項目", "診療科別", "終止合約或歇業日期", "固定看診時段", "備註", "縣市別代碼",
        "合約起日",
    ),
)  # fmt: skip

BEDS = RecordedHeader(
    "National Health Insurance Administration, 全民健保特約醫院之保險病床比率 "
    "(H1, data.gov.tw 9402)",
    "TW_GOV/NHIA/H1_9402_nhi_bed_ratio/raw/A21030000I-D02001-018.csv",
    "as landed 2026-09-27",
    (
        "機構代碼", "統計年月", "特約類別", "機構名稱", "急性保險病床數", "急性病床數", "急性比率",
        "慢性保險病床數", "慢性病床數", "慢性比率",
    ),
)  # fmt: skip

RECORDED = (WRI_GPPD, OURAIRPORTS, INSTITUTION_REGISTER, HOSPITAL_LISTS, BEDS)
"""Every recorded header, for the local check."""
