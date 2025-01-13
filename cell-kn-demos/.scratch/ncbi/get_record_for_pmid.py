# https://www.ncbi.nlm.nih.gov/books/NBK25499/
import logging
import os
import requests
from urllib import parse

from bs4 import BeautifulSoup

EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EMAIL = "raymond.leclair@gmail.com"
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
PUBMED = "pubmed"
PUBMEDCENTRAL = "pmc"


def get_pmid(title):

    pmid = ""

    search_url = EUTILS_URL + "esearch.fcgi"

    params = {
        "db": PUBMED,
        "term": title,
        "field": "title",
        "retmode": "json",
        # "retmax": 0,
        "email": EMAIL,
        "api_key": NCBI_API_KEY,
    }

    response = requests.get(search_url, params=parse.urlencode(params, safe=","))

    if response.status_code == 200:
        data = response.json()
        resultcount = int(data["esearchresult"]["count"])
        if resultcount > 1:
            logging.warning("PubMed returned more than one result. Returning first.")
        pmid = data["esearchresult"]["idlist"][0]

    elif response.status_code == 429:
        logging.error("Too many requests to NCBI API. Try again later, or use API key.")

    else:
        logging.error("Encountered error in searching PubMed: {response.status_code}")

    return pmid


def get_record(pmid):

    record = {
        "pmid": pmid,
        "pmc_id": "",
        "title": "",
        "abstract": "",
        "keywords": [""],
        "body": "",
    }

    fetch_url = EUTILS_URL + "efetch.fcgi"

    params = {
        "db": PUBMED,
        "id": pmid,
        "rettype": "xml",
        "email": EMAIL,
        "api_key": NCBI_API_KEY,
    }

    response = requests.get(fetch_url, params=parse.urlencode(params, safe=","))

    if response.status_code == 200:
        xml_data = response.text
        fullsoup = BeautifulSoup(xml_data, "xml")

        found = fullsoup.find("ArticleTitle")
        if found:
            record["title"] = found.text

        found = fullsoup.find("Abstract")
        if found:
            record["abstract"] = found.text

        found = fullsoup.find("KeywordList")
        if found:
            record["keywords"] = [tag.text for tag in fullsoup.find_all("Keyword")]

        found = (
            fullsoup.find("PubmedData")
            .find("ArticleIdList")
            .find("ArticleId", {"IdType": "pmc"})
        )
        if found:
            record["pmc_id"] = found.text

            params = {
                "db": PUBMEDCENTRAL,
                "id": record["pmc_id"],
                "rettype": "xml",
                "email": EMAIL,
                "api_key": NCBI_API_KEY,
            }

            response = requests.get(fetch_url, params=parse.urlencode(params, safe=","))

            if response.status_code == 200:
                xml_data = response.text
                fullsoup = BeautifulSoup(xml_data, "xml")

                found = fullsoup.find("pmc-articleset").find("article").find("body")
                if found:
                    record["body"] = found.text

            else:
                logging.error(
                    f"Encountered error in fetching from PubMed Central: {response.status_code}"
                )

    else:
        logging.error(
            f"Encountered error in fetching from PubMed: {response.status_code}"
        )

    return record


def main():
    title = "Single cell transcriptomic profiling identifies molecular phenotypes of newborn human lung cells"
    pmid = get_pmid(title)
    record = get_record(pmid)
    return record


if __name__ == "__main__":
    record = main()
    print(record["title"])
    print(record["pmid"])
