# Helper functions for ai4ki literature review project

import requests
from tqdm import tqdm
from scholarly import scholarly
  
    
def format_gs_data(pub_counter, results):
    
    '''
    Function for extracting and formatting the results of a Google Scholar search query
    Input:  pub_counter (int)  --> number of papers
            results (dict)     --> dictionary containing the Google Scholar results
    Output: output_list (list) --> list for Excel dump
    '''
    
    output_list = []
    entries_dict = {}

    for i in tqdm(range(pub_counter)):

        title = results[i]['bib']['title']
        authors = ', '.join(results[i]['bib']['author'])

        entries_dict['Title'] = title
        try:
            abstract = results[i]['bib']['abstract']
            entries_dict['Abstract'] = abstract.replace('\n',' ')
        except:
            entries_dict['Abstract'] = None

        entries_dict['Authors'] = authors

        try:
            entries_dict['Year'] = results[i]['bib']['pub_year']
        except:
            entries_dict['Year'] = None

        doi = get_doi(title, authors)
        entries_dict['DOI'] = doi

        if doi is not None:
            entries_dict['BibTex'] = doi2bib(doi)
        else:
            entries_dict['BibTex'] = None

        try:
            entries_dict['Citations'] = results[i]['num_citations']
        except:
            entries_dict['Citations'] = None

        try:
            entries_dict['URL'] = results[i]['pub_url']
        except:
            entries_dict['URL'] = None

        output_list.append(entries_dict)
        entries_dict = {}

    return output_list


def doi2bib(doi):
    
    '''
    Function for converting DOI to BibTex with the Crossref REST API
    Crossref REST API documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    Input:  DOI (str)     --> publication Digital Object Identifier
    Output: bibtex (str) --> publication metadata in BibTex-format
    '''

    CROSSREF_URL = "http://api.crossref.org/"
    bibtex = None

    url = "{}works/{}/transform/application/x-bibtex"
    url = url.format(CROSSREF_URL, doi)
    r = requests.get(url)

    if r.status_code == 200:
        bibtex = r.content
        bibtex = str(bibtex, "utf-8")

    return bibtex


def get_doi(title, author):
    
    '''
    Function for getting DOI from publication title and author(s) with the Crossref REST API
    Crossref REST API documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    Input:  title (str)  --> publication title
            author (str) --> publication's author(s)
    Output: doi (str)    --> publication Digital Object Identifier
    '''
    
    CROSSREF_URL = "http://api.crossref.org/"

    title = title.replace(' ', '%20')
    author = author.replace(' ', '%20')
    doi = None

    url = "{}works?query.bibliographic={},{}&rows=1"
    url = url.format(CROSSREF_URL, title, author)
    r = requests.get(url)

    if r.status_code == 200:
        data = r.json()
        doi = data['message']['items'][0]['DOI']

    return doi