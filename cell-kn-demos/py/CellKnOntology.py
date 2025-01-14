import argparse
from pathlib import Path

import pandas as pd
from rdflib.term import Literal, URIRef

import ArangoDB as adb
from CellOntology import (
    OBO_DIRPATH,
    VALID_VERTICES,
    load_triples_into_adb_graph,
    parse_obo,
    parse_term,
)


def read_cel_kn_schema(cell_kn_dirname, cell_kn_filename):
    """Read slightly, manually modified Cell KN schema Excel file.

    Parameters
    ----------
    cell_kn_dirname : str | Path
        The name of the directory containing the Cell KN schema
    cell_kn_filename : str
        The name of the file containing the Cell KN shema

    Returns
    -------
    schema : pd.DataFrame
        The DataFrame containing the schema name triples
    relations : pd.DataFrame
        The DataFrame containing the relations of the schema names to
        labels and CURIEs
    """
    schema = pd.read_excel(Path(cell_kn_dirname) / cell_kn_filename, sheet_name=0).iloc[
        :, 0:6
    ]
    relations = pd.read_excel(
        Path(cell_kn_dirname) / cell_kn_filename, sheet_name=2
    ).iloc[:, 0:3]

    return (
        schema.loc[
            schema["Connections"] == "Class-Class",
            ["Subject Node", "Predicate Relation", "Object Node", "Connections"],
        ].copy(),
        relations,
    )


def create_triples(schema, relations, ro=None):
    """Create triples by translating schema names to labels, and to
    CURIEs with a default URL.

    Parameters
    ----------
    schema : pd.DataFrame
        The DataFrame containing the schema name triples
    relations : pd.DataFrame
        The DataFrame containing the relations of the schema names to
        labels and CURIEs

    Returns
    -------
    triples : list(tuple)
        List of tuples which contain each triple
    """
    triples = []

    # Create mapping from name to label
    n2l = {}
    for _, row in relations.iterrows():
        n2l[row.iloc[0].replace("_class", "")] = row.iloc[1]

    # Create mapping from name to CURIE
    n2c = {}
    for _, row in relations.iterrows():
        n2c[row.iloc[0].replace("_class", "")] = row.iloc[2]

    # Map name to term, and collect ids
    ids = set()

    def n2t(name):
        if not name in n2c:
            print(f"Skipping name: {name}")
            return

        curie = n2c[name]
        if "rdf:type" in curie:
            term = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

        elif "rdfs:subClassOf" in curie:
            term = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")

        else:
            term = URIRef(f"http://purl.obolibrary.org/obo/{curie.replace(':', '_')}")

        id, _, _, _, _ = parse_term(term, ro=ro)
        ids.add(id)

        return term

    # Create triples by translating schema names to labels, and to
    # CURIEs with a default URL.
    for _, row in schema.iterrows():

        # Create subject from row
        s = n2t(row.iloc[0])
        if s is None:
            print(f"Skipping row due to subject: {s}")
            continue

        # Create triple to label subject
        if row.iloc[0] in n2l:
            triple = (
                s,
                URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                Literal(n2l[row.iloc[0]]),
            )
            triples.append(triple)

        # Create predicate from row
        p = n2t(row.iloc[1])
        if p is None:
            print(f"Skipping row due to predicate: {p}")
            continue

        # Create object from row
        o = n2t(row.iloc[2])
        if o is None:
            print(f"Skipping row due to object: {o}")
            continue

        # Create triple to label object
        if row.iloc[2] in n2l:
            triple = (
                o,
                URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                Literal(n2l[row.iloc[2]]),
            )
            triples.append(triple)

        triple = (s, p, o)
        triples.append(triple)

    return triples, ids


def main():

    parser = argparse.ArgumentParser(description="Load Cell KN schema")
    parser.add_argument(
        "--cell-kn-dirname",
        default=Path("../data/cell-kn"),
        help="name of directory containing Cell KN schema",
    )
    parser.add_argument(
        "--cell-kn-filename",
        default=Path("Cell_Phenotype_KG_Schema_v2_2025-01-13.xlsx"),
        help="name of file containing Cell KN schema",
    )

    args = parser.parse_args()

    db_name = "NIH-NLM"
    graph_name = "Cell-KN-RL"

    ro_filename = "ro.owl"
    log_filename = f"{graph_name}.log"

    print(f"Reading {args.cell_kn_dirname / args.cell_kn_filename}")
    schema, relations = read_cel_kn_schema(args.cell_kn_dirname, args.cell_kn_filename)

    print("Creating triples")
    ro, _, _ = parse_obo(OBO_DIRPATH, ro_filename)
    triples, ids = create_triples(schema, relations, ro=ro)

    print("Creating ArangoDB database and graph, and loading triples")
    VALID_VERTICES.update(ids.difference(set([None, "BFO", "IAO", "RO"])))
    db = adb.create_or_get_database(db_name)
    adb_graph = adb.create_or_get_graph(db, graph_name)
    vertex_collections = {}
    edge_collections = {}
    load_triples_into_adb_graph(
        triples, adb_graph, vertex_collections, edge_collections, ro=ro
    )


if __name__ == "__main__":
    main()
