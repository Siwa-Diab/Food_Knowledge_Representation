"""Run Session 2 food SPARQL questions against Fuseki or local Oxigraph.

    python run_queries.py
    python run_queries.py oxigraph

Outputs query timings in output/query-timings-<backend>.txt.
"""
import sys
import time
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
FUSEKI_QUERY = 'http://localhost:3031/foodkr/sparql'
QUERIES_PATH = HERE / 'queries.sparql'
TTL_PATH = HERE / 'output' / 'food_knowledge_graph.ttl'


def load_queries():
    blocks = QUERIES_PATH.read_text(encoding='utf-8').split('# --- ')[1:]
    queries = []
    for block in blocks:
        label, separator, query = block.partition(' ---\n')
        if not separator or not query.strip():
            raise ValueError(f'Invalid query block: {label!r}')
        queries.append((label.strip(), query.strip()))
    return queries


def fuseki(query):
    construct = 'CONSTRUCT' in query.upper().split()
    accept = 'application/n-triples' if construct else 'application/sparql-results+json'
    response = requests.post(FUSEKI_QUERY, data={'query': query},
                             headers={'Accept': accept}, timeout=300)
    response.raise_for_status()
    if construct:
        return [line for line in response.text.splitlines() if line.strip()]
    result = response.json()
    if 'boolean' in result:
        return [result['boolean']]
    columns = result['head']['vars']
    return [tuple(binding.get(column, {}).get('value') for column in columns)
            for binding in result['results']['bindings']]


def oxigraph_store():
    import pyoxigraph
    store = pyoxigraph.Store()
    store.load(path=str(TTL_PATH), format=pyoxigraph.RdfFormat.TURTLE)
    return store


def oxigraph(store, query):
    result = store.query(query)
    if isinstance(result, bool) or type(result).__name__ == 'QueryBoolean':
        return [bool(result)]
    if type(result).__name__ == 'QueryTriples':
        return list(result)
    columns = [variable.value for variable in result.variables]
    return [tuple(solution[column].value if solution[column] is not None else None
                  for column in columns) for solution in result]


def main():
    backend = sys.argv[1] if len(sys.argv) > 1 else 'fuseki'
    if backend not in ('fuseki', 'oxigraph'):
        raise SystemExit('Usage: python run_queries.py [fuseki|oxigraph]')
    store = oxigraph_store() if backend == 'oxigraph' else None
    lines = []
    for label, query in load_queries():
        start = time.perf_counter()
        try:
            rows = oxigraph(store, query) if store is not None else fuseki(query)
        except requests.ConnectionError:
            raise SystemExit('Fuseki unavailable at http://localhost:3031; '
                             'start your food project Docker container.')
        elapsed_ms = (time.perf_counter() - start) * 1000
        lines.append(f'[{label}] {len(rows)} rows in {elapsed_ms:.1f} ms')
        for row in rows[:6]:
            lines.append(f'    {row}')
    report = '\n'.join(lines)
    print(report)
    out = HERE / 'output'
    out.mkdir(exist_ok=True)
    destination = out / f'query-timings-{backend}.txt'
    destination.write_text(report + '\n', encoding='utf-8')
    print(f'\nReport saved to: {destination}')


if __name__ == '__main__':
    main()
