"""Loading, validating and reading the modeling rules registry.

Every rule and number that shapes the world lives in ``modeling_rules.yaml`` beside this
module. Each entry says where it came from and why, and code reads it by id. A rule changes
only by a reviewed edit to that file (Work Order 5, A5). The registry's version and SHA-256
are stamped on the resolved recipe and on every world, so each world records which rules
built it.

Spec: Work Order 5, Part A; decision 0009.
"""

import functools
import hashlib
from collections.abc import Mapping
from enum import StrEnum
from importlib import resources
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

REGISTRY_FILE = "modeling_rules.yaml"
RULE_ID_PATTERN = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"

Scalar = bool | int | float | str


class Grade(StrEnum):
    """Evidence grade: a standard or regulation, literature or a government report, judgment."""

    S = "S"
    L = "L"
    J = "J"


class Jurisdiction(StrEnum):
    """Where the rule comes from."""

    TW = "TW"
    JP = "JP"
    US = "US"
    INTERNATIONAL = "international"


class Status(StrEnum):
    """Whether a rule is ruled, a placeholder, or an open decision."""

    RULED = "ruled"
    PLACEHOLDER = "placeholder"
    OPEN = "open"


class Stage(StrEnum):
    """The stage a rule shapes; the Modeling Rules page groups by it."""

    LAYERS = "layers"
    DEPENDENCIES = "dependencies"
    REQUIREMENTS = "requirements"
    RESERVES = "reserves"
    TOLERANCE = "tolerance"
    FAILURE_MODES = "failure_modes"
    REPAIR = "repair"
    CREWS = "crews"
    SIZING = "sizing"
    DRAWS = "draws"


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Source(_Strict):
    """One source for a rule."""

    citation: str = Field(min_length=1)
    url: str | None = None
    quote: str | None = None
    verified: bool | None = Field(
        None,
        description="Whether the evidence records the source as fetched and read (true), not yet "
        "checked (false), or does not say (null).",
    )


class Ruling(_Strict):
    """Who ruled a value, when, and where it is recorded."""

    by: str
    date: str
    decision: str


class HistoryItem(_Strict):
    """An earlier value and the decision that changed it."""

    value: Any
    units: str | None = None
    date: str
    decision: str


class AppliesTo(_Strict):
    """Where a rule applies: layer, class and subtype condition (any may be empty)."""

    layer: str | None = None
    node_class: str | None = None
    condition: str | None = None


class Rule(_Strict):
    """One entry of the registry."""

    id: str = Field(pattern=RULE_ID_PATTERN)
    title: str = Field(min_length=1)
    stage: Stage
    value: Any
    units: str | None = None
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    grade: Grade | None = None
    jurisdiction: Jurisdiction | None = None
    sources: tuple[Source, ...] = ()
    reasoning: str = Field(min_length=1)
    status: Status
    open_decision: str | None = None
    ruling: Ruling | None = None
    history: tuple[HistoryItem, ...] = ()
    overridable: bool = Field(
        False, description="Whether a recipe may override the value for a sensitivity run."
    )

    @model_validator(mode="after")
    def _complete(self) -> Self:
        if _is_number(self.value) and not self.units:
            raise ValueError(f"{self.id}: a numeric value needs units")
        if self.grade is None and self.ruling is None:
            raise ValueError(f"{self.id}: needs a grade, or a ruling that stands in for one")
        if not self.sources and self.status == Status.RULED:
            raise ValueError(f"{self.id}: a ruled entry needs at least one source")
        if self.overridable and not _is_number(self.value):
            raise ValueError(f"{self.id}: only numeric values can be overridden")
        return self


class Registry(_Strict):
    """The whole registry: a version and the rules."""

    version: str = Field(min_length=1)
    rules: tuple[Rule, ...]
    sha256: str = Field("", description="SHA-256 of the registry file's bytes.")
    overrides: tuple[tuple[str, float], ...] = Field(
        (), description="Recipe overrides applied to this copy, in id order."
    )

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [rule.id for rule in self.rules]
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        if repeated:
            raise ValueError(f"rule ids repeated: {', '.join(repeated)}")
        return self

    @functools.cached_property
    def _by_id(self) -> dict[str, Rule]:
        return {rule.id: rule for rule in self.rules}

    def rule(self, rule_id: str) -> Rule:
        """Return one rule by id.

        Parameters
        ----------
        rule_id : str
            The rule's dotted id.

        Returns
        -------
        Rule
            The entry.

        Raises
        ------
        KeyError
            If no rule has that id.

        Spec: Work Order 5, A1.
        """
        try:
            return self._by_id[rule_id]
        except KeyError:
            raise KeyError(f"no modeling rule {rule_id!r} in the registry") from None

    def has(self, rule_id: str) -> bool:
        """Return whether a rule with this id exists."""
        return rule_id in self._by_id

    def value(self, rule_id: str) -> Any:
        """Return a rule's value as stored (a number, text, list or table)."""
        return self.rule(rule_id).value

    def number(self, rule_id: str) -> float:
        """Return a numeric rule's value as a float.

        Parameters
        ----------
        rule_id : str
            The rule's dotted id.

        Returns
        -------
        float
            The value, in the rule's units.

        Spec: Work Order 5, A2.
        """
        value = self.value(rule_id)
        if not _is_number(value):
            raise TypeError(f"modeling rule {rule_id!r} is not a number")
        return float(value)

    def with_overrides(self, overrides: Mapping[str, float]) -> "Registry":
        """Return a copy with a recipe's overrides applied to overridable numeric rules.

        Parameters
        ----------
        overrides : Mapping[str, float]
            New values by rule id.

        Returns
        -------
        Registry
            The overridden registry; its hash stays the file's, and the overrides are listed.

        Raises
        ------
        ValueError
            If an id is unknown or its rule may not be overridden.

        Spec: Work Order 5, A3.
        """
        if not overrides:
            return self
        rules = []
        for rule in self.rules:
            if rule.id in overrides:
                rules.append(rule.model_copy(update={"value": overrides[rule.id]}))
            else:
                rules.append(rule)
        for rule_id in overrides:
            if not self.rule(rule_id).overridable:
                raise ValueError(f"modeling rule {rule_id!r} may not be overridden by a recipe")
        # A fresh model, not a copy: a copy would carry this registry's cached id index.
        return Registry(
            version=self.version,
            rules=tuple(rules),
            sha256=self.sha256,
            overrides=tuple(sorted((k, float(v)) for k, v in overrides.items())),
        )


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def registry_bytes() -> bytes:
    """Return the registry file's bytes as shipped with the package."""
    return resources.files("swm.rules").joinpath(REGISTRY_FILE).read_bytes()


def parse_registry(content: bytes) -> Registry:
    """Parse and validate registry bytes.

    Parameters
    ----------
    content : bytes
        The YAML file's bytes.

    Returns
    -------
    Registry
        The validated registry, carrying the bytes' SHA-256.

    Spec: Work Order 5, A3.
    """
    data = yaml.safe_load(content.decode("utf-8"))
    data["sha256"] = hashlib.sha256(content).hexdigest()
    return Registry.model_validate(data)


@functools.cache
def load_registry() -> Registry:
    """Load and validate the shipped registry once.

    Returns
    -------
    Registry
        The modeling rules in force, with no overrides.

    Spec: Work Order 5, A3.
    """
    return parse_registry(registry_bytes())


RULES = load_registry()
"""The shipped registry, for stages whose rules no recipe may override."""
