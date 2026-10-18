
"""Session 07 — Part B — Y2.

Detect RDF classes used in SPARQL that do not exist
in the Food Knowledge Graph ontology.
"""

from access_layer import ul_terms


def unknown_classes(query, classes, props):
    """
    Return problems for unknown Food RDF classes.

    classes: dictionary of class IRIs from VoID
    props: dictionary of property IRIs from VoID
    """

    known = {
        iri.rsplit("#", 1)[-1]
        for iri in classes
    }

    used = {
        term
        for term in ul_terms(query)
        if term[0].isupper()
    }

    unknown = used - known

    return [
        f"food:{term} is not a class of this graph. "
        f"Known classes: {', '.join(sorted(known))}"
        for term in sorted(unknown)
    ]
