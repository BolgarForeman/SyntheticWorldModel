"""The observed world: everything a source may carry, and nothing it may not (CLAUDE.md §3).

Emission code receives only these records. They hold what a real source could see: where an
asset is, its class, its observed attributes, its name and outline, and the links mapped on
emitted layers. Subtypes, requirements, reserves, couplings, feeds and every other unobserved
quantity are absent by construction, so no writer can reach them.

Spec: structure v0.11 §4.6 (emission) and §3 (observed versus unobserved); Work Order 8.
"""

from dataclasses import dataclass

from swm.recipe.schema import Layer, NodeClass, Source

LonLat = tuple[float, float]
AttributeValue = str | int | float | bool


@dataclass(frozen=True)
class ObservedTown:
    """A town: its invented name and its district code (``XS-01`` …)."""

    town_id: int
    name: str
    district: str
    centre: LonLat


@dataclass(frozen=True)
class ObservedNode:
    """One asset as a source can see it."""

    node_id: str
    """The world's own id: the key the truth manifest maps every record to, never emitted."""
    layer: Layer
    node_class: NodeClass
    location: LonLat
    """WGS 84, 7 decimals: the true location, which is an outline's centre."""
    attributes: tuple[tuple[str, AttributeValue], ...]
    """The observed attributes only (decision 0007)."""
    town: str
    named: bool
    """False for a minor element left unnamed (E4)."""
    outline: tuple[LonLat, ...] | None
    """A closed rectangle (first corner repeated) for an area class, else None (E2)."""
    runway: tuple[LonLat, LonLat] | None
    district: str
    direction: str | None = None
    """A repeated facility's direction word from its town centre, else None (§4.6)."""
    number: int | None = None
    """Its number when another repeat in its town shares the direction, else None."""

    def name(self, word: str) -> str:
        """Return the facility's name in a source's style: town, direction, class word, number.

        Parameters
        ----------
        word : str
            The source's word for the class ("Substation", "Medical Centre" …).

        Returns
        -------
        str
            Such as "Selimere Substation" or "Selimere North Substation 2".

        Spec: structure v0.11 §4.6 (names).
        """
        parts = [self.town, self.direction, word, None if self.number is None else str(self.number)]
        return " ".join(part for part in parts if part)

    def attribute(self, name: str) -> AttributeValue | None:
        """Return one observed attribute, or None if the asset does not carry it."""
        return dict(self.attributes).get(name)


@dataclass(frozen=True)
class ObservedLink:
    """A link mapped on an emitted layer that is not nodes-only: a line, main or road."""

    link_id: str
    layer: Layer
    from_id: str
    to_id: str
    route: tuple[LonLat, ...]
    voltage_kv: int | None = None
    """Power lines only."""
    circuits: int | None = None
    towers: tuple[LonLat, ...] = ()
    """Power lines only: the tower points along the route, both ends included."""


@dataclass(frozen=True)
class ObservedWorld:
    """What the emitted sources can carry, per layer and source."""

    nodes: tuple[ObservedNode, ...]
    links: tuple[ObservedLink, ...]
    towns: tuple[ObservedTown, ...]
    sources: tuple[tuple[Layer, tuple[Source, ...]], ...]
    """The switched-on sources of each emitted layer."""
    nodes_only: frozenset[Layer]

    def sources_of(self, layer: Layer) -> tuple[Source, ...]:
        """Return the switched-on sources of a layer (empty if it is not emitted)."""
        return dict(self.sources).get(layer, ())
