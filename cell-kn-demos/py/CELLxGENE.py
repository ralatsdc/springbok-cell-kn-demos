import logging
import os
from pathlib import Path
import re
import subprocess
from time import sleep
from traceback import print_exception
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import cellxgene_census
import pandas as pd
import requests

DATA_DIR = "../data"

CELLXGENE_DOMAIN_NAME = "cellxgene.cziscience.com"
CELLXGENE_API_URL_BASE = f"https://api.{CELLXGENE_DOMAIN_NAME}"
CELLXGENE_DIR = f"{DATA_DIR}/cellxgene"

CELL_KN_DIR = f"{DATA_DIR}/cell-kn"

HTTPS_SLEEP = 1


def get_metadata_and_datasets(
    organisms=["homo_sapiens", "mus_musculus"], tissues=["lung", "eye", "brain"]
):
    """Use the CZ CELLxGENE Census to obtain all datasets, summary
    cell counts, gene metadata, and, by default, human and mouse
    lung, eye, and brain cell metadata, then write the resulting
    Pandas DataFrames to parquet files, or, if the files exist, read
    them.

    Parameters
    ----------
    organisms : list(str)
        List of organisms, default is ["homo_sapiens", "mus_musculus"]
    tissues : list(str)
        List of tissues, default is ["lung", "eye", "brain"]

    Returns
    -------
    datasets : pd.DataFrame
        DataFrame containing dataset descriptions
    counts : pd.DataFrame
        DataFrame containing summary cell counts
    var : pd.DataFrame
        DataFrame containing gene metadata
    obs : pd.DataFrame
        DataFrame containing cell metadata
    """
    # Create and write, or read DataFrames
    datasets_parquet = f"{CELL_KN_DIR}/datasets.parquet"
    counts_parquet = f"{CELL_KN_DIR}/counts.parquet"
    var_parquet = f"{CELL_KN_DIR}/var.parquet"
    obs_parquet = f"{CELL_KN_DIR}/obs.parquet"
    if (
        not os.path.exists(datasets_parquet)
        or not os.path.exists(counts_parquet)
        or not os.path.exists(var_parquet)
        or not os.path.exists(obs_parquet)
    ):
        print("Opening soma")
        census = cellxgene_census.open_soma(census_version="latest")

        print("Collecting all datasets")
        datasets = census["census_info"]["datasets"].read().concat().to_pandas()

        print("Collecting summary cell counts")
        counts = (
            census["census_info"]["summary_cell_counts"].read().concat().to_pandas()
        )

        var = pd.DataFrame()
        for organism in organisms:
            print(f"Collecting gene metadata for {organism}")
            var = pd.concat(
                [
                    var,
                    cellxgene_census.get_var(
                        census,
                        organism,
                    ),
                ]
            )

        obs = pd.DataFrame()
        for organism in organisms:
            print(f"Collecting cell metadata for {organism}: {tissues} tissue")
            obs_for_org = cellxgene_census.get_obs(
                census,
                organism,
                value_filter=f"tissue_general in {tissues} and is_primary_data == True",
            )
            obs_for_org["organism"] = organism
            obs = pd.concat(
                [
                    obs,
                    obs_for_org,
                ]
            )

        print("Closing soma")
        census.close()

        print("Writing datasets parquet")
        datasets.to_parquet(datasets_parquet)

        print("Writing summary cell counts parquet")
        counts.to_parquet(counts_parquet)

        print("Writing gene metadata parquet")
        var.to_parquet(var_parquet)

        print("Writing cell metadata parquet")
        obs.to_parquet(obs_parquet)

    else:

        print("Reading datasets parquet")
        datasets = pd.read_parquet(datasets_parquet)

        print("Reading summary cell counts parquet")
        counts = pd.read_parquet(counts_parquet)

        print("Reading gene metadata parquet")
        var = pd.read_parquet(var_parquet)

        print("Reading cell metadata parquet")
        obs = pd.read_parquet(obs_parquet)

    return datasets, counts, var, obs


