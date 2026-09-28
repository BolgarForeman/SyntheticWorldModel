"""Recipe schema v1: every choice that builds a world, with its type, range, default and meaning.

The field inventory follows the interface mockup v0.5, as amended by the Work Order 1 rulings
(decision 0003). A recipe may leave any field out; the default here applies.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

RECIPE_VERSION: Literal[1] = 1
"""The recipe schema version this module defines."""

SUPPORTED_RECIPE_VERSIONS = (1,)
"""Recipe versions this code reads."""

ROOT_SEED_UPPER_BOUND = 2**64 - 1
"""Largest root or terrain seed (ruling C4, decision 0003)."""

DEFAULT_ROOT_SEED = 91577
"""Default root seed: the mockup's (interface mockup v0.5)."""

FEED_MIX_TOTAL_PCT = 100
"""The feed-mix shares always total exactly this, in percent (structure v0.2 §4.3)."""

ServiceWeight = Annotated[float, Field(ge=0, le=100)]
"""A custom service weight: non-negative, 0-100 (ruling C6, decision 0003)."""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _partial_sections_keep_their_defaults(cls, data: Any) -> Any:
        # A section given in part keeps its own defaults for the rest (fuel stays nodes-only),
        # not the defaults of its settings class.
        if not isinstance(data, dict):
            return data
        merged = dict(data)
        for name, field in cls.model_fields.items():
            value = data.get(name)
            if isinstance(value, dict) and field.default_factory is not None:
                default = field.get_default(call_default_factory=True, validated_data={})
                if isinstance(default, BaseModel):
                    merged[name] = {**default.model_dump(), **value}
        return merged


# --- Enumerations ---------------------------------------------------------------------------


class MapType(StrEnum):
    """The overall shape of the land (the mockup's eleven; ruling B1)."""

    SPINE_ISLAND = "spine_island"
    ARCHIPELAGO = "archipelago"
    CONTINENT = "continent"
    COASTAL_STRIP = "coastal_strip"
    RIVER_DELTA = "river_delta"
    TWIN_ISLANDS = "twin_islands"
    MAINLAND_AND_ISLANDS = "mainland_and_islands"
    PENINSULA = "peninsula"
    MOUNTAIN_BASIN = "mountain_basin"
    ARID_PLATEAU = "arid_plateau"
    LANDLOCKED = "landlocked"


class UrbanPattern(StrEnum):
    """How built-up land is arranged (the mockup's three; ruling B2)."""

    ONE_DOMINANT_CITY = "one_dominant_city"
    SEVERAL_CITIES = "several_cities"
    DISPERSED_TOWNS = "dispersed_towns"


class SizePreset(StrEnum):
    """A starting size that sets the area and every layer's node count together."""

    HAND_CHECK = "hand_check"
    SMALL = "small"
    TAIWAN_SCALE = "taiwan_scale"
    VERY_LARGE = "very_large"
    HUGE = "huge"
    CUSTOM = "custom"


class HoldOnAreaChange(StrEnum):
    """What gives when the area differs from the preset's."""

    DENSITY = "density"
    NODE_COUNTS = "node_counts"


class Layer(StrEnum):
    """The six infrastructure layers."""

    POWER = "power"
    TELECOM = "telecom"
    WATER = "water"
    TRANSPORT = "transport"
    FUEL = "fuel"
    HEALTHCARE = "healthcare"


class LayerState(StrEnum):
    """Whether a layer is in the world and whether it reaches its sources."""

    EMITTED = "emitted"
    HIDDEN = "hidden"
    OFF = "off"


class Source(StrEnum):
    """Real source formats a layer can be emitted to (the mockup's list)."""

    OSM_POWER = "osm_power"
    WRI_GPPD = "wri_gppd"
    OPENINFRAMAP = "openinframap"
    OSM_TELECOM = "osm_telecom"
    SUBMARINE_CABLES = "submarine_cables"
    OSM_WATER = "osm_water"
    DAM_REGISTER = "dam_register"
    OURAIRPORTS = "ourairports"
    WORLD_PORT_INDEX = "world_port_index"
    OSM_ROADS_RAIL = "osm_roads_rail"
    OSM_FUEL = "osm_fuel"
    OSM_PIPELINES = "osm_pipelines"
    LNG_REGISTER = "lng_register"
    OSM_HEALTH = "osm_health"
    HEALTHSITES = "healthsites"
    FACILITY_REGISTER = "facility_register"


