from pathlib import Path
from pprint import pprint
from urllib.parse import urlparse

from rdflib import Graph

from CellOntology import (
    OBO_DIRPATH,
    OBO_PURLS,
    count_triple_types,
    collect_fnode_triples,
    collect_bnode_triple_sets,
    create_bnode_triples_from_bnode_triple_sets,
)

for obo_purl in OBO_PURLS:
    obo_filename = Path(urlparse(obo_purl).path).name
    print(f"\nParsing {OBO_DIRPATH / obo_filename} to populate rdflib graph")
    rdf_graph = Graph()
    rdf_graph.parse(OBO_DIRPATH / obo_filename)

    # TODO: Review namespaces before using
    # print(f"Parsing {OBO_DIRPATH / obo_filename} to identify ids")
    # _, _, ids = parse_obo(OBO_DIRPATH, obo_filename)
    # print(ids)

    print("Counting triple types in rdflib graph")
    triple_types = count_triple_types(rdf_graph)
    pprint(triple_types)

    # print("Printing all triples in rdflib graph")
    # triples = []
    # triples_filename = obo_filename.replace(".owl", "_triples.txt")
    # with open(triples_filename, "w") as fp:
    #     for triple in rdf_graph:
    #         fp.write(str(triple) + "\n")

    # print("Collecting and printing all filled node triples in rdflib graph")
    # fnode_triples = collect_fnode_triples(rdf_graph)
    # fnode_triples_filename = obo_filename.replace(".owl", "_fnode_triples.txt")
    # with open(fnode_triples_filename, "w") as fp:
    #     for fnode_triple in fnode_triples:
    #         fp.write(str(fnode_triple) + "\n")

    # print("Collecting and printing all blank node triple sets in rdflib graph")
    # bnode_triple_sets = {}
    # ro_filename = "ro.owl"
    # ro, _, _ = parse_obo(OBO_DIRPATH, ro_filename)
    # collect_bnode_triple_sets(rdf_graph, bnode_triple_sets, use="subject", ro=ro)
    # collect_bnode_triple_sets(rdf_graph, bnode_triple_sets, use="object", ro=ro)
    # bnode_triple_sets_filename = obo_filename.replace(".owl", "_bnode_triple_sets.txt")
    # with open(bnode_triple_sets_filename, "w") as fp:
    #     pprint(bnode_triple_sets, fp)

    # print("Creating and printing all blank node triples in rdflib graph")
    # bnode_triples, ignored_triples = create_bnode_triples_from_bnode_triple_sets(
    #     bnode_triple_sets, ro=ro
    # )
    # bnode_triples_filename = obo_filename.replace(".owl", "_bnode_triples.txt")
    # with open(bnode_triples_filename, "w") as fp:
    #     for bnode_triple in bnode_triples:
    #         fp.write(str(bnode_triple) + "\n")
