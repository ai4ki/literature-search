import os
import pandas as pd
import requests
import string

from tqdm import tqdm
from os.path import join


def pdf_download(filename, pdf_dir='./pdfs', fraction=64):
    
    '''
    Function for downloading PDFs from an Excel file that contains direct PDF download links
    Input:  filename (str) --> name of the Excel file with publication records
            dir_path (str) --> path of directory in which to store downloaded PDFs
            fraction (int) --> fraction of characters from publication title for constrcuting PDF filename
    Output: None
    '''
    
    # Read the input Excel file
    df = pd.read_excel(filename, index_col=None)
    pub_data = df.to_dict('records')

    print('==> Downloading PDFs...')

    fail_count = 0
    pub_count = 0
    
    # Loop over publication records
    for pub in tqdm(pub_data):
        pub_count += 1
        link, title = '',''
        for k,v in pub.items():
            if k.lower() in 'title':
                title = v
            if type(v) is str and '.pdf' in v:
                link = v
        if link:
            if title:
                title_frac = title[:fraction].translate(str.maketrans('', '', string.punctuation)).replace(' ', '_')
            else:
                title_frac = str(pub_count)
            pdf_name = title_frac + '.pdf'
            file_path = join(pdf_dir, pdf_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Download PDF
            r = requests.get(link)
            if r.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(r.content)
            else:
                fail_count += 1
        else:
            fail_count += 1

    if fail_count != 0:
        print('{} PDFs could not be downloaded!'.format(fail_count))

    return



def find_pdfs(filename, pdf_dir='./pdfs', fraction=64):
    
    '''
    Function for finding an downloading PDFs for publications listed in an Excel file (using the unpaywall.org REST API)
    Input:  filename (str) --> name of the Excel file with publication records
            dir_path (str) --> path of directory in which to store PDFs
            fraction (int) --> fraction of characters from publication title for constructing PDF filename
    Output: None
    '''
    
    # Set the unpaywall.org base URL
    BASE_URL = 'https://api.unpaywall.org/v2/'
    
    # Read the input Excel file
    df = pd.read_excel(filename, index_col=None)
    pub_data = df.to_dict('records')
    
    print('==> Searching for PDFs...')
    
    fail_count = 0
    pub_count = 0 
    
    # Loop over publication records
    for pub in tqdm(pub_data):
        pub_count += 1
        title, authors, doi = '', '', ''
        for k,v in pub.items():
            if k.lower() in 'title':
                title = v
            if k.lower() in 'authors':
                authors = v
            if k.lower() in 'doi':
                doi = v
        
        # If Excel file doesn't contain DOI, get it from Crossref
        if not doi: 
            doi = get_doi(title, authors)
    
        if doi:
            if title:
                title_frac = title[:fraction].translate(str.maketrans('', '', string.punctuation)).replace(' ', '_')
            else:
                title_frac = str(pub_count)
            pdf_name = title_frac + '.pdf'
            file_path = join(pdf_dir, pdf_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Access the API endpoint
            get_url = BASE_URL + doi + '?email=ai4ki.dev@gmail.com'
            r_api = requests.get(get_url)
            
            if r_api.status_code == 200:
                results = r_api.json()
                try:
                    # Get the golden link
                    pdf_url = results['best_oa_location']['url_for_pdf']
                    r_pdf = requests.get(pdf_url)
                    
                    # Download PDF
                    if r_pdf.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(r_pdf.content)
                    else:
                        fail_count += 1
                except:
                    fail_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1

    print(f'==> Found PDFs for {pub_count-fail_count} publications; failed to find {fail_count} PDFs')
    
    return
            
            
def get_doi(title, author):
    
    '''
    Function for getting DOI from publication title and author(s) with the Crossref REST API
    Crossref REST API documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
    Input:  title (str)       --> publication title
            author (str)      --> publication's author(s)
    Output: Found flag (bool) --> request successful/failed
            doi (str)         --> publication Digital Object Identifier
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
    
    
    
    