class NodeClass(StrEnum):
    """Node classes per layer (the mockup's per-layer class strings; ruling C6)."""

    GENERATION = "generation"
    TRANSMISSION_SUBSTATION = "transmission_substation"
    DISTRIBUTION_SUBSTATION = "distribution_substation"
    EXCHANGE = "exchange"
    MAST = "mast"
    DATA_CENTRE = "data_centre"
    CABLE_LANDING = "cable_landing"
    RESERVOIR = "reservoir"
    TREATMENT = "treatment"
    PUMPING = "pumping"
    STORAGE = "storage"
    AIRPORT = "airport"
    SEAPORT = "seaport"
    RAIL_NODE = "rail_node"
    ROAD_JUNCTION = "road_junction"
    REFINERY = "refinery"
    TANK_FARM = "tank_farm"
    IMPORT_TERMINAL = "import_terminal"
    DEPOT = "depot"
    TERTIARY = "tertiary"
    REGIONAL = "regional"
    CLINIC = "clinic"
    BLOOD_BANK = "blood_bank"


class SwitchedOffHandling(StrEnum):
    """What happens to supplier-consumer pairs that are switched off."""

    GENERATE_AND_HIDE = "generate_and_hide"
    NOT_GENERATED = "not_generated"


class Hazard(StrEnum):
    """Shared-cause hazard fields."""

    STORM_CORRIDOR = "storm_corridor"
    SEISMIC_ZONE = "seismic_zone"
    FLOOD_PLAIN = "flood_plain"


class Tier(StrEnum):
    """The world's dynamics tier."""

    EXACT = "exact"
    SIMULATION = "simulation"
    BOTH = "both"


class TransferForm(StrEnum):
    """The four canon transfer forms: how supply loss becomes function loss."""

    LINEAR = "linear"
    CONCAVE = "concave"
    THRESHOLD = "threshold"
    STEP = "step"


class ErrorMechanism(StrEnum):
    """The process that produces a source's errors."""

    PARAMETRIC = "parametric"
    PROCESS = "process"
    REPLAY = "replay"
    GENERATIVE = "generative"
    ADVERSARIAL = "adversarial"


class MemberClass(StrEnum):
    """Optimization member-classes."""

    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"
    RESTORATIVE = "restorative"
    INFORMATIVE = "informative"


class Objective(StrEnum):
    """What an answer-key request optimizes."""

    UNSERVED_DEMAND_HOURS = "unserved_demand_hours"
    TIME_TO_RESTORE_80_PCT = "time_to_restore_80_pct"
    WORST_SINGLE_LAYER = "worst_single_layer"


class WeightPreset(StrEnum):
    """Service-weight presets."""

    EQUAL = "equal"
    HEALTHCARE_FIRST = "healthcare_first"
    CUSTOM = "custom"


# --- Fixed tables ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SizePresetValues:
    """Area and per-layer node count a size preset sets."""

    area_km2: float
    nodes_per_layer: int
    note: str


SIZE_PRESETS: Mapping[SizePreset, SizePresetValues] = {
    SizePreset.HAND_CHECK: SizePresetValues(400.0, 4, "structure v0.2 §4.1"),
    SizePreset.SMALL: SizePresetValues(2_000.0, 20, "structure v0.2 §4.1"),
    SizePreset.TAIWAN_SCALE: SizePresetValues(
        36_000.0,
        300,
        "placeholder (open decision: realism ranges and Taiwan-scale counts)",
    ),
    SizePreset.VERY_LARGE: SizePresetValues(250_000.0, 2_000, "structure v0.2 §4.1"),
    SizePreset.HUGE: SizePresetValues(8_000_000.0, 50_000, "structure v0.2 §4.1"),
}
"""Size presets. Source: structure v0.2 §4.1; Taiwan-scale values are placeholders."""

LAYER_SOURCES: Mapping[Layer, tuple[Source, ...]] = {
    Layer.POWER: (Source.OSM_POWER, Source.WRI_GPPD, Source.OPENINFRAMAP),
    Layer.TELECOM: (Source.OSM_TELECOM, Source.SUBMARINE_CABLES),
    Layer.WATER: (Source.OSM_WATER, Source.DAM_REGISTER),
    Layer.TRANSPORT: (Source.OURAIRPORTS, Source.WORLD_PORT_INDEX, Source.OSM_ROADS_RAIL),
    Layer.FUEL: (Source.OSM_FUEL, Source.OSM_PIPELINES, Source.LNG_REGISTER),
    Layer.HEALTHCARE: (Source.OSM_HEALTH, Source.HEALTHSITES, Source.FACILITY_REGISTER),
}
"""The sources each layer can be emitted to. Source: interface mockup v0.5."""

