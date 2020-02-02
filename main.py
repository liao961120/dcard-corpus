import falcon
import json
import io
from falcon_cors import CORS
from KWIC.queryDB import Corpus
import KWIC.queryParser as Parser

# Initialize corpus
DB = 'data/dcard.sqlite'
CORP = 'data/dcard_lite.jsonl'
CONCORDANCE_CACHE = []

C = Corpus(db=DB, corp=CORP)
############  DEBUGGING ##############
print("Corpus Loaded")
############ _DEBUGGING ##############


class nGram(object):
    def on_get(self, req, resp):
        global CONCORDANCE_CACHE
        global DB
        params = {
            'query': '''[word="" pos=""][pos='' word="他"][word.regex='打' pos='V.*']''',
            'left': '10',
            'right': '10',
            'gender': 3,
        }
        # Parse query string
        for k, v in req.params.items():
            params[k] = v
        params['gender'] = int(params['gender'])
        params['left'] = int(params['left'])
        params['right'] = int(params['right'])
        ############ DEBUGGING ##############
        print("Recieved request!!!")
        ############ _DEBUGGING ##############
        
        # Find seed token for DB search
        params['query'] = Parser.tokenize(params['query'])
        score = [ Parser.querySpecificity(q) for q in params['query'] ]
        seed_idx = score.index(max(score))
        seed_token = params['query'][seed_idx]
        anchor = {
            'n': len(params['query']), 
            'seed': seed_idx}
        matchOpr = {
            'token': 'REGEXP' if seed_token['tk.regex'] else '=', 
            'pos': 'REGEXP'}

        # Query Database
        if DB.endswith('asbc.sqlite') or params['gender'] not in [0, 1]:
            params['gender'] = None
        if anchor['n'] == 1:
            query = C.queryOneGram(token=seed_token['tk'], pos=seed_token['pos'], matchOpr=matchOpr, gender=params['gender'])
        elif anchor['n'] > 1:
            query = C.queryNgram(params['query'], anchor, gender=params['gender'])
        else:
            raise Exception("Bug at nGram.on_get() line 70 for querying DB")

        # Retrieve Concordance
        concord_params = {
            'n': anchor['n'],
            'left': params['left'],
            'right': params['right']
        }
        results = [{}] * query.shape[0]
        for i, (idx, row) in enumerate(query.iterrows()):
            results[i] = C.concordance(text_id=row.text_id, sent_id=row.sent_id, position=(row.position - anchor['seed']) ,**concord_params)
        
        # Response to frontend
        ############ DEBUGGING ##############
        print("Sending response...")
        ############ _DEBUGGING ##############
        resp.status = falcon.HTTP_200  # This is the default status
        CONCORDANCE_CACHE = results
        resp.body =json.dumps(results, ensure_ascii=False)
        ############ DEBUGGING ##############
        print("Response sent !!!")
        ############ _DEBUGGING ##############


    def on_get_export(self, req, resp):
        global CONCORDANCE_CACHE
        params = {
            'kwtag': True,
            'ctxtag': True,
        }
        for k, v in req.params.items():
            if v == "true":
                params[k] = True
            else:
                params[k] = False

        # Process concordance to tsv
        with open("cache.tsv", "w") as f:
            f.write('left\tkeyword\tright\n')
            for kwic in CONCORDANCE_CACHE:
                if params['kwtag']:
                    keyword = ' '.join(f"{word}/{tag}" for word, tag in kwic['keyword'])
                else: 
                    keyword = ' '.join(f"{word}" for word, tag in kwic['keyword'])
                if params['ctxtag']:
                    left = ' '.join(f"{word}/{tag}" for word, tag in kwic['left'])
                    right = ' '.join(f"{word}/{tag}" for word, tag in kwic['right'])
                else:
                    left = ''.join(f"{word}" for word, tag in kwic['left'])
                    right = ''.join(f"{word}" for word, tag in kwic['right'])
                f.write(f'{left}\t{keyword}\t{right}\n')
        resp.content_type = 'text/tsv'
        resp.status = falcon.HTTP_200  # This is the default status
        with open("cache.tsv", 'r') as f:
            resp.body = f.read()
        
        

#---------- API settings -----------#
# falcon.API instances are callable WSGI apps
cors = CORS(allow_all_origins=True)  # Allow access from frontend
app = falcon.API(middleware=[cors.middleware])

# Resources are represented by long-lived class instances
ngram = nGram()
#export = Export()

# things will handle all requests to the '/things' URL path
app.add_route('/query', ngram)
app.add_route('/export', ngram, suffix='export')



if __name__ == '__main__':
    from wsgiref import simple_server

    port = 1420
    print(f"Start serving at http://localhost:{port}")
    httpd = simple_server.make_server('localhost', port, app)
    httpd.serve_forever()