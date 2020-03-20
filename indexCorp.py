RAW_CORPUS = 'data/dcard.jsonl'
LITE_CORPUS = 'data/dcard_lite.jsonl'
INDEXED_CORPUS = 'data/dcard.sqlite'


import copy

def revDict(dict_):
    return dict((v, k) for k, v in dict_.items())

class IndexedCorp():

    def __init__(self, corp):
        """Create an indexed corpus object
        
        Parameters
        ----------
        corp : [type]
            [description]
        """
        
        words = set()
        tags = set()
        for text in corp:
            if isinstance(text, dict):
                try:
                    text = text['text']
                except:
                    raise Exception("corpus structure not expected.")
            for sent in text:
                for word, tag in sent:
                    words.add(word)
                    tags.add(tag)
        wd = dict((w, i) for i, w in enumerate(words))
        td = dict((t, i) for i, t in enumerate(tags))
        
        # Initialize
        if isinstance(corp[0], list):
            self.corpus = [
                [ [ (wd[word], td[tag]) for word, tag in sent ] for sent in text ] for text in corp
                ]
        elif isinstance(corp[0], dict):
            indexedCorp = copy.deepcopy(corp)
            for i, text in enumerate(indexedCorp):
                indexedCorp[i]['text'] = [ 
                    [ (wd[w], td[t]) for w, t in sent ] for sent in text['text']
                ]
            self.corpus = indexedCorp
            self.corpus_lite = [ text['text'] for text in corp ]
        else:
            raise Exception("corpus structure not expected.")
        
        self.tokens = words
        self.tags = tags
        self.wd = wd #revDict(wd)
        self.td = td #revDict(td)
        self.rev_wd = revDict(wd)
        self.rev_td = revDict(td)


if __name__ == "__main__":
    import json
    import os

    # Clean up
    if os.path.isfile(INDEXED_CORPUS):
        os.unlink(INDEXED_CORPUS)

    # Load original corpus
    with open(RAW_CORPUS) as f:
        corp = [json.loads(line) for line in f]
    # Index Corpus
    corp = IndexedCorp(corp)

    # Save lite corpus (for finding kwic)
    with open(LITE_CORPUS, "w") as f:
        for text in corp.corpus_lite:
            json.dump(text, f, ensure_ascii=False)
            f.write('\n')

    # Initiate sqlite DB
    import sqlite3
    conn = sqlite3.connect(INDEXED_CORPUS)
    c = conn.cursor()
    #conn.close()

    # Create Table: token
    c.execute("""
        CREATE TABLE token(
            token_id INTEGER PRIMARY KEY, 
            token varchar(128) NOT NULL
            )
        """)
    # Create Table: token
    c.execute("""
        CREATE TABLE pos(
            pos_id INTEGER PRIMARY KEY, 
            pos varchar(32) NOT NULL
            )
        """)
    
    # Add data to Table: token
    rows = []
    for key in corp.wd:
        token = key
        token_id = corp.wd[key]
        rows.append( (token_id, token) )
    c.executemany("INSERT INTO token (token_id, token) VALUES (?,?)", rows)

    # Add data to Table: pos
    rows = []
    for key in corp.td:
        pos = key
        pos_id = corp.td[key]
        rows.append( (pos_id, pos) )
    c.executemany("INSERT INTO pos (pos_id, pos) VALUES (?,?)", rows)
    # Index token
    c.execute("""
        CREATE UNIQUE INDEX idx_token 
            ON token (token, token_id);  """)
    # Index pos
    c.execute("""
        CREATE UNIQUE INDEX idx_pos 
            ON pos (pos, pos_id);  """)
    conn.commit()
    # rows = c.execute("SELECT * FROM pos")


    # Create Table: oneGram
    #c.execute("DROP TABLE oneGram;")
    c.execute("""
        CREATE TABLE oneGram(
            text_id INTEGER NOT NULL, 
            sent_id INTEGER NOT NULL, 
            position INTEGER NOT NULL,
            gender INTEGER NOT NULL,
            token_id INTEGER NOT NULL,
            pos_id INTEGER NOT NULL,
            FOREIGN KEY (token_id) REFERENCES token(token_id),
            FOREIGN KEY (pos_id) REFERENCES pos(pos_id)
            )""")

    # Add data to Table: oneGram
    rows = []
    for text_id, text in enumerate(corp.corpus):
        for sent_id, sent in enumerate(text['text']):
            for position, (token_id, pos_id) in enumerate(sent):
                rows.append( (text_id, sent_id, position, text['gender'], token_id, pos_id) )

    c.executemany('''INSERT INTO oneGram (text_id, sent_id, position, gender, token_id, pos_id) 
                                VALUES (?,?,?,?,?,?)''', rows)
    conn.commit()

    # Index oneGram
    c.execute("""
        CREATE INDEX idx_gender_token_pos
            ON oneGram (gender, token_id, pos_id, text_id, sent_id, position);
    """)
    c.execute("""
        CREATE INDEX idx_gender_pos_token
            ON oneGram (gender, pos_id, token_id, text_id, sent_id, position);
    """)
    conn.commit()
