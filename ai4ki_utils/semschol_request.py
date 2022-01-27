import requests

def semschol_request(url, params):
    # Function for sending a GET request to the Semantic Scholar API endpoint
    # Input variables: url (str) --> API endpoint, params (dir) --> query parameters
    # Output variables: status (boolean) --> True, if request returned results
    #                   results (dir) --> publication data

    status = False
    results = None

    r = requests.get(url, params=params)
    if r.status_code == 200:
        results = r.json()
        if results['total'] != 0:
            status = True
            print('---------------------------------')
            print('Your query returned {total} papers'.format(total=results['total']))
            print('---------------------------------')
            if results['total'] == 0:
                print('==> Try another one!')
    elif r.status_code == 504:
        print('Error code 504: Time out -- try again')
    else:
        print('Error code {code}'.format(code=r.status_code))

    return status, results