LAYER_NODE_CLASSES: Mapping[Layer, tuple[NodeClass, ...]] = {
    Layer.POWER: (
        NodeClass.GENERATION,
        NodeClass.TRANSMISSION_SUBSTATION,
        NodeClass.DISTRIBUTION_SUBSTATION,
    ),
    Layer.TELECOM: (
        NodeClass.EXCHANGE,
        NodeClass.MAST,
        NodeClass.DATA_CENTRE,
        NodeClass.CABLE_LANDING,
    ),
    Layer.WATER: (NodeClass.RESERVOIR, NodeClass.TREATMENT, NodeClass.PUMPING, NodeClass.STORAGE),
    Layer.TRANSPORT: (
        NodeClass.AIRPORT,
        NodeClass.SEAPORT,
        NodeClass.RAIL_NODE,
        NodeClass.ROAD_JUNCTION,
    ),
    Layer.FUEL: (
        NodeClass.REFINERY,
        NodeClass.TANK_FARM,
        NodeClass.IMPORT_TERMINAL,
        NodeClass.DEPOT,
    ),
    Layer.HEALTHCARE: (
        NodeClass.TERTIARY,
        NodeClass.REGIONAL,
        NodeClass.CLINIC,
        NodeClass.BLOOD_BANK,
    ),
}
"""Node classes per layer. Source: interface mockup v0.5 (ruling C6)."""

DEFAULT_COUPLINGS: tuple[tuple[Layer, Layer], ...] = (
    (Layer.POWER, Layer.TELECOM),
    (Layer.POWER, Layer.WATER),
    (Layer.POWER, Layer.TRANSPORT),
    (Layer.POWER, Layer.FUEL),
    (Layer.POWER, Layer.HEALTHCARE),
    (Layer.TELECOM, Layer.POWER),
    (Layer.TELECOM, Layer.WATER),
    (Layer.TELECOM, Layer.TRANSPORT),
    (Layer.TELECOM, Layer.FUEL),
    (Layer.TELECOM, Layer.HEALTHCARE),
    (Layer.WATER, Layer.POWER),
    (Layer.WATER, Layer.TELECOM),
    (Layer.WATER, Layer.FUEL),
    (Layer.WATER, Layer.HEALTHCARE),
    (Layer.TRANSPORT, Layer.FUEL),
    (Layer.TRANSPORT, Layer.HEALTHCARE),
    (Layer.FUEL, Layer.POWER),
    (Layer.FUEL, Layer.TELECOM),
    (Layer.FUEL, Layer.WATER),
    (Layer.FUEL, Layer.TRANSPORT),
    (Layer.FUEL, Layer.HEALTHCARE),
)
"""The 21 modeled supplier-to-consumer couplings; healthcare supplies none.

Source: structure v0.2 §4.3 ("defaulting to the 21 modeled"); interface mockup v0.5.
"""

MODEL_MEMBER_CLASS: Mapping[str, MemberClass] = {
    "protect_condition_and_add_reserve": MemberClass.DEFENSIVE,
    "add_redundant_feeds": MemberClass.DEFENSIVE,
    "strike_nodes": MemberClass.OFFENSIVE,
    "drain_reserves": MemberClass.OFFENSIVE,
    "sequence_repair_crews": MemberClass.RESTORATIVE,
    "stage_crews_at_depots": MemberClass.RESTORATIVE,
    "observe_uncertain_couplings": MemberClass.INFORMATIVE,
    "verify_source_records": MemberClass.INFORMATIVE,
}
"""The member-class each model belongs to. Source: interface mockup v0.5 (placeholder names)."""


# --- Terrain --------------------------------------------------------------------------------


class TerrainCharacter(_Section):
    """What the land is like. Each 0-100 index runs from none (0) to the most the map allows."""

    mountainous: int = Field(
        60,
        ge=0,
        le=100,
        description="How much of the land is high and steep. 0 = none; 100 = the most the "
        "map type allows.",
    )
    forested: int = Field(
        35, ge=0, le=100, description="Forest cover. 0 = none; 100 = the most the map allows."
    )
    river_density: int = Field(
        40,
        ge=0,
        le=100,
        description="How many rivers cross the land. 0 = none; 100 = the most the map allows.",
    )
    urban_density: int = Field(
        45,
        ge=0,
        le=100,
        description="How much land is built up; drives siting, not demand. 0 = none; 100 = the "
        "most the map allows.",
    )
    coastline_complexity: int = Field(
        50,
        ge=0,
        le=100,
        description="Smooth coast (0) to the most harbours and inlets the map allows (100).",
    )
    lowland_and_wetland: int = Field(
        20,
        ge=0,
        le=100,
        description="Share of low, wet ground, as an index. 0 = none; 100 = the most the map "
        "allows.",
    )
    aridity: int = Field(
        20,
        ge=0,
        le=100,
        description="How dry the land is. 0 = none; 100 = the most the map allows.",
    )
    outlying_islands: int = Field(
        2, ge=0, le=8, description="Number of small islands off the main landmass."
    )


