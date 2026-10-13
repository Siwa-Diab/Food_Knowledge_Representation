"""IRI naming scheme for the Food Knowledge Representation project."""

from urllib.parse import quote

VOCAB = "https://example.org/food-kr/schema#"
DATA = "https://example.org/food-kr/id/"

SOURCE = "usda"


def mint(kind: str, source_key: str) -> str:
    """Create a source-qualified IRI for one resource."""
    key = quote(str(source_key).strip(), safe="")
    return f"{DATA}{kind}/{SOURCE}/{key}"


def food_iri(fdc_id: str) -> str:
    return mint("food", fdc_id)


def nutrient_iri(nutrient_id: str) -> str:
    return mint("nutrient", nutrient_id)


def measurement_iri(measurement_id: str) -> str:
    return mint("measurement", measurement_id)


def graph_iri(table: str) -> str:
    return f"{DATA}graph/{SOURCE}/{quote(table, safe='')}"