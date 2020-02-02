#%%
import sqlite3

#------- Helpers ----------#
def sentPos2textPos(sent_len_lst, sent_id, position):
    if sent_id == 0:
        return position
    for i in range(sent_id):
        position += sent_len_lst[i]
    return position


#%%
import json
import re
import pandas as pd

class Corpus():
    """Query corpus from sqlite database
    """

    def __init__(self, db='data/asbc.sqlite', corp="data/asbc_lite.jsonl"):
        """Initialize a corpus for query
        
        Parameters
        ----------
        db : str, optional
            Relative path to the sqlite database of the corpus, 
            by default 'data/asbc.sqlite'.
        corp : str, optional
            Relative path to the jsonl file of the corpus, 
            by default "data/asbc_lite.jsonl". This file is
            read into memory to enable fast locating of kwic
            in the corpus.
        """

        def functionRegex(pattern, value):
            pat = re.compile(r"\b" + pattern + r"\b")
            #pat = re.compile(pattern)
            return pat.search(value) is not None
        
        # sqlite corpus
        conn = sqlite3.connect(db)
        conn.create_function("REGEXP", 2, functionRegex)
        # Connection object of sqlite3
        self.conn = conn
        self.cursor = conn.cursor()

        # Get column names of tables
        conn.commit()

        # jsonl corpus path
        with open(corp) as f:
            self.corp = [json.loads(line) for line in f ]
    

    def queryOneGram(self, token, pos, matchOpr={'token': '=', 'pos': 'REGEXP'}, gender=None):
        """Query KWIC of one token
        
        Parameters
        ----------
        token : str
            RegEx pattern of the keyword's form.
        pos : str
            RegEx pattern of the keyword's PoS tag. E.g., to 
            search for:

            - Nouns, use ``N.*``
            - Verbs, use ``V.*``

            See the tag set `here <https://github.com/ckiplab/ckiptagger/wiki/POS-Tags>`_.
        matchOpr: dict
            The operator ``<opr>`` given to the SQL command in 
            ``WHERE x <opr> pattern``. Could be one of ``=`` (exact match),
            ``REGEXP`` (uses RegEx to match pattern), or 
            ``LIKE`` (uses ``%`` to match pattern).
            Defaults to exact match for ``token`` and sql pattern for ``pos``.
        gender: int, optional
            Pre-filter SQL database based on the sex of the texts authors.

            - ``0``: female
            - ``1``: male
            - other values: all (no filter)

        Returns
        -------
        pandas.DataFrame
            A pandas dataframe for matching keywords and their
            positional information in the corpus.
        """

        # Add gender for Dcard
        if gender is not None:
            head = '''
                SELECT text_id, sent_id, position, token_id, pos_id FROM oneGram
                    WHERE gender = {} AND '''.format(gender)
        else:
            head = 'SELECT text_id, sent_id, position, token_id, pos_id FROM oneGram WHERE'

        # Optimize search 
        if (token is not None) and (pos is not None):
            sqlQuery = f"""{head}
                        (token_id IN (SELECT token_id FROM token 
                                    WHERE token {matchOpr['token']} ?) ) AND
                        (pos_id IN (SELECT pos_id FROM pos 
                                    WHERE pos {matchOpr['pos']} ?) )
                """
            q = (token, pos)
        elif (token is not None) and (pos is None):
            sqlQuery = f"""{head}
                    token_id IN (SELECT token_id FROM token WHERE token {matchOpr['token']} ?)
                    """
            q = (token, )
        elif (token is None) and (pos is not None):
            sqlQuery = f"""{head}
                    pos_id IN (SELECT pos_id FROM pos WHERE pos {matchOpr['pos']} ?)
                    """
            q = (pos, )
        else:
            raise Exception("Error in queryDB.py:line 98")
            return 1
        
        rows = self.cursor.execute(sqlQuery, q)
        self.conn.commit()

        return pd.DataFrame(data=rows, columns=['text_id', 'sent_id', 'position', 'token_id', 'pos_id'])

    def getNgram(self, text_id, sent_id, position, anchor={'n': 4, 'seed': 1}):
        """Get the ngram of a seed token from the in-memory corpus
        
        The three parameters ``text_id``, ``sent_id``, and ``position`` together
        locates the position of a seed token in the corpus. The info about the ngram
        in which this seed token lies is saved in the parameter ``anchor``.

        Parameters
        ----------
        text_id : int
            The index of the text in the corpus.
        sent_id : int
            The index of the sentence in the text.
        position : int
            The index of the token in the sentence.
        anchor : dict, optional
            Information about the seed token's ngram, by default 
            {'n': 4, 'seed': 1}.

            - ``seed``: The token's position in the ngram 
            - ``n``:  The ngram's length
        
        Returns
        -------
        list
            An ngram stored as (word, tag) pairs in a list.
        """

        sent = self.corp[text_id][sent_id]
        ngram_idx_start = position - anchor['seed']
        ngram = sent[ngram_idx_start:(ngram_idx_start + anchor['n'])]
        if len(ngram) != anchor['n']:
            return None
        return ngram

    def _getQueryMatchSet(self, query):
        matchOpr = {'token': '=', 'pos': 'REGEXP'}
        out = []
        for q in query:
            if q['tk.regex']:
                matchOpr['token'] = 'REGEXP'
            else:
                matchOpr['token'] = '='
            # Query DB for matching tags
            matching_tk = []
            matching_pos = []
            if q['tk'] is not None:
                matching_tk = self.conn.execute(f"""
                    SELECT token from token WHERE token {matchOpr['token']} ?
                    """, (q['tk'],) )
            if q['pos'] is not None:
                matching_pos = self.conn.execute(f"""
                    SELECT pos from pos WHERE pos {matchOpr['pos']} ?
                    """, (q['pos'],) )

            # Convert to python set
            matching_tk = set(t[0] for t in matching_tk)
            matching_pos = set(t[0] for t in matching_pos)
            out.append({'tk': matching_tk, 'pos': matching_pos})
        return out

    def queryNgram(self, query, anchor={'n': 2, 'seed': 1}, gender=None):
        """Query KWIC of phrases
        
        Parameters
        ----------
        query : list
            A list of token objects (dictionaries), with each dictionary
            representing the token in the query string (i.e. token enclosed 
            in the brackets). Returned by :py:func:`queryParser.tokenize`.
        anchor : dict, optional
            Passed to ``anchor`` in :py:meth:`.getNgram`, 
            by default {'n': 2, 'seed': 1}.
        gender : int, optional
            Passed to ``gender`` in :py:meth:`.queryOneGram`, by default None.
        
        Returns
        -------
        pandas.DataFrame
            A pandas dataframe for matching keywords and their
            positional information in the corpus.
        """

        # Query Seed Token
        seed_tk = query[anchor['seed']]['tk']
        seed_pos = query[anchor['seed']]['pos']
        if query[anchor['seed']]['tk.regex']:
            matchOpr = {'token': 'REGEXP', 'pos': 'REGEXP'}
        else:
            matchOpr = {'token': '=', 'pos': 'REGEXP'}
        oneGram = self.queryOneGram(token=seed_tk, pos=seed_pos, matchOpr=matchOpr, gender=gender)

        # Scan through ngrams of the seed token
        valid_rows = []
        queryMatchSet = self._getQueryMatchSet(query)
        for idx, row in oneGram.iterrows():
            ngram = self.getNgram(row.text_id, row.sent_id, row.position, anchor)
            if ngram:  # ngram successfully extracted from sent
                valid = True
                for i in range(len(ngram)):
                    ngram_tk = ngram[i][0]
                    ngram_pos = ngram[i][1]
                    # Check whether token and pos match between query ngram and corpus ngram
                    # If user didn't specify token or pos (i.e. None), they are treated
                    # as equal to whatever tokens or tags are in the corpus
                    tk_equal, pos_equal = False, False
                    if (query[i]['tk'] is None) or (ngram_tk in queryMatchSet[i]['tk']):
                        tk_equal = True
                    if (query[i]['pos'] is None) or (ngram_pos in queryMatchSet[i]['pos']):
                        pos_equal = True
                    if not (tk_equal and pos_equal):
                        valid = False
                        break
            else:
                valid = False
            if valid:
                valid_rows.append(idx)
        
        return oneGram.iloc[valid_rows]


    def concordance(self, text_id, sent_id, position, n=1, left=10, right=10):
        """Retrive all KWIC instances from corpus based on positional information
        
        Parameters
        ----------
        text_id : int
            One of a index of the items (text level of the corpus) in
            the first level of :py:attr:`.corpus`. This is the index
            indicating the order of the texts in the corpus.
        sent_id : int
            One of a index of the items (sentence level of the corpus)
            in the second level of :py:attr:`.corpus`. 
            This is the index indicating the order of the sentences in
            a text.
        position : int
            One of a index of the items (word level of the corpus)
            in the third level of :py:attr:`.corpus`. 
            This is the index indicating the order of the words in
            a sentence.
        n : int, optional
            Keyword length, by default 1
        left : int, optional
            Left context size, in number of tokens, by default 10
        right : int, optional
            Right context size, in number of tokens, by default 10
        
        Returns
        -------
        dict
            A dictionary with:
            
            - ``keyword``: the keyword and its PoS tag
            - ``left`` & ``right``: the left and right context, 
                consisting of tokens and their PoS tags.
        """

        full_text = []
        sent_len = []
        for i, sent in enumerate(self.corp[text_id]):
            sent_len.append(len(sent))
            full_text += sent
        
        keyword_idx = sentPos2textPos(sent_len, sent_id, position)
        keyword = full_text[keyword_idx:(keyword_idx + n)]

        return {
            'keyword': keyword,
            'left': full_text[(keyword_idx - left):keyword_idx],
            'right': full_text[(keyword_idx + n):(keyword_idx + n + right)]
        }

