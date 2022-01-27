import os
import requests
import string

from tqdm import tqdm
from os.path import join

def core_request(url, params):
    
    '''
    Function for sending a GET request to the CORE API endpoint
    Input:  url (str)        --> URL of API endpoint
            params (dir)     --> query parameters
    Output: status (boolean) --> True, if request returned results
            results (dir)    --> publication data
    '''
    
    status = False
    results = None

    r = requests.get(url, params=params)
    
    if r.status_code == 200:
        results = r.json()
        if results['totalHits'] is not None:
            status = True
            print('---------------------------------')
            print('Your query returned {total} papers'.format(total=results['totalHits']))
            print('---------------------------------')
            if results['totalHits'] == 0:
                print('==> Try another one!')
    elif r.status_code == 401:
        print('Error code {code}: Invalid or no API key provided!'.format(code=r.status_code))
    elif r.status_code == 429:
        print('Error code {code}: Too many requests in given amount of time!'.format(code=r.status_code))
    else:
        print('Something went seriously wrong -- try restarting runtime!')

    return status, results


def core_download(results, dir_path='../pdfs', n_down=100, fraction=30):
    
    '''
    Function for downloading PDFs from the CORE Collection
    Input:  results (dir)  --> list of dictionaries with formatted publication data
            dir_path (str) --> path to download directory
            n_down (int)   --> number of PDFs to download
            fraction (int) --> fraction of characters from publication title for PDF filename
    Output: None
    '''
    
    assert n_down <= len(results), 'Number of requested downloads larger than number of stored publications!'

    fail_count = 0

    print('Downloading {} PDFs'.format(n_down))

    for i in tqdm(range(n_down)):
        pdf_link = results[i]['CORE PDF link']

        if pdf_link is not None:
            title = results[i]['Title']
            title_frac = title[:fraction].translate(str.maketrans('', '', string.punctuation)).replace(' ', '_')
            filename = 'CORE_' + title_frac + '.pdf'
            file_path = join(dir_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            r = requests.get(pdf_link)
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
