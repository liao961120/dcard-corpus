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

- number of posts: 18540
    - female author: 11573 (62.42%)
    - male author: 6967  (37.58%)
- number of tokens: 5284288


## Concordance App

The quickest way to query KWIC concordance in this corpus with [this concordance app](https://kwic.yongfu.name) is using [docker](https://www.docker.com).


Download image:

```bash
docker pull liao961120/dcard
```

Run server:

```bash
docker run -it -p 127.0.0.1:1420:80 liao961120/dcard
```

When you see `Corpus Loaded` printed on the command line, you can visit <https://kwic.yongfu.name> to use the app.