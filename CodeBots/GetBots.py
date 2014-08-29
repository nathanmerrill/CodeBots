#!/usr/bin/env python

import os
import time
import requests
from bs4 import BeautifulSoup
import re

if os.path.exists('bots'):
    os.rename('bots','bots_bak_'+str(time.time()))

os.mkdir('bots')

r = requests.get('http://api.stackexchange.com/2.2/questions/36978/answers?order=desc&sort=activity&site=codegolf')
j = r.json()

ids = []

for i in j['items']:
    ids.append(i['answer_id'])

idlist = '%3B'.join([str(id) for id in ids])

r = requests.get('http://api.stackexchange.com/2.2/answers/'+idlist+'?order=desc&sort=activity&site=codegolf&filter=!9YdnSK0R1')
j = r.json()

for a in j['items']:
    soup = BeautifulSoup(a['body'])
    h1s = soup.find_all('h1')
    bot_name = h1s[0].string
    bot_name = bot_name.title()
    bot_name = re.sub('[^0-9a-zA-Z]+', '', bot_name)
    code_blocks = soup.find_all('code')
    cbl = 0
    bcb = ''
    for cb in code_blocks:
        if len(cb.string)>cbl:
            bcb = cb.string
            cbl = len(cb.string)
    bot_code = bcb
    with open('bots/'+bot_name+'.txt','w') as bot_file:
        bot_file.write(bot_code)


