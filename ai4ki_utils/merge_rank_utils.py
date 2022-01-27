import os
import json
import string

from itertools import combinations
from os import listdir
from os.path import isfile, join
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity



def get_pub_data(path='./results'):

    '''
    Fetches publication data from all JSON-files in directory 'path'
    Input: path (str)       --> path to directory with JSON-files
    Output: pub_data (list) --> list with publication data from each JSON-file
    '''
    
    file_names = [f for f in listdir(path) if isfile(join(path, f)) and f[-4:] == 'json']
    n_files = len(file_names)
    print('Found {} files in directory {}:'.format(n_files, path))
    print('========================================')

    pub_data = []
    for i in range(n_files):
        with open(os.path.join(path, file_names[i]), 'r', encoding='utf-8') as f:
            file_data = list(json.load(f))
            print('Data file {}: {}'.format(i, file_names[i]))
            print('\tFile lists {} publications'.format(len(file_data)))
            print('----------------------------------------')
        pub_data.append(file_data)

    return pub_data


def check_pub_data(pub_data):
    
    '''
    Check publication data and remove items that doesn't have an entry in the title field
    Input:  pub_data (list) --> list of lists with publication data from different queries
    '''
    
    n_files = len(pub_data)

    print('==> Checking publication data for entries without title...')
    for k in range(n_files):
        count = 0
        for item in pub_data[k]:
            if item['Title'] is None:
                pub_data[k].remove(item)
                count += 1
        print(f"Deleted {count} entries from file {k}")
        
        
def rank_score(pub_list, norm, key='Rank score'):
    
    '''
    Calculates linear rank score (rs) for a ranked list of n items (0<=rs<=1)
    Input:  pub_list (list) --> list with publication data from different queries
            norm (int)      --> norm for calculating rank score
            name (str)      --> key for the score in item directory
    Output: pub_list (list) --> list with rs-expanded publication data from different queries
    '''
    
    n_files = len(pub_list)

    for i in range(n_files):
        n_items = len(pub_list[i])
        scores = [r/(norm-1.0) for r in range(n_items)]

        for j, item in enumerate(pub_list[i]):
            item[key] = scores[j]

    print('==> Normalized rank scores calculated and added to publication data')
    
   
def match_score(pub_list, keywords):
    
    '''
    Calculates the title and abstract match scores
    Input:  pub_list (list)       --> list with publication data from different queries
            keywords (list)       --> list of keywords to match in title or abstract        
    Output: pub_list (list)       --> list with rs-expanded publication data from different queries
    '''
    
    n_keywords = len(keywords)
    n_files = len(pub_list)

    for i in range(n_files):
             
        for j, item in enumerate(pub_list[i]):
            title_score = 0
            abstract_score = 0
            title = ''
            abstract = ''
            
            if item['Title'] is not None: 
                title = item['Title'].lower()
            if item['Abstract'] is not None:
                abstract = item['Abstract'].lower()
            
            for k in keywords:
                title_score += k in title
                abstract_score += k in abstract
                
            item['Title match score'] = title_score / n_keywords
            item['Abstract match score'] = abstract_score / n_keywords

    print('==> Title and abstract match scores calculated and added to publication data')
    

def sim_score(pub_list, document):
    
    '''
    Calculates the similarity score between a dcoument and a publication's abstract using the tf-idf-algorithm
    Input:  pub_list (list) --> list of lists with publication data from different queries
            document (str)  --> document to be compared against a publications's abstract
    Output: pub_list (list) --> input data with similarity score added for each publications
    '''
    
    vectorizer = TfidfVectorizer()
    n_files = len(pub_list)
    
    for i in range(n_files):
             
        for j, item in enumerate(pub_list[i]):
            
            if item['Abstract'] is not None:
                abstract = item['Abstract'].lower()
                embeddings = vectorizer.fit_transform([document, abstract])
                cosine_similarities = cosine_similarity(embeddings[0:1], embeddings[1:]).flatten()
                item['Similarity score'] = cosine_similarities[0]
            else:
                item['Similarity score'] = 0.0
                    
    print('==> Similarity scores calculated and added to publication data')
    
    
def get_proc_titles(pub_data):
    
    '''
    Retrieve publication titles from publication data and process them for matching
    Input:  pub_data (list)        --> list of lists with publication data from different queries
    Output: pub_data_titles (list) --> list of sets with processed publication titles
            pub_data_idx (list)    --> list of directories, which link processed titles to data file
    '''
    
    n_files = len(pub_data)

    pub_data_titles = []
    pub_data_idx = []

    print('==> Processing titles...')
    for k in range(n_files):
        pub_titles = []
        title2idx = {}
        for idx, item in enumerate(pub_data[k]):
            # Remove punctuation from title and lowercase as notation might not be consistent across databases
            title = item['Title'].translate(str.maketrans('', '', string.punctuation)).lower()

            # For each title, store the index of the item for identification later
            title2idx[title] = idx
            pub_titles.append(title)

        # For each data file, store publication titles as sets for easy duplicate identification below
        '''
        NOTE: There's a problem, when a title appears multiple times in one data file with different authors
        (e.g. because it's a collection of articles where each individual article doesn't have its own title).
        With the following code, we only keep one of the corresponding articles (the one which is last on the list).
        Since we currently see no other option than to use the title as a unquie article id, we have to accpet 
        this for now (and hope that such cases don't occur too often... ;).
        ''' 
        pub_data_titles.append(set(pub_titles))
        pub_data_idx.append(title2idx)

    return pub_data_titles, pub_data_idx


