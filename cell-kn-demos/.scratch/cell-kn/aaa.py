import json
from pprint import pprint

with open("../data/nlm-kn/HLCA_CellRef_matching_ver3_import1.json", "r") as fp:
    gdata = json.load(fp)

max_disease_score = 0.0

unq_marker_names = set()
unq_marker_ids = set()
unq_disease_ids = set()
unq_drug_ids = set()
unq_name_id_tuples = set()
unq_gene_id_disease = set()
unq_drug_gene_id = set()

for _, cell_type_dict in gdata["cell_types"].items():
    for _, marker_names_dict in cell_type_dict.items():
        for marker_name, marker_ids_dict in marker_names_dict.items():
            unq_marker_names |= set([marker_name])
            for _, marker_ids in marker_ids_dict.items():
                unq_marker_ids |= set(marker_ids)
                for marker_id in marker_ids:
                    unq_name_id_tuples |= set([(marker_name, marker_id)])

for gene_id, gene_ids_dict in gdata["gene_ids"].items():
    for resource, resources_list in gene_ids_dict["resources"].items():
        if resource == "diseases":
            for disease in resources_list:
                if disease["score"] > max_disease_score:
                    unq_disease_ids |= set([disease["id"]])
                    unq_gene_id_disease |= set([(gene_id, disease["id"])])
                    if disease["id"][0:5] == "MONDO":
                        pprint(disease)
        if resource == "drugs":
            for drug in resources_list:
                unq_drug_ids |= set([drug["id"]])
                unq_drug_gene_id |= set([(drug["id"], gene_id)])


print(f"Maximum disease score: {max_disease_score}")
print()
print(f"Number of unique marker names: {len(unq_marker_names)}")
print(f"Number of unique marker ids: {len(unq_marker_ids)}")
print(f"Number of unique disease ids: {len(unq_disease_ids)}")
print(f"Number of unique drug ids: {len(unq_drug_ids)}")
