"""Reading recipes from YAML and writing them, and the stream record, as canonical bytes."""

import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from swm.recipe.schema import SUPPORTED_RECIPE_VERSIONS, Recipe
from swm.rng import StreamRecord

RESOLVED_RECIPE_FILE = "resolved_recipe.yaml"
STREAM_RECORD_FILE = "stream_record.yaml"


class RecipeVersionError(ValueError):
    """A recipe names a schema version this code does not read."""


class RecipeFormatError(ValueError):
    """A recipe file is not a YAML mapping."""


class _RecipeLoader(yaml.SafeLoader):
    """YAML loader in which only true and false are booleans.

    YAML 1.1 reads bare ``off``, ``on``, ``yes`` and ``no`` as booleans, which would turn a layer
    state of ``off`` into ``False``. YAML 1.2 keeps them as strings, and so does this loader.
    """


_RecipeLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_RecipeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def parse_recipe(text: str) -> Recipe:
    """Validate a recipe from YAML text.

    Parameters
    ----------
    text : str
        The recipe as YAML.

    Returns
    -------
    Recipe
        The validated, unresolved recipe.

    Raises
    ------
    RecipeFormatError
        If the text is not a YAML mapping.
    RecipeVersionError
        If ``recipe_version`` is missing or names a version this code does not read.
    pydantic.ValidationError
        If any field breaks the schema.

    Spec: CLAUDE.md §8 (old recipes load or fail with a clear message); Work Order 1, item 2.
    """
    data = yaml.load(text, Loader=_RecipeLoader)
    if not isinstance(data, dict):
        raise RecipeFormatError("a recipe must be a YAML mapping of sections")
    readable = ", ".join(str(version) for version in SUPPORTED_RECIPE_VERSIONS)
    # CHOICE: a recipe file must state its version, so an old file is never read as a new one.
    if "recipe_version" not in data:
        raise RecipeVersionError(
            f"the recipe does not state recipe_version; this code reads version {readable}"
        )
    version = data["recipe_version"]
    if version not in SUPPORTED_RECIPE_VERSIONS:
        raise RecipeVersionError(
            f"recipe_version {version!r} is not supported; this code reads version {readable}"
        )
    return Recipe.model_validate(data)


def load_recipe(path: Path) -> Recipe:
    """Read and validate a recipe file.

    Parameters
    ----------
    path : Path
        A UTF-8 YAML recipe.

    Returns
    -------
    Recipe
        The validated, unresolved recipe.

    Spec: Work Order 1, item 3.
    """
    return parse_recipe(path.read_text(encoding="utf-8"))


def canonical_yaml(data: Mapping[str, Any]) -> bytes:
    """Return data as canonical YAML bytes, identical on every platform.

    Keys keep the order given (the schema's order for a recipe). Output is UTF-8 with LF line
    endings and no timestamps; floats use Python's shortest round-trip form.

    Parameters
    ----------
    data : Mapping[str, Any]
        Plain data: mappings, sequences, strings, integers, floats and booleans.

    Returns
    -------
    bytes
        The canonical encoding.

    Spec: CLAUDE.md §4 (byte-identical output); Work Order 1, item 3.
    """
    text = yaml.safe_dump(
        dict(data),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1_000_000,
        line_break="\n",
    )
    return text.encode("utf-8")


def recipe_bytes(recipe: Recipe) -> bytes:
    """Return a recipe as canonical YAML bytes.

    Parameters
    ----------
    recipe : Recipe
        A recipe, normally resolved.

    Returns
    -------
    bytes
        The canonical encoding, in schema order.

    Spec: Work Order 1, item 3.
    """
    return canonical_yaml(recipe.model_dump(mode="json"))


def recipe_sha256(recipe: Recipe) -> str:
    """Return the SHA-256 of a recipe's canonical bytes, as hex.

    Parameters
    ----------
    recipe : Recipe
        A resolved recipe.

    Returns
    -------
    str
        The hex digest that answer keys and manifests carry.

    Spec: Work Order 1, item 3.
    """
    return hashlib.sha256(recipe_bytes(recipe)).hexdigest()


def write_resolved_recipe(recipe: Recipe, out_dir: Path) -> Path:
    """Write a resolved recipe as canonical YAML.

    Parameters
    ----------
    recipe : Recipe
        A resolved recipe.
    out_dir : Path
        The folder to write into; created if absent.

    Returns
    -------
    Path
        The file written.

    Spec: CLAUDE.md §4; Work Order 1, items 3 and 4.
    """
    return _write(out_dir / RESOLVED_RECIPE_FILE, recipe_bytes(recipe))


def write_stream_record(record: StreamRecord, out_dir: Path) -> Path:
    """Write the stream record as canonical YAML.

    Parameters
    ----------
    record : StreamRecord
        The stream record.
    out_dir : Path
        The folder to write into; created if absent.

    Returns
    -------
    Path
        The file written.

    Spec: CLAUDE.md §7 (identity check); Work Order 1, item 4.
    """
    return _write(out_dir / STREAM_RECORD_FILE, canonical_yaml(record))


def write_canonical_yaml(data: Mapping[str, Any], path: Path) -> Path:
    """Write plain data as canonical YAML.

    Parameters
    ----------
    data : Mapping[str, Any]
        Plain data in the key order to write.
    path : Path
        The file to write; its folder is created if absent.

    Returns
    -------
    Path
        The file written.

    Spec: CLAUDE.md §4; Work Order 2, A11.
    """
    return _write(path, canonical_yaml(data))


def write_hash_list(hashes: Sequence[tuple[str, str]], path: Path) -> Path:
    """Write ``(name, hex digest)`` pairs as ``digest  name`` lines, in the order given.

    Parameters
    ----------
    hashes : Sequence[tuple[str, str]]
        Names and SHA-256 hex digests.
    path : Path
        The file to write; its folder is created if absent.

    Returns
    -------
    Path
        The file written.

    Spec: Work Order 2, A11.
    """
    lines = "".join(f"{digest}  {name}\n" for name, digest in hashes)
    return _write(path, lines.encode("utf-8"))


def write_binary(content: bytes, path: Path) -> Path:
    """Write bytes as they are, such as a preview image.

    Parameters
    ----------
    content : bytes
        The file's content.
    path : Path
        The file to write; its folder is created if absent.

    Returns
    -------
    Path
        The file written.

    Spec: CLAUDE.md §5 (only emit/, manifest/ and recipe/io write files).
    """
    return _write(path, content)


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Bytes are written as-is, so no platform newline translation can occur.
    path.write_bytes(content)
    return path
