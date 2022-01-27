import json
import pandas as pd
import requests
import sys
sys.path.append('../')


from ai4ki_utils.det_rbo import rbo
from ai4ki_utils.semschol_request import semschol_request

from datetime import datetime
from os.path import join
from tqdm import tqdm


def comp_mult_queries(queries, min_match=0.7, min_rbo=0.5, p_value=0.9):
    
    '''
    Function for quickly comparing the results of different queries
    Input:  queries (list)    --> list with different queries
            min_match (float) --> treat two queries as equal, if they share at least min_match results
            min_rbo (float)   --> treat two queries as equal, if their ranked biased overlap is > min_rbo
            p_value (float)   --> p-value for calculating rank biased overlap (RBO)
    Output: compare (dir)     --> dictionary with number of matches and RBO for each pair of queries
    '''

    # Set query parameters
    limit = 100
    offset = 0
    params = {
        'offset': str(offset),
        'limit': str(limit),
    }

    # Create dictionary with paper Ids for each query
    id_dict = {}

    # Loop over all queries and send corresponding request to the Semantic Scholar endpoint
    for i in range(len(queries)):
        # Set the Semantic Scholar base url
        url = 'https://api.semanticscholar.org/graph/v1/paper/search?query=' + queries[i]

        # Make the request and fetch the data
        r = requests.get(url, params=params)
        if r.status_code == 200:
            results = r.json()
            n_total = results['total']
            n_papers = len(results['data'])
            print('Found {} papers for query {}'.format(n_total, i))
            if n_total != 0:
                id_dict[i] = [results['data'][j]['paperId'] for j in range(n_papers)]
        else:
           print('ERROR while trying to request data for query {}'.format(i))
    
    # Determine the number of matches between each query pair and how their rankings compare
    count = 1
    matches = {}
    rank_compare = {}
    compare = {}
    keys = [key for key in id_dict]

    print('------------------')
    for k in range(len(id_dict)):
        for l in range(count, len(id_dict)):

            m_key = (keys[k], keys[l])
            # Calculate matches between pair (k,l)
            intersection = set(id_dict[keys[k]]) & set(id_dict[keys[l]])
            matches = len(intersection)

            # Calculate RBO between pair (k,l)
            min_papers = min(len(id_dict[keys[k]]), len(id_dict[keys[l]]))
            rank_compare = rbo(id_dict[keys[k]][:min_papers], id_dict[keys[l]][:min_papers], p_value)

            print("Query {q_a:02d} and query {q_b:02d} have {match:02d} matches and their RBO is {rank:02f}".
                  format(q_a=keys[k], q_b=keys[l], match=matches, rank=rank_compare))

            compare[m_key] = [{'matches': matches/min_papers}, {'rbo': rank_compare}]

        count += 1

    print('------------------')
    print('QUERY SUGGESTIONS:')
    print('------------------')
    for pair in compare.keys():
        if compare[pair][0]['matches'] > min_match or compare[pair][1]['rbo'] > min_rbo:
            print('==> Suggesting to skip either query {} or {}'.format(pair[0], pair[1]))
            
    return compare



def proc_mult_queries(queries, params, out_dir='../results'):
    
    '''
    Function for sending multiple queries to the Semantic Scholar API endpoint
    Input:  queries (list) --> list with user queries
            params (dict)  --> dictionary with search parameters
    Output: None
    '''
    
    XCL_XTNSN, JSN_XTNSN, BBT_XTNSN = '.xlsx', '.json', '.bib'
    
    # Create output directory, if it doesn't exist
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Loop over all queries and send corresponding request to the Semantic Scholar endpoint
    print('PROCESSING QUERIES:')
    print('===================')
    for i in range(len(queries)):

        print('Query {}: {}'.format(i,queries[i].replace('%20',' ')))
              
        # Set the Semantic Scholar base url
        url = 'https://api.semanticscholar.org/graph/v1/paper/search?query=' + queries[i]

        # Make the request and fetch the data
        status, results = semschol_request(url, params)
        if status:
            n_papers = len(results['data'])
            print('==> Formatting publication data {beg} to {end}:'.
                  format(beg=int(params['offset']), end=n_papers + int(params['offset']) - 1))
            results_form = format_semschol_data(n_papers, results)

            # Construct output filename
            time_stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            outfile = "MySemSchol_Search_Query_" + str(i) + '_' + str(time_stamp)
            
            # Export results to EXCEL file
            df_out = pd.DataFrame(results_form)
            df_out.to_excel(join(out_dir, outfile + XCL_XTNSN), engine='openpyxl', index=False)
            
            # Export BibTex-Data to .bib-file
            bibtex_data = '\n\n'.join([item['BibTex'] for item in results_form if item['BibTex'] is not None])
            with open(join(out_dir, outfile + BBT_XTNSN), 'w', encoding='utf-8') as f:
                f.write(bibtex_data)
              
            # Export results to JSON file
            with open(join(out_dir, outfile + JSN_XTNSN), 'w', encoding='utf-8') as f:
                json.dump(results_form, f)

            results_form = []
            results = {}
            df_out = None
            bibtex_data = ''
            url = ''

def format_semschol_data(num_papers, results):
    
    '''
    Function for extracting and formatting the results of a Semantic Scholar search query
    Input:  num_papers (int)   --> number of papers
            results (dict)     --> dictionary containing the Semantic Scholar results
    Output: output_list (list) --> list for Excel dump
    '''
    
    num_authors = None
    output_list = []
    entries_dict = {}

    for i in tqdm(range(num_papers)):
        try:
            entries_dict['Title'] = results['data'][i]['title']
        except:
            entries_dict['Title'] = None

        try:
            abstract = results['data'][i]['abstract']
            entries_dict['Abstract'] = abstract.replace('\n',' ')
        except:
            entries_dict['Abstract'] = None

        authors = ''
        try:
            num_authors = len(results['data'][i]['authors'])
            for j in range(num_authors):
                authors += results['data'][i]['authors'][j]['name']
                if j != num_authors - 1:
                    authors += ', '
        except:
            pass
        entries_dict['Authors'] = authors

        try:
            entries_dict['Year'] = results['data'][i]['year']
        except:
            entries_dict['Year'] = None

        try:
            entries_dict['DOI'] = 'https://doi.org/' + results['data'][i]['externalIds']['DOI']
            bibtex = doi2bib(results['data'][i]['externalIds']['DOI'])
            entries_dict['BibTex'] = bibtex
        except:
            entries_dict['DOI'] = None
            entries_dict['BibTex'] = None

        try:
            if results['data'][i]['fieldsOfStudy'] is not None:
                entries_dict['Fields of Study'] = ', '.join(results['data'][i]['fieldsOfStudy'])
            else:
                entries_dict['Fields of Study'] = None
        except:
            entries_dict['Fields of Study'] = None

        try:
            entries_dict['Citations'] = results['data'][i]['citationCount']
        except:
            entries_dict['Citations'] = None

        try:
            entries_dict['Open Access'] = results['data'][i]['isOpenAccess']
        except:
            entries_dict['Open Access'] = None

        try:
            entries_dict['URL'] = results['data'][i]['url']
        except:
            entries_dict['URL'] = None

        output_list.append(entries_dict)
        entries_dict = {}

    return output_list

def doi2bib(doi):
    
    '''
    Function for converting DOI to BibTex with the Crossref REST API
    Crossref REST API documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    Input:  DOI (str)    --> publication Digital Object Identifier
    Output: bibtex (str) --> publication metadata in BiBTex format
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