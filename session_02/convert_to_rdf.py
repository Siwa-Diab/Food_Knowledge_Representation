"""Convert four processed USDA FoodData Central tables into RDF.

Run from your project's session_02 folder: python convert_to_rdf.py
Requires food_iri.py in this folder and CSVs in ../data/processed/.
Outputs output/food_knowledge_graph.ttl and .trig plus sample/food.ttl.
"""
from pathlib import Path
import pandas as pd
from rdflib import Dataset, Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from food_iri import VOCAB, food_iri, nutrient_iri, measurement_iri, graph_iri

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'data' / 'processed'
OUT = HERE / 'output'
F = Namespace(VOCAB)


def add_text(g, subject, predicate, value):
    if pd.notna(value) and str(value).strip():
        g.add((subject, predicate, Literal(str(value).strip())))


def add_decimal(g, subject, predicate, value):
    if pd.notna(value) and str(value).strip():
        g.add((subject, predicate, Literal(str(value), datatype=XSD.decimal)))


def add_schema(g):
    for cls in (F.Food, F.BrandedFood, F.Nutrient, F.NutrientMeasurement):
        g.add((cls, RDF.type, RDFS.Class))
    g.add((F.BrandedFood, RDFS.subClassOf, F.Food))
    for prop, domain, range_ in (
        (F.description, F.Food, XSD.string),
        (F.ingredientDeclaration, F.BrandedFood, XSD.string),
        (F.brandOwner, F.BrandedFood, XSD.string),
        (F.brandName, F.BrandedFood, XSD.string),
        (F.foodCategory, F.BrandedFood, XSD.string),
        (F.gtinUpc, F.BrandedFood, XSD.string),
        (F.hasNutrientMeasurement, F.Food, F.NutrientMeasurement),
        (F.measuresNutrient, F.NutrientMeasurement, F.Nutrient),
        (F.amount, F.NutrientMeasurement, XSD.decimal),
        (F.nutrientName, F.Nutrient, XSD.string),
        (F.unitName, F.Nutrient, XSD.string),
    ):
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDFS.domain, domain))
        g.add((prop, RDFS.range, range_))


def load(name, required, dtype=None):
    path = DATA / name
    if not path.is_file():
        raise SystemExit(f'Missing {path}')
    df = pd.read_csv(path, dtype=dtype or {}, low_memory=False)
    missing = set(required) - set(df.columns)
    if missing:
        raise SystemExit(f'{name} missing columns: {sorted(missing)}')
    return df


def build():
    ds = Dataset()
    ds.bind('food', F)
    graphs = {name: ds.graph(URIRef(graph_iri(name))) for name in
              ('schema', 'food', 'branded_food', 'food_nutrient', 'nutrient')}
    add_schema(graphs['schema'])

    food = load('food.csv', ['fdc_id', 'description'], {'fdc_id': 'string'})
    branded = load('branded_food.csv',
                   ['fdc_id', 'ingredients', 'brand_owner', 'branded_food_category', 'gtin_upc'],
                   {'fdc_id': 'string', 'gtin_upc': 'string'})
    nutrient = load('nutrient.csv', ['id', 'name', 'unit_name'], {'id': 'string'})
    measurements = load('food_nutrient.csv', ['id', 'fdc_id', 'nutrient_id', 'amount'],
                        {'id': 'string', 'fdc_id': 'string', 'nutrient_id': 'string'})

    for r in food.itertuples(index=False):
        if pd.isna(r.fdc_id):
            continue
        s = URIRef(food_iri(r.fdc_id))
        graphs['food'].add((s, RDF.type, F.Food))
        add_text(graphs['food'], s, F.description, r.description)

    for r in branded.itertuples(index=False):
        if pd.isna(r.fdc_id):
            continue
        s = URIRef(food_iri(r.fdc_id))
        g = graphs['branded_food']
        g.add((s, RDF.type, F.BrandedFood))
        add_text(g, s, F.ingredientDeclaration, r.ingredients)
        add_text(g, s, F.brandOwner, r.brand_owner)
        add_text(g, s, F.brandName, r.brand_name)
        add_text(g, s, F.foodCategory, r.branded_food_category)
        add_text(g, s, F.gtinUpc, r.gtin_upc)

    for r in nutrient.itertuples(index=False):
        if pd.isna(r.id):
            continue
        s = URIRef(nutrient_iri(r.id))
        g = graphs['nutrient']
        g.add((s, RDF.type, F.Nutrient))
        add_text(g, s, F.nutrientName, r.name)
        add_text(g, s, F.unitName, r.unit_name)

    for r in measurements.itertuples(index=False):
        if pd.isna(r.id) or pd.isna(r.fdc_id) or pd.isna(r.nutrient_id):
            continue
        s = URIRef(measurement_iri(r.id))
        food_s = URIRef(food_iri(r.fdc_id))
        nutrient_s = URIRef(nutrient_iri(r.nutrient_id))
        g = graphs['food_nutrient']
        g.add((s, RDF.type, F.NutrientMeasurement))
        g.add((food_s, F.hasNutrientMeasurement, s))
        g.add((s, F.measuresNutrient, nutrient_s))
        add_decimal(g, s, F.amount, r.amount)
    return ds, graphs


def write(ds, graphs):
    OUT.mkdir(exist_ok=True)
    (HERE / 'sample').mkdir(exist_ok=True)
    ds.serialize(destination=str(OUT / 'food_knowledge_graph.trig'), format='trig')
    union = Graph()
    union.bind('food', F)
    for s, p, o, _ in ds.quads((None, None, None, None)):
        union.add((s, p, o))
    union.serialize(destination=str(OUT / 'food_knowledge_graph.ttl'), format='turtle')
    first = URIRef(food_iri('1107471'))
    sample = Graph()
    sample.bind('food', F)
    for triple in union.triples((first, None, None)):
        sample.add(triple)
    sample.serialize(destination=str(HERE / 'sample' / 'food.ttl'), format='turtle')
    for name, graph in graphs.items():
        print(f'{name}: {len(graph):,} triples')
    print(f'Union: {len(union):,} triples; sample: {len(sample)} triples')
    print(f'Output: {OUT}')


if __name__ == '__main__':
    write(*build())
