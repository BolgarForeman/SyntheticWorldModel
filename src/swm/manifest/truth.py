"""The truth manifest: what is really there, apart from the sources (structure v0.10 §4.8).

One YAML file per world, under ``truth/``, which the pipeline is never pointed at. It holds:
- the planted errors (none in Phase 1: a zero-error emission, and it says so);
- every unobserved value with its target and levers: subtypes, requirements, reserves,
  backup, tolerance, failure modes, coupling strength, repair and crews;
- the hidden layers and couplings, the links nodes-only sources withhold, and the feeds with
  their road routes;
- the cross-source correspondence: each true element's record in every file and view;
- the true geometry: locations, outlines' corners and centres, routes and tower points;
- the scored and context attribute lists per source, and the declared departures;
- θ* by registry fingerprint, with the Theta List; the seeds and the spawn tree.

Spec: structure v0.10 §4.8; Work Order 8, Part C; Emission ruling sheet v0.2, E7.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any

from swm.coordinates import to_lonlat
from swm.emit.observed import ObservedWorld
from swm.emit.sources import EmittedSources
from swm.recipe.schema import (
    RECORDED_NOT_APPLIED,
    Layer,
    LayerState,
    Recipe,
    Source,
    errors_above_zero,
)
from swm.rng import StreamRecord
from swm.rules.registry import Registry
from swm.rules.theta import theta_list
from swm.stages.buffers import BuffersResult, buffer_tables
from swm.stages.couplings import CouplingsResult, dependency_table, edge_table
from swm.stages.crews import CrewsResult, crews_tables
from swm.stages.emission import AREA_CLASSES, outline_m
from swm.stages.layers import LayersResult
from swm.stages.repair import RepairResult, repair_tables
from swm.stages.requirements import RequirementsResult, requirement_table
from swm.stages.strength import StrengthResult, strength_tables

SCORED: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "openstreetmap": (
        ("location", "class (tags)", "plant:output:electricity", "voltage", "line end points"),
        ("name", "operator", "beds", "plant:source", "plant:method", "circuits", "cables",
         "the remaining tags"),
    ),
    Source.WRI_GPPD.value: (
        ("latitude", "longitude", "capacity_mw", "primary_fuel"),
        ("name", "gppd_idnr", "country", "country_long", "the empty columns"),
    ),
    Source.OURAIRPORTS.value: (
        ("latitude_deg", "longitude_deg", "type", "scheduled_service"),
        ("name", "ident", "iso_country", "iso_region", "municipality", "continent"),
    ),
    Source.FACILITY_REGISTER.value: (
        ("location (地址)", "class", "level (特約類別; which list)", "beds (急性病床數)"),
        ("name", "institution code", "county and district", "departments", "the other columns"),
    ),
}  # fmt: skip
"""Scored and context attributes per source (E6; structure v0.10 §4.6)."""

DEPARTURES = (
    "Facility register: latitude and longitude stand in the address column (E5); addresses, a "
    "gazetteer and the geocoder come in Phase 6.",
    "Names are in English only (E4); bilingual names come later.",
    "Footprints are axis-aligned rectangles centred on the true location (E2).",
    "PBF blobs are stored uncompressed, which the format allows, so the file is identical on "
    "every platform (A5); Geofabrik's extracts are compressed.",
    "Facility register coordinates are at 6 decimals, a choice: the real files carry addresses, "
    "so there is no precision to measure (§4.1a).",
    "Columns the world does not hold are left empty: WRI's commissioning_year and owner (Phase 6 "
    "draws them at fill rates measured from the real file; structure v0.11 §4.6).",
    "Overpass: TWN_Hospital, TWN_Industrial and TWN_Telecom_OSM_Overpass are inferred from "
    "landed tags, query text not saved; they are replaced when the pipeline supplies the text.",
    "The institution register's file is named in ASCII; the real one is named in Chinese.",
    "Source overlap (assets missing from one of two sources) is Phase 3: in Phase 1 every true "
    "element in a source's scope appears in it.",
)


@dataclass(frozen=True)
class TruthInputs:
    """Everything the manifest records."""

    recipe: Recipe
    rules: Registry
    layers: LayersResult
    requirements: RequirementsResult
    couplings: CouplingsResult
    strength: StrengthResult
    buffers: BuffersResult
    crews: CrewsResult
    repair: RepairResult
    observed: ObservedWorld
    sources: EmittedSources
    streams: StreamRecord


def truth_manifest(inputs: TruthInputs) -> dict[str, object]:
    """Return the truth manifest as plain data, in a fixed key order.

    Parameters
    ----------
    inputs : TruthInputs
        The recipe, the registry, every stage's output, the observed world and the emitted
        sources, and the stream record.

    Returns
    -------
    dict
        Plain data for canonical YAML.

    Spec: structure v0.10 §4.8; Work Order 8, C1.
    """
    recipe = inputs.recipe
    return {
        "planted_errors": {"status": "zero-error emission (Phase 1)", "errors": []},
        "correspondence": correspondence(inputs.sources),
        "geometry": _geometry(inputs),
        "unobserved": _unobserved(inputs),
        "hidden": _hidden(inputs),
        "scored_and_context": {
            source: {"scored": list(scored), "context": list(context)}
            for source, (scored, context) in SCORED.items()
        },
        "declared_departures": [*DEPARTURES, *_phase_1_errors(recipe)],
        "theta": {
            "registry_version": inputs.rules.version,
            "registry_sha256": inputs.rules.sha256,
            "overrides": dict(recipe.modeling_rules.overrides),
            "relaxed_limits": list(recipe.modeling_rules.relaxed_limits),
            "theta_list": [_entry(e) for e in theta_list(inputs.rules)],
        },
        "seeds": {
            "root_seed": recipe.root_seed,
            "terrain_seed": recipe.terrain.terrain_seed,
            "spawn_tree": [
                {"path": s["path"], "spawn_key": s["spawn_key"]} for s in inputs.streams["streams"]
            ],
        },
    }


def _phase_1_errors(recipe: Recipe) -> list[str]:
    """Declare the error settings Phase 1 records but does not apply (WO-09 C2)."""
    sources = errors_above_zero(recipe.errors)
    if not sources:
        return []
    return [f"{RECORDED_NOT_APPLIED[0].upper()}{RECORDED_NOT_APPLIED[1:]}: {', '.join(sources)}."]


def correspondence(sources: EmittedSources) -> list[dict[str, object]]:
    """Return every true element's record in each file and view, sorted by the world's id.

    Parameters
    ----------
    sources : EmittedSources
        The emitted files and each writer's records.

    Returns
    -------
    list of dict
        One entry per true element: its id and, per source, its record.

    Spec: Work Order 8, C1 (cross-source correspondence).
    """
    entries: dict[str, dict[str, object]] = {}
    # OpenStreetMap's node and way ids are separate spaces that overlap here: match on both.
    shapefiles = {(r.osm_type, r.osm_id): r for r in sources.geofabrik}
    for element in sources.osm.elements:
        record: dict[str, object] = {"kind": element.kind}
        for name in ("node", "way", "anchor"):
            value = getattr(element, name)
            if value is not None:
                record[name] = value
        if element.corners:
            record["corners"] = list(element.corners)
        if element.towers:
            record["towers"] = list(element.towers)
        osm_type, osm_id = (
            ("way", element.way) if element.way is not None else ("node", element.node)
        )
        if osm_id is None:
            raise ValueError(f"{element.element_id} has neither a node nor a way")
        main = (osm_type, osm_id)
        shapefile = shapefiles.get(main)
        if shapefile is not None:
            record["geofabrik"] = {"layer": shapefile.layer, "fclass": shapefile.fclass}
        queries = sorted(r.query for r in sources.overpass if (r.osm_type, r.osm_id) == main)
        if queries:
            record["overpass"] = queries
        entries.setdefault(element.element_id, {})["openstreetmap"] = record
    for wri in sources.wri:
        entries.setdefault(wri.node_id, {})[Source.WRI_GPPD.value] = {"gppd_idnr": wri.gppd_idnr}
    for airport in sources.airports:
        entries.setdefault(airport.node_id, {})[Source.OURAIRPORTS.value] = {
            "id": airport.row_id, "ident": airport.ident}  # fmt: skip
    for code in sources.register:
        entries.setdefault(code.node_id, {})[Source.FACILITY_REGISTER.value] = {
            "code": code.code, "files": list(code.files)}  # fmt: skip
    return [{"element": element_id, **entries[element_id]} for element_id in sorted(entries)]


def _geometry(inputs: TruthInputs) -> dict[str, object]:
    rules, seed = inputs.rules, inputs.recipe.root_seed
    nodes = []
    for node in sorted(inputs.layers.nodes, key=lambda n: n.node_id):
        entry: dict[str, object] = {
            "node": node.node_id,
            "location": [node.longitude, node.latitude],
            "epsg_32710": [round(node.x_m, 3), round(node.y_m, 3)],
        }
        if node.node_class in AREA_CLASSES:
            corners = outline_m(node, rules, seed)
            entry["outline"] = {
                "centre": [node.longitude, node.latitude],
                "corners": [list(to_lonlat(x, y)) for x, y in corners],
            }
        nodes.append(entry)
    lines = {line.link_id: line for line in inputs.layers.power_lines}
    links = []
    for link in sorted(inputs.layers.links, key=lambda link: link.link_id):
        record: dict[str, object] = {
            "link": link.link_id,
            "route": [list(to_lonlat(x, y)) for x, y in link.points],
        }
        if link.link_id in lines:
            record["towers"] = [list(to_lonlat(x, y)) for x, y in lines[link.link_id].tower_points]
        links.append(record)
    feeds = [
        {"edge": edge.edge_id, "route": [list(to_lonlat(x, y)) for x, y in edge.route]}
        for edge in inputs.couplings.edges
        if edge.route
    ]
    return {"nodes": nodes, "links": links, "feeds": feeds}


def _unobserved(inputs: TruthInputs) -> dict[str, object]:
    unobserved = inputs.recipe.unobserved
    return {
        "levers": unobserved.model_dump(mode="json"),
        "subtypes": [
            {"node": n.node_id, **{k: v for k, v in n.subtype}}
            for n in sorted(inputs.layers.nodes, key=lambda n: n.node_id)
            if n.subtype
        ],
        "requirements": requirement_table(inputs.requirements),
        "strength": strength_tables(inputs.strength),
        "buffers": buffer_tables(inputs.buffers),
        "crews": crews_tables(inputs.crews),
        "repair": repair_tables(inputs.repair),
    }


def _hidden(inputs: TruthInputs) -> dict[str, object]:
    recipe = inputs.recipe
    hidden_layers = [
        layer.value for layer in Layer if recipe.layers.get(layer).state != LayerState.EMITTED
    ]
    edges = edge_table(inputs.couplings)

    # A coupling is hidden when it is switched off, or when either end's layer is hidden: no
    # source shows a hidden layer, so none shows its couplings (WO-09 B3).
    def hidden(row: Mapping[str, object]) -> bool:
        ends = (row.get("supplier_layer"), row.get("consumer_layer"))
        return not row.get("switched_on") or any(end in hidden_layers for end in ends)

    return {
        "layers": hidden_layers,
        "couplings": [row for row in edges if hidden(row)],
        "switched_on_couplings": [row for row in edges if not hidden(row)],
        "dependencies": dependency_table(inputs.couplings),
        "withheld_links": [
            {"link": link.link_id, "layer": link.layer.value}
            for link in sorted(inputs.layers.links, key=lambda link: link.link_id)
            if link.layer in inputs.observed.nodes_only
        ],
    }


def _entry(entry: Any) -> dict[str, object]:
    record: dict[str, object] = {}
    for item in fields(entry):
        value = getattr(entry, item.name)
        if hasattr(value, "value"):
            value = value.value
        elif isinstance(value, tuple):
            value = list(value)
        elif item.name == "ruling" and value is not None:
            value = {"by": value.by, "date": value.date, "decision": value.decision}
        record[item.name] = value
    return record


def node_ids(manifest: Mapping[str, Any]) -> Sequence[str]:
    """Return the true elements the manifest's correspondence lists (for tests)."""
    return [entry["element"] for entry in manifest["correspondence"]]