def find_matches(pub_data_titles, n_files):
    
    '''
    Find matches of papers for all possible combinations of publication data files
    Input:  pub_data_titles (list) --> list of sets with processed publication titles
            n_files (int)          --> number of publication lists/queries (=len(pub_data_titles))
    Output: pub_data_matches (dir) --> directory with the following structure:
               key (tuple)             --> tuples indicating the queries which have matches
               value (list):           --> list of matching titles
    '''
    
    pub_data_matches = {}
    # Things get tricky only, if there are more than two data files:
    print('==> Finding matches...')
    if n_files > 2:
        max_tup = n_files
        for nt in range(2, max_tup + 1):
            # Get all tuples of length nt <= n_files
            n_tuples = list(combinations(range(max_tup), nt))

            # Loop of all tuples of length nt
            for tuples in n_tuples:
                # Create list with the nt data files in tuples
                sub_set = [pub_data_titles[t] for t in tuples]
                # Find the matching titles in the nt data files
                match = list(set.intersection(*sub_set))
                pub_data_matches[tuples] = match
                print('\tFound {n:03d} matching papers in data files {tp}'.format(n=len(match), tp=tuples))
                sub_set, match = [], {}

    elif n_files == 2:
        pub_data_matches[(0, 1)] = list(set.intersection(*pub_data_titles))
        print('\tFound {} matching papers in the two files.'.format(len(pub_data_matches[(0, 1)])))
    else:
        print('\tERROR: No enough files for matching--got {}, need 2 or more!'.format(n_files))

    return pub_data_matches


def merge_pub_data(pub_data, pub_data_titles, pub_data_idx, pub_data_matches={}, use_find_matches=False):
    
    '''
    Merge all publication data into one final list
    Input:  pub_data (list)             --> list of lists with publication data from different queries
            pub_data_titles (list)      --> list of sets with processed publication titles
            pub_data_idx (list)         --> list of directories, which link processed titles to data file
            pub_data_matches (dir)      --> directory with match-title-info
            use_find_matches (bool)     --> switch for using/not using output of function find_matches
    Output: pub_data_merge_final (list) --> list with directories for each selected publication
    '''
    
    n_files = len(pub_data)

    print('==> Merging publication data...')
    # Remove duplicates and merge lists
    pub_data_merge = list(set.union(*pub_data_titles))
    print('Number of unique papers: ', len(pub_data_merge))

    pub_data_merge_final = []
    for title in pub_data_merge:
        idx = -1
        found = (-1, -1)
        sum_rs = 0.0
        n_rs = 0
        entries_dict = {}
        occ_count = 1

        for file in range(n_files):
            try:
                idx = pub_data_idx[file][title]
                sum_rs += pub_data[file][idx]['Rank score']
                n_rs += 1
                found = (file, idx)
            except:
                pass

        if use_find_matches:
            for key, values in pub_data_matches.items():
                if title in values:
                    occ_count = len(key)

        entries_dict['Title'] = pub_data[found[0]][found[1]]['Title']
        entries_dict['Authors'] = pub_data[found[0]][found[1]]['Authors']
        entries_dict['Abstract'] = pub_data[found[0]][found[1]]['Abstract']
        entries_dict['BibTex'] = pub_data[found[0]][found[1]]['BibTex']

        # Care for non-int entries for year in publication data...
        year = pub_data[found[0]][found[1]]['Year']
        if type(year) == str:
            if year.isdigit():
                entries_dict['Year'] = int(year)
            else:
                entries_dict['Year'] = -1
        elif type(year) == int:
            entries_dict['Year'] = year
        else:
            entries_dict['Year'] = -1

        # Care for non-int entries for citations in publication data...
        cites = pub_data[found[0]][found[1]]['Citations']
        if type(cites) == str:
            if cites.isdigit():
                entries_dict['Citations'] = int(cites)
            else:
                entries_dict['Citations'] = -1
        elif type(cites) == int:
            entries_dict['Citations'] = cites
        else:
            entries_dict['Citations'] = -1

        entries_dict['Rank score'] = sum_rs / n_rs
        entries_dict['Title match score'] = pub_data[found[0]][found[1]]['Title match score']
        entries_dict['Abstract match score'] = pub_data[found[0]][found[1]]['Abstract match score']
        entries_dict['Similarity score'] = pub_data[found[0]][found[1]]['Similarity score']
        
        if use_find_matches:
            entries_dict['Occurrence count'] = occ_count

        pub_data_merge_final.append(entries_dict)

    return pub_data_merge_final


def inspect_pubs(pub_data_merge_final, idx_start=0):
    
    '''
    Merge all publication data into one final list
    Input:  pub_data_merge_final (list) --> list with directories for each selected publication
    Output: pub_data_final (list)       --> final list with directories for each selected publication
    '''
    
    ir_index = -1
    n_pubs = len(pub_data_merge_final)

    pub_data_final = []
    for idx in range(idx_start, n_pubs):

        pub = pub_data_merge_final[idx]
        print('=====================================================================================================')
        for k, v in pub.items():
            print(k, ':')
            print(v)
            print('-------------------------------------------------------------------------------------------------')

        print('==> KEEP THIS PUBLICATION?')
        keep_no_keep = input('yes/no')
        if keep_no_keep == 'yes':
            pub_data_final.append(pub)
        elif keep_no_keep == 'stop':
            ir_index = idx - 1
            break

    return ir_index, pub_data_final

