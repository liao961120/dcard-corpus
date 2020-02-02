#%%
import json
with open('data/dcard_2020-02.jsonl') as f:
    corp = [json.loads(l) for l in f]

#%%
tk_num = 0
male_text_count = 0
female_text_count = 0
text_num = len(corp)
for text in corp:
    if text['gender'] == 1:
        male_text_count += 1
    else:
        female_text_count += 1
    for sent in text['text']:
        tk_num += len(sent)


#%%
readme = f'''
# Dcard post data

This repo hosts the post data retrieved from Dcard API,
which were colleceted for the purpose of building a small corpus.
These posts came from the top-100 popular forums of Dcard. 
Each post is at least 100-character-long and is posted before or on 2020-01-29.

The post data were segmented and PoS tagged using [`ckiplab/ckiptagger`](https://github.com/ckiplab/ckiptagger).

## Files

- `data/dcard_2020-02.jsonl`: The segmented and tagged corpus. Each line is a json string representing a post.
- `data/rawdata.zip`: The raw data retrieved from <https://www.dcard.tw/_api/forums> and <https://www.dcard.tw/_api/posts>.



## Corpus Stats

- number of posts: {text_num}
    - female author: {female_text_count} ({round(100*female_text_count/text_num, 2)}%)
    - male author: {male_text_count}  ({round(100*male_text_count/text_num, 2)}%)
- number of tokens: {tk_num}


## Concordancer

The quickest way to query KWIC concordance in this corpus with [this concordancer](https://kwic.yongfu.name) is using [docker](https://www.docker.com).


Download image:

```bash
docker pull liao961120/dcard
```

Run server:

```bash
docker run -it -p 127.0.0.1:1420:80 liao961120/dcard
```

When you see `Corpus Loaded` printed on the command line, you can visit <https://kwic.yongfu.name> to use the app.

The source code of the concordancer is hosted in [`liao961120/kwic`](https://github.com/liao961120/kwic) and [`liao961120/kwic-backend`](https://github.com/liao961120/kwic-backend).
'''.strip()

with open("README.md", "w") as f:
    f.write(readme)