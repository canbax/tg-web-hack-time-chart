import json
import requests
CONF = None
TOKEN = ''

with open('tg_conf.json', 'r') as f:
  CONF = json.loads(f.read())


def run_interpretted_gsql(gsql: str):
  print(gsql)
  domain = CONF['db']['host']
  url = f'{domain}:14240/gsqlserver/interpreted_query'
  usr = CONF['db']['username']
  pwd = CONF['db']['password']

  response = requests.post(url, data=gsql, auth=(usr, pwd))
  obj = json.loads(response.text)
  if obj['error']:
    raise Exception(obj['message'])
  return obj['results']
