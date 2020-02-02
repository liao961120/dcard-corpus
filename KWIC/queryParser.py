import re

def tokenize(string):
    """Parse query string for ngram into token objects
    
    Parameters
    ----------
    string : str
        Query string with each token enclosed in a pair 
        of square brackets. In each token, the tag ``word``
        and ``pos`` could be given as ``[word="他們" pos="N.*"]``.
        To search with regex in ``word``, append ``.regex`` to
        ``word``: ``[word.regex="們$" pos="N.*"]``.
        ``pos`` by default uses regex search.
    
    Returns
    -------
    list
        A list of token objects (dictionaries), with each dictionary
        representing the token in the query string (i.e. token enclosed 
        in the brackets). Each token has three key-value pairs:

        - `tk`: ``str``. The pattern of the word to search for.
        - `tk.regex`: ``bool``. Whether to use regex search with word.
        - `pos`: ``str``. The pattern of the pos tag to search for.
    """

    # Deal with single exact match of token
    if string.find("[") == -1:
        return [{
            'tk': string,
            'pos': None,
            'tk.regex': False,
        }]

    # Scan through the string to find matching brackets
    tokens = []
    openPos =[]
    depth = 0
    for i, char in enumerate(string):
        if char == '[':
            openPos.append(i)
            depth += 1
        if char == ']':
            start = openPos.pop()
            depth -= 1
            tokens.append({
                'start': start,
                'end': i,
                'inside': string[start+1:i],
                'depth': depth
            })
    # Get matching brackets at first depth level
    tk_pat = re.compile('''word=['"]([^'"]+)['"]''')
    pos_pat = re.compile('''pos=['"]([^'" ]+)['"]''')
    tkRegEx_pat = re.compile('''word.regex=['"]([^'"]+)['"]''')

    output = []
    for tk in tokens:
        if tk['depth'] == 0:
            token = tk_pat.findall(tk['inside'])
            tkRegEx = tkRegEx_pat.findall(tk['inside'])
            token = tkRegEx if tkRegEx else token
            pos = pos_pat.findall(tk['inside'])
            output.append({
                'tk': token[0] if len(token) > 0 else None,
                'pos': pos[0] if len(pos) > 0 else None,
                'tk.regex': True if tkRegEx else False,
            })
    return output

#%%
def querySpecificity(queryObj={'tk': '^我們$', 'pos': 'N%', 'tk.regex': True}):
    """Score a token object for specificity.
    
    Parameters
    ----------
    queryObj : dict
        A token object in a list returned by :py:func:`.tokenize`.
    
    Returns
    -------
    float
        A point indicating the specificity of the token. Higher score
        means the token is more specific and may result in fewer query
        results in the corpus. This point is used to determine the
        seed token of an ngram to search in the corpus (to boost 
        performance).
    """

    status = {
        'token': {
            'has_regEx': False,
            'zh_len': 0
        },
        'pos': {
            'has_wildcard': False,
            'tag_len': 0,
        }
    }
    #-------- Check token pattern --------#
    # List of regEx metacharacters indicating specific pattern
    regEx_meta = ['^', '$', '[', ']', '?' '{', '}', '(', ')', '|']
    if queryObj['tk.regex'] and \
       set(queryObj['tk']).intersection(regEx_meta):
        status['token']['has_regEx'] = True
    # Check chinese character
    if queryObj['tk'] is not None:
        for char in queryObj['tk']:
            if char > u'\u4e00' and char < u'\u9fff':
                status['token']['zh_len'] += 1

    #------ Check pos tag pattern --------#
    if queryObj['pos'] is not None:
        if queryObj['pos'].find('%') != -1:
            status['pos']['has_wildcard'] = True
        for char in queryObj['pos']:
            if re.match('[A-Za-z]', char):
                status['pos']['tag_len'] += 1
    
    return 1.2 * status['token']['zh_len'] + status['token']['has_regEx'] + \
        0.5 * status['pos']['tag_len'] - 0.2 * status['pos']['has_wildcard']