def get_title(citation):
    """Get the title given a dataset citation. Note that only wget
    succeeded for Cell Press journals, and neither requests nor wget
    succeeded for The EMBO Journal and Science.

    Parameters
    ----------
    citation : str
        Dataset citation

    Returns
    -------
    title : str
        Title of publication associated with the dataset
    """
    # Need a default return value
    title = None

    # Compile patterns for finding the publication URL and article
    # title
    p1 = re.compile("Publication: (.*) Dataset Version:")
    p2 = re.compile("articleName : '(.*)',")

    # Assign CSS selectors for selecting article title elements
    selectors = [
        "h1.c-article-title",
        "h1.article-header__title.smaller",
        "div.core-container h1",
        "h1.content-header__title.content-header__title--xx-long",
        "h1#page-title.highwire-cite-title",
    ]

    # Find the publication URL
    m1 = p1.search(citation)
    if not m1:
        logging.warning(f"Could not find citation URL for {citation}")
        return title
    citation_url = m1.group(1)
    print(f"Getting title for citation URL: {citation_url}")

    # Attempt to get the publication page using requests
    print(f"Trying requests")
    sleep(HTTPS_SLEEP)
    response = requests.get(citation_url)
    try_wget = True
    if response.status_code == 200:
        html_data = response.text

        # Got the page, so parse it, and try each selector
        fullsoup = BeautifulSoup(html_data, features="lxml")
        for selector in selectors:
            selected = fullsoup.select(selector)
            if selected:

                # Selected the article title, so assign it
                if len(selected) > 1:
                    logging.warning(
                        f"Selected more than one element using {selector} on soup from {citation_url}"
                    )
                title = selected[0].text
                try_wget = False
                break

    if try_wget:

        # Attempt to get the publication page using wget
        print(f"Trying wget")
        sleep(HTTPS_SLEEP)
        completed_process = subprocess.run(
            ["curl", "-L", citation_url], capture_output=True
        )
        html_data = completed_process.stdout

        # Got the page, so parse it, and search for the title
        fullsoup = BeautifulSoup(html_data, features="lxml")
        found = fullsoup.find_all("script")
        if found and len(found) > 4:
            m2 = p2.search(found[4].text)
            if m2:
                title = m2.group(1)

    print(f"Found title: '{title}' for citation URL: {citation_url}")

    return title


def get_and_download_dataset_h5ad_file(dataset_series):
    """Get the dataset filename and download the dataset file.

    Parameters
    ----------
    dataset_series : pd.Series
        A row from the dataset DataFrame

    Returns
    -------
    dataset : str
       The dataset filename
    """
    # Need a default return value
    dataset_filename = None

    # Get the dataset object
    collection_id = dataset_series.collection_id
    dataset_id = dataset_series.dataset_id
    dataset_url = f"{CELLXGENE_API_URL_BASE}/curation/v1/collections/{collection_id}/datasets/{dataset_id}"
    sleep(HTTPS_SLEEP)
    response = requests.get(dataset_url)
    response.raise_for_status()
    if response.status_code != 200:
        logging.error(f"Could not get dataset for id {dataset_id}")
        return

    data = response.json()
    if dataset_id != data["dataset_id"]:
        logging.error(
            f"Response dataset id: {data['dataset_id']} does not equal specified dataset id: {dataset_id}"
        )
        return

    # Find H5AD files, if possible
    assets = data["assets"]
    for asset in assets:
        if asset["filetype"] != "H5AD":
            continue

        # Found an H5AD file, so download it, if needed
        dataset_filename = Path(urlparse(asset["url"]).path).name
        dataset_filepath = f"{CELLXGENE_DIR}/{dataset_filename}"
        if not os.path.exists(dataset_filepath):
            print(f"Downloading dataset file: {dataset_filepath}")
            with requests.get(asset["url"], stream=True) as response:
                response.raise_for_status()
                with open(dataset_filepath, "wb") as df:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        df.write(chunk)
            print(f"Dataset file: {dataset_filepath} downloaded")

        else:
            print(f"Dataset file: {dataset_filepath} exists")

    return dataset_filename
