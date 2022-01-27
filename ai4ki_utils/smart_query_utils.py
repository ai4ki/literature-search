import nltk
import pprint
import spacy
import random
import requests
import transformers
import yake

from nltk.corpus import stopwords as sw
from nltk.corpus import wordnet as wn
from transformers import pipeline
from transformers import GPT2Tokenizer
transformers.logging.set_verbosity_error()
nltk.download('wordnet')


def query_constructor(text, org_kw=False, language='en', num_keywords=10, top_k=3, ngram_limit=2, dedup_value=0.5):
    
    '''
    Function for constructing a Boolean search string from an input text using the YAKE keyword extractor
    Input:  text (str)          --> text from which to extract the keywords
            org_kw (Boolean)    --> use all keywords or only proper nouns, nouns and verbs (True/False)
            language (str)      --> language of the input text
            num_keywords (int)  --> maximum number of keywords to extract
            top_k (int)         --> top k keywords for the serach string (to be AND-chained)
            ngram_limit (int)   --> maximum keyword length
            dedup_value (float) --> parameter to control duplication of words in different keywords
    Output: qs (str)            --> constructed Boolean search string
            keywords (list)     --> list of keyword tuples (term, relevance)
    '''

    # Create keyword extractor object
    extractor = yake.KeywordExtractor(lan=language, n=ngram_limit, dedupLim=dedup_value, top=num_keywords, features=None)
    
    # Extract keywords from input text 
    all_keywords = extractor.extract_keywords(text)

    # Delete irrelevant keywords based on POS
    nlp = spacy.load("en_core_web_sm")
    rel_keywords = []
    for t in all_keywords:
        term = t[0]
        if len(term.split()) == 1:
            doc = nlp(term)
            term_pos = doc[0].pos_
            term_lemma = doc[0].lemma_
            if term_pos == "PROPN" or term_pos == "NOUN" or term_pos =="VERB":
                rel_keywords.append((term_lemma,t[1]))
        else:
            rel_keywords.append(t)
    
    # Choose which keywords to use for search string construction
    if org_kw:
        keywords = all_keywords
    else:
        keywords = rel_keywords
    
    # Constrcut Boolean search string from keywords
    qs = ''
    t_count = 0
    if top_k < len(keywords):
        qs = '('
        for t in keywords:
            t_count +=1
            term = t[0].lower()
            if len(term.split()) > 1:
                term = '\"' + t[0].lower() + '\"'
            if t_count < top_k: 
                qs += term + ' AND '
            elif t_count == top_k:
                qs += term + ') AND ('
            elif t_count > top_k and t_count != len(keywords):
                qs += term + ' OR '
            elif t_count == len(keywords):
                qs += term + ')'
    elif top_k == len(keywords):
        qs = ''
        for t in keywords:
            t_count +=1
            term = t[0].lower()
            if len(term.split()) > 1:
                term = '\"' + t[0].lower() + '\"'
            if t_count < top_k: 
                qs += term + ' AND '
            elif t_count == top_k:
                qs += term    
    else:
        print('ERROR: Number of extracted keywords smaller than value for top_k --> adjust your parameters!')
            
    if qs:
        print('THESE ARE YOUR RANKED KEYWORDS:')
        pp = pprint.PrettyPrinter()
        pp.pprint(keywords)
        print('\nTHIS IS YOUR SEARCH STRING:')
        print(qs)
    
    return qs, keywords


def query_synonymizer(search_string, term=""):
     
    '''
    Function for synonymizing search terms in Boolean search string 
    Input:  search_string (str) --> Boolean search string to be synonymized
            term (str)          --> term to be replaced with OR-chained synonyms
    Output: syn_string (str)    --> synonymized Boolean search string
    '''
    
    assert term in search_string, "ERROR: Your chosen term doesn't appear in the search string--check for typos!"
    
    term = term.lower()
    syn_string = search_string
    
    # Find synonyms for term using wordnet
    syns_tmp = []
    for syn in wn.synsets(term):
        for lem in syn.lemmas():
            syns_tmp.append(lem.name())
    
    # Eliminate synonyms appearing more than once
    synonyms = list(set(syns_tmp))
    num_syns = len(synonyms)
    
    # Replace term with OR-chained synonyms
    if num_syns > 1:
        if term in synonyms:
            new_term = '('
        else:
            new_term = '(' + term + ' OR '
        
        for i in range(num_syns-1): 
            new_term += synonyms[i] + ' OR '
            
        new_term += synonyms[-1] + ')'
        syn_string = syn_string.replace(term,new_term)
    else:
        print(f'Sorry, no synonyms found for \"{term}\"') 
        
    return syn_string
    

def query_composer(text, maxq_length=20, temperature=0.9):
    
    '''
    Function to create Boolean search stroing from an input text using GPT-2
    Input: text (str)          --> input text
           maxq_length (int)   --> maximum number of tokens for GPT-2 output 
           temperature (float) --> GPT-2 parameter for controlling output randomness
    Output: Search string suggestion
    '''
    
    with open('qs_example.txt', 'r', encoding='utf-8') as f: example = f.read()
    
    prompt = f"{example}\n\nText: {text}\n\Search string:"
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    n_tokens = len(tokenizer(prompt)['input_ids'])
    max_tokens = n_tokens + maxq_length 
    generator = pipeline('text-generation', model='gpt2')
    queries = generator(prompt,
                        max_length=max_tokens,
                        temperature=temperature,
                        top_p=1.0,
                        return_full_text=False,
                        num_return_sequences=1)

    return queries[0]['generated_text']

    
def find_synonyms(query):
    
    '''
    Function for finding synonyms for every non-stopword in 'query'
    Input:  query (str)  --> some string
    Output: q_alt (list) --> list with synonyms for each non-stopword in 'query'
    '''
    
    q = query.lower()
    stop_words = set(sw.words('english'))

    # Tokenize query (the simple way...)
    q_tokens = q.split()

    # Find synonyms for each query token
    q_syns = []
    for w in q_tokens:
        if not '!' in w:
            if not w in stop_words:
                synonyms = [w]
                for syn in wn.synsets(w):
                    for lem in syn.lemmas():
                        synonyms.append(lem.name())
                q_syns.append(list(set(synonyms)))
            else:
                q_syns.append(w)
        else:
            w = w.replace('!', '')
            w = w.replace('&', ' ')
            q_syns.append(w)

    return q_syns


def us_vs_uk_en(query, direction):
    
    '''
    Function for translating a query from Amerivan to British English an vice versa
    Input:  query (str)     --> some string
            direction (str) --> direction of translation: us2uk or uk2us
    Output: query (str)     --> translated string
    '''
    
    url ="https://raw.githubusercontent.com/hyperreality/American-British-English-Translator/master/data/british_spellings.json"
    british_to_american_dict = requests.get(url).json()    

    for british_spelling, american_spelling in british_to_american_dict.items():
        if direction == "uk2us":
            query = query.replace(british_spelling, american_spelling)
        elif direction == "us2uk":
            query = query.replace(american_spelling, british_spelling)

    return query


def rand_query(query_syns):
    
    '''
    Function for creating a query by randomly choosing synonyms of terms
    Input:  query_syns (list) --> list containing either words or lists of words' synonyms
    Output: query_rndm (str)  --> reformulation of query by randomly picking synoyms
    '''
    
    query_rndm = ''
    for q in query_syns:
        if q: 
            if type(q) == str:
                query_rndm += q
            if type(q) == list:
                query_rndm += random.choice(q)
            query_rndm += ' '

    print('==> How about this one:', query_rndm)
    
    return query_rndm