class Terrain(_Section):
    """Terrain: shape, character and size. Spec: structure v0.2 §4.1."""

    map_type: MapType = Field(MapType.SPINE_ISLAND, description="The overall shape of the land.")
    terrain_seed: int = Field(
        0,
        ge=0,
        le=ROOT_SEED_UPPER_BOUND,
        description="Rerolls the ground alone: an extra spawn-key element on every terrain "
        "stream. Infrastructure follows the terrain, but its own streams never move.",
    )
    size_preset: SizePreset = Field(
        SizePreset.HAND_CHECK,
        description="Sets the area and every layer's node count together. 'custom' sets none; "
        "the recipe must give them.",
    )
    area_km2: float | None = Field(
        None,
        ge=1,
        description="Map area in km². Default: the size preset's area.",
    )
    hold_on_area_change: HoldOnAreaChange = Field(
        HoldOnAreaChange.DENSITY,
        description="When the area differs from the preset's: hold density (node counts scale "
        "with the area) or hold node counts (density falls as the area grows).",
    )
    character: TerrainCharacter = Field(
        default_factory=TerrainCharacter, description="Terrain character settings."
    )
    urban_pattern: UrbanPattern = Field(
        UrbanPattern.SEVERAL_CITIES, description="How built-up land is arranged."
    )


# --- Layers ---------------------------------------------------------------------------------


class LayerSettings(_Section):
    """One layer's controls. Spec: structure v0.2 §4.2."""

    state: LayerState = Field(
        LayerState.EMITTED,
        description="emitted: in the world and its sources. hidden: in the world and every "
        "answer key, but reaches no source. off: not generated.",
    )
    node_count: int | None = Field(
        None, ge=1, description="Nodes in this layer. Default: from the size preset."
    )
    links_per_node: float = Field(
        2.0, ge=1.0, le=4.0, description="Mean intra-layer links per node."
    )
    nodes_only: bool = Field(
        False,
        description="The layer's sources report nodes only. Its links exist in the true world "
        "but are never emitted.",
    )
    sources: tuple[Source, ...] = Field(
        (), description="The sources switched on for this layer; each must be this layer's."
    )
    overlap_pct: int = Field(
        30,
        ge=0,
        le=100,
        description="Share of true assets appearing in more than one of this layer's sources.",
    )


def _layer(links_per_node: float, nodes_only: bool, *sources: Source) -> LayerSettings:
    return LayerSettings(links_per_node=links_per_node, nodes_only=nodes_only, sources=sources)


class Layers(_Section):
    """The six layers, plus dual membership. Spec: structure v0.2 §4.2."""

    dual_membership: bool = Field(
        True, description="Whether assets may belong to two layers (a hydro dam, say)."
    )
    power: LayerSettings = Field(
        default_factory=lambda: _layer(2.4, False, Source.OSM_POWER, Source.WRI_GPPD),
        description="Power layer.",
    )
    telecom: LayerSettings = Field(
        default_factory=lambda: _layer(2.2, False, Source.OSM_TELECOM),
        description="Telecommunications layer.",
    )
    water: LayerSettings = Field(
        default_factory=lambda: _layer(1.6, False, Source.OSM_WATER), description="Water layer."
    )
    transport: LayerSettings = Field(
        default_factory=lambda: _layer(2.6, False, Source.OURAIRPORTS, Source.WORLD_PORT_INDEX),
        description="Transportation layer.",
    )
    fuel: LayerSettings = Field(
        default_factory=lambda: _layer(1.4, True, Source.OSM_FUEL), description="Fuel layer."
    )
    healthcare: LayerSettings = Field(
        default_factory=lambda: _layer(1.2, True, Source.OSM_HEALTH, Source.FACILITY_REGISTER),
        description="Healthcare layer.",
    )

    def get(self, layer: Layer) -> LayerSettings:
        """Return one layer's settings.

        Parameters
        ----------
        layer : Layer
            Which layer.

        Returns
        -------
        LayerSettings
            That layer's settings.

        Spec: structure v0.2 §4.2.
        """
        settings: LayerSettings = getattr(self, layer.value)
        return settings

    @model_validator(mode="after")
    def _sources_belong_to_their_layer(self) -> Self:
        for layer in Layer:
            sources = self.get(layer).sources
            allowed = LAYER_SOURCES[layer]
            for source in sources:
                if source not in allowed:
                    raise ValueError(
                        f"layers.{layer}.sources: {source} is not a {layer} source; "
                        f"{layer} takes {', '.join(allowed)}"
                    )
            if len(set(sources)) != len(sources):
                raise ValueError(f"layers.{layer}.sources: a source is listed twice")
        return self


# --- Couplings and shared causes ------------------------------------------------------------


class CouplingPair(_Section):
    """One supplier-to-consumer layer pair."""

    supplier: Layer = Field(description="The supplying layer.")
    consumer: Layer = Field(description="The consuming layer.")

    @model_validator(mode="after")
    def _distinct_layers(self) -> Self:
        if self.supplier == self.consumer:
            raise ValueError(f"a coupling needs two layers, got {self.supplier} twice")
        return self


class FeedMix(_Section):
    """How consumers are fed. The three shares always total exactly 100."""

    single_feed_pct: int = Field(60, ge=0, le=100, description="Consumers with one supplier.")
    two_full_feeds_pct: int = Field(
        25, ge=0, le=100, description="Consumers with two feeds, either of which covers the need."
    )
    two_half_feeds_pct: int = Field(
        15, ge=0, le=100, description="Consumers with two feeds, both of which are needed."
    )

    @model_validator(mode="after")
    def _total_is_100(self) -> Self:
        total = self.single_feed_pct + self.two_full_feeds_pct + self.two_half_feeds_pct
        if total != FEED_MIX_TOTAL_PCT:
            raise ValueError(f"feed_mix shares must total exactly 100, got {total}")
        return self


class Couplings(_Section):
    """Cross-layer couplings. Spec: structure v0.2 §4.3."""

    switched_on: tuple[CouplingPair, ...] = Field(
        default_factory=lambda: tuple(
            CouplingPair(supplier=supplier, consumer=consumer)
            for supplier, consumer in DEFAULT_COUPLINGS
        ),
        description="The supplier-to-consumer pairs switched on. Default: the 21 modeled.",
    )
    switched_off_handling: SwitchedOffHandling = Field(
        SwitchedOffHandling.GENERATE_AND_HIDE,
        description="Whether switched-off pairs are generated in the true world and hidden, or "
        "not generated at all.",
    )
    density: int = Field(
        50,
        ge=0,
        le=100,
        description="Cross-layer dependencies per consumer. 0 = the minimum one supplier per "
        "coupled layer; 100 = the maximum the matrix allows.",
    )
    two_way: bool = Field(True, description="Whether two-way dependencies are generated.")
    supplier_not_nearest_pct: int = Field(
        25,
        ge=0,
        le=100,
        description="Share of consumers whose true supplier is not the nearest one.",
    )
    concentration: int = Field(
        40,
        ge=0,
        le=100,
        description="Dependency concentration. 0 = supply spread evenly across suppliers; "
        "100 = one supplier per layer carries every consumer.",
    )
    feed_mix: FeedMix = Field(default_factory=FeedMix, description="Feed configuration mix.")

    @model_validator(mode="after")
    def _no_repeated_pairs(self) -> Self:
        pairs = [(pair.supplier, pair.consumer) for pair in self.switched_on]
        if len(set(pairs)) != len(pairs):
            raise ValueError("couplings.switched_on: a supplier-consumer pair is listed twice")
        return self


class HazardSettings(_Section):
    """One hazard field."""

    switched_on: bool = Field(False, description="Whether this hazard field is drawn.")
    correlation_km: int = Field(
        40,
        ge=5,
        le=150,
        description="How far apart two assets can be and still tend to fail together, in km.",
    )
    severity: int = Field(
        60,
        ge=0,
        le=100,
        description="How hard the hazard hits. 0 = no damage; 100 = every exposed element in "
        "the hazard core fails.",
    )


class Hazards(_Section):
    """The hazard fields. Spec: structure v0.2 §4.3; ruling B4."""

    storm_corridor: HazardSettings = Field(
        default_factory=lambda: HazardSettings(switched_on=True, correlation_km=40),
        description="Storm corridor.",
    )
    seismic_zone: HazardSettings = Field(
        default_factory=lambda: HazardSettings(correlation_km=60), description="Seismic zone."
    )
    flood_plain: HazardSettings = Field(
        default_factory=lambda: HazardSettings(correlation_km=20), description="Flood plain."
    )

    def get(self, hazard: Hazard) -> HazardSettings:
        """Return one hazard's settings.

        Parameters
        ----------
        hazard : Hazard
            Which hazard.

        Returns
        -------
        HazardSettings
            That hazard's settings.

        Spec: structure v0.2 §4.3.
        """
        settings: HazardSettings = getattr(self, hazard.value)
        return settings


class SharedCauses(_Section):
    """Shared causes: hazard fields and scenarios. Spec: structure v0.2 §4.3."""

    hazards: Hazards = Field(default_factory=Hazards, description="The hazard fields.")
    scenarios: int = Field(
        8, ge=1, le=200, description="Disruption scenarios drawn from the active hazard fields."
    )


# --- What sources don't show ----------------------------------------------------------------


class ContinuousDrawnQuantity(_Section):
    """A quantity drawn per element around its design target. Spec: structure v0.2 §4.4."""

    heterogeneity: int = Field(
        0,
        ge=0,
        le=100,
        description="How much elements with the same target differ. 0 = every element of a "
        "class gets the same value.",
    )
    compliance_gap_pct: int = Field(
        0,
        ge=-50,
        le=100,
        description="Mean departure from the design target, as a percent of the target. "
        "Positive: shortfall; negative: the element exceeds its target.",
    )


class CategoricalDrawnQuantity(_Section):
    """A drawn quantity with no numeric target. Compliance gap does not apply (ruling C1)."""

    heterogeneity_pct: int = Field(
        0,
        ge=0,
        le=100,
        description="Share of elements departing from their canon default.",
    )
    compliance_gap_pct: int = Field(
        0,
        ge=-50,
        le=100,
        description="Does not apply; resolved to 0, with a validation note if set otherwise.",
    )


class Unobserved(_Section):
    """Real but unobserved quantities: drawn per element, never emitted. Spec: v0.2 §4.4."""

    reserves: ContinuousDrawnQuantity = Field(
        default_factory=lambda: ContinuousDrawnQuantity(heterogeneity=50, compliance_gap_pct=30),
        description="Reserves. Buffer time is the reserve divided by the draw, computed in the "
        "run.",
    )
    requirements: ContinuousDrawnQuantity = Field(
        default_factory=lambda: ContinuousDrawnQuantity(heterogeneity=40),
        description="Node requirements per commodity.",
    )
    repair_rates: ContinuousDrawnQuantity = Field(
        default_factory=lambda: ContinuousDrawnQuantity(heterogeneity=45, compliance_gap_pct=20),
        description="Repair rates.",
    )
    failure_mode: CategoricalDrawnQuantity = Field(
        default_factory=lambda: CategoricalDrawnQuantity(heterogeneity_pct=30),
        description="Failure mode (throttle or trip). Heterogeneity: share of elements whose "
        "failure mode departs from their type's canon default.",
    )
    links_on_nodes_only_layers: CategoricalDrawnQuantity = Field(
        default_factory=lambda: CategoricalDrawnQuantity(heterogeneity_pct=35),
        description="Links on nodes-only layers. Heterogeneity: share of links that depart "
        "from the shortest road route.",
    )
    crews: int = Field(6, ge=1, le=40, description="Repair crews in the world.")
    depots: int = Field(2, ge=1, le=10, description="Depots the crews deploy from.")


# --- Dynamics -------------------------------------------------------------------------------


class TransferForms(_Section):
    """Transfer form per dependency type (ruling B6)."""

    physical_flow: TransferForm = Field(
        TransferForm.LINEAR, description="Physical flow dependencies."
    )
    logistic: TransferForm = Field(TransferForm.THRESHOLD, description="Logistic dependencies.")
    control: TransferForm = Field(TransferForm.STEP, description="Control dependencies.")
    service: TransferForm = Field(TransferForm.LINEAR, description="Service dependencies.")


class Dynamics(_Section):
    """The world's own declared dynamics. Spec: structure v0.2 §4.5; rulings B5, B6, C5."""

    tier: Tier = Field(
        Tier.EXACT,
        description="exact: restricted forms with a provable optimum. simulation: full rules. "
        "both: sized for both, so the two can be compared.",
    )
    combining: Literal["typed_weakest_link"] = Field(
        "typed_weakest_link",
        description="How several inbound dependencies combine at a node. Fixed.",
    )
    transfer_forms: TransferForms = Field(
        default_factory=TransferForms, description="Transfer form per dependency type."
    )


# --- Error induction ------------------------------------------------------------------------


class SourceErrors(_Section):
    """One source's error settings. Rates count against true elements in the source's scope."""

    mechanism: ErrorMechanism | None = Field(
        None, description="The mechanism for this source. Default: errors.default_mechanism."
    )
    coverage_pct: int = Field(
        90, ge=30, le=100, description="Share of the region or asset range covered at all."
    )
    snapshot_age_y: int = Field(2, ge=0, le=10, description="How old the source's data is.")
    phantom_pct: int = Field(
        2, ge=0, le=100, description="Share of true assets for which the source invents a record."
    )
    missing_pct: int = Field(
        5, ge=0, le=100, description="Share of true assets in scope absent from the source."
    )
    merged_pct: int = Field(
        2, ge=0, le=100, description="Share of true assets folded into another asset's record."
    )
    location_pct: int = Field(
        10,
        ge=0,
        le=100,
        description="Share of reported assets placed away from their true position.",
    )
    attributes_pct: int = Field(
        15,
        ge=0,
        le=100,
        description="Share of reported assets with a wrong value in a scored attribute.",
    )
    links_pct: int = Field(
        5,
        ge=0,
        le=100,
        description="Share of true links dropped plus false links added. Ignored on nodes-only "
        "layers.",
    )
    labels_pct: int = Field(
        5, ge=0, le=100, description="Share of reported assets with a wrong or missing class tag."
    )


class Errors(_Section):
    """Error induction, per source. Spec: structure v0.2 §4.7; ruling B3."""

    default_mechanism: ErrorMechanism = Field(
        ErrorMechanism.PARAMETRIC,
        description="Mechanism for every source that does not set its own. Adversarial is "
        "carried in the schema and never exercised.",
    )
    sources: dict[Source, SourceErrors] = Field(
        default_factory=dict,
        description="Per-source settings. Every switched-on source gets the defaults.",
    )


# --- Ensemble -------------------------------------------------------------------------------


class EnsembleVary(_Section):
    """Which streams vary between ensemble members."""

    terrain: bool = Field(False, description="Vary the terrain (the terrain seed).")
    infrastructure: bool = Field(False, description="Vary the infrastructure.")
    unobserved: bool = Field(False, description="Vary the unobserved quantities.")
    errors: bool = Field(True, description="Vary the errors.")


class Ensemble(_Section):
    """A set of worlds from one recipe. Spec: structure v0.2 §4.9."""

    members: int = Field(1, ge=1, le=50, description="Worlds built from this recipe.")
    vary: EnsembleVary = Field(default_factory=EnsembleVary, description="What varies.")


# --- Answer-key requests --------------------------------------------------------------------


class _Request(_Section):
    """Fields every model request carries. Spec: structure v0.2 §5; rulings A5, C5, C6."""

    model: str = Field(description="The model within the member-class.")
    member_class: MemberClass = Field(description="The optimization member-class.")
    objective: Objective = Field(
        Objective.UNSERVED_DEMAND_HOURS, description="What the request optimizes."
    )
    service_weights: WeightPreset = Field(
        WeightPreset.HEALTHCARE_FIRST,
        description="How much a unit of unserved demand counts at each node class.",
    )
    custom_weights: dict[NodeClass, ServiceWeight] | None = Field(
        None,
        description="A weight (0-100) for every node class. Required with custom weights only.",
    )
    window_h: int = Field(
        72, ge=6, le=336, description="The horizon the objective is scored over, in hours."
    )

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        expected = MODEL_MEMBER_CLASS[self.model]
        if self.member_class != expected:
            raise ValueError(f"model {self.model} belongs to {expected}, not {self.member_class}")
        self._check_custom_weights()
        return self

    def _check_custom_weights(self) -> None:
        if self.service_weights != WeightPreset.CUSTOM:
            if self.custom_weights is not None:
                raise ValueError("custom_weights is set only with service_weights: custom")
            return
        if self.custom_weights is None:
            raise ValueError("service_weights: custom needs custom_weights for every node class")
        missing = [node_class for node_class in NodeClass if node_class not in self.custom_weights]
        if missing:
            raise ValueError(f"custom_weights is missing {', '.join(missing)}")


class ProtectConditionAndAddReserve(_Request):
    """Defensive: spend a budget on protecting condition and adding reserves."""

    model: Literal["protect_condition_and_add_reserve"] = Field(
        "protect_condition_and_add_reserve", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.DEFENSIVE, description="Defensive.")
    budget_cost_units: int = Field(3, ge=1, le=20, description="The action budget, in cost units.")
    protect_condition_cost_units: int = Field(
        2, ge=1, description="Cost of protecting one node's condition (pilot value)."
    )
    add_reserve_cost_units: int = Field(
        1, ge=1, description="Cost of adding a reserve at one node (pilot value)."
    )


class AddRedundantFeeds(_Request):
    """Defensive: add redundant feeds. Parameters not yet scheduled."""

    model: Literal["add_redundant_feeds"] = Field(
        "add_redundant_feeds", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.DEFENSIVE, description="Defensive.")


class StrikeNodes(_Request):
    """Offensive: strike k nodes, degrading their condition."""

    model: Literal["strike_nodes"] = Field(
        "strike_nodes", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.OFFENSIVE, description="Offensive.")
    strikes_k: int = Field(2, ge=1, le=20, description="Number of nodes struck.")


class DrainReserves(_Request):
    """Offensive: drain reserves. Parameters not yet scheduled."""

    model: Literal["drain_reserves"] = Field(
        "drain_reserves", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.OFFENSIVE, description="Offensive.")


class SequenceRepairCrews(_Request):
    """Restorative: sequence the world's repair crews. Takes no budget (ruling A2)."""

    model: Literal["sequence_repair_crews"] = Field(
        "sequence_repair_crews", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.RESTORATIVE, description="Restorative.")


class StageCrewsAtDepots(_Request):
    """Restorative: stage crews at depots. Parameters not yet scheduled."""

    model: Literal["stage_crews_at_depots"] = Field(
        "stage_crews_at_depots", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.RESTORATIVE, description="Restorative.")


class ObserveUncertainCouplings(_Request):
    """Informative: choose couplings to observe before hardening."""

    model: Literal["observe_uncertain_couplings"] = Field(
        "observe_uncertain_couplings", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.INFORMATIVE, description="Informative.")
    observations_n: int = Field(1, ge=1, le=20, description="Number of couplings observed.")


class VerifySourceRecords(_Request):
    """Informative: verify source records. Parameters not yet scheduled."""

    model: Literal["verify_source_records"] = Field(
        "verify_source_records", description="The model within the member-class."
    )
    member_class: MemberClass = Field(MemberClass.INFORMATIVE, description="Informative.")


AnswerKeyRequest = Annotated[
    ProtectConditionAndAddReserve
    | AddRedundantFeeds
    | StrikeNodes
    | DrainReserves
    | SequenceRepairCrews
    | StageCrewsAtDepots
    | ObserveUncertainCouplings
    | VerifySourceRecords,
    Field(discriminator="model"),
]


def _default_requests() -> tuple[AnswerKeyRequest, ...]:
    return (
        ProtectConditionAndAddReserve(budget_cost_units=3),
        StrikeNodes(strikes_k=2, service_weights=WeightPreset.EQUAL),
    )


# --- The recipe -----------------------------------------------------------------------------


class Recipe(_Section):
    """A recipe: every choice that builds one world, and the questions posed of it.

    Spec: structure v0.2 §3 (the recipe is the record) and §4; Work Order 1, item 2.
    """

    recipe_version: Literal[1] = Field(
        RECIPE_VERSION, description="The recipe schema version the recipe was written for."
    )
    root_seed: int = Field(
        DEFAULT_ROOT_SEED,
        ge=0,
        le=ROOT_SEED_UPPER_BOUND,
        description="With the recipe, rebuilds this exact world. Every stream spawns from it.",
    )
    terrain: Terrain = Field(default_factory=Terrain, description="Terrain.")
    layers: Layers = Field(default_factory=Layers, description="Layers and sources.")
    couplings: Couplings = Field(default_factory=Couplings, description="Couplings.")
    shared_causes: SharedCauses = Field(default_factory=SharedCauses, description="Causes.")
    unobserved: Unobserved = Field(default_factory=Unobserved, description="Never emitted.")
    dynamics: Dynamics = Field(default_factory=Dynamics, description="The world's rules.")
    errors: Errors = Field(default_factory=Errors, description="Error induction per source.")
    ensemble: Ensemble = Field(default_factory=Ensemble, description="Ensembles.")
    answer_key_requests: tuple[AnswerKeyRequest, ...] = Field(
        default_factory=_default_requests,
        description="Model requests posed of the world, separate from it.",
    )

    @model_validator(mode="after")
    def _custom_size_is_complete(self) -> Self:
        if self.terrain.size_preset != SizePreset.CUSTOM:
            return self
        missing = [layer.value for layer in Layer if self.layers.get(layer).node_count is None]
        if self.terrain.area_km2 is None:
            missing.insert(0, "terrain.area_km2")
        if missing:
            raise ValueError(
                "size_preset custom needs the area and every layer's node_count; missing: "
                + ", ".join(missing)
            )
        return self
