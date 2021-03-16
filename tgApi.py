import json
import requests
CONF = None
TOKEN = ''

with open('tg_conf.json', 'r') as f:
  CONF = json.loads(f.read())


# def get_token():
#   global TOKEN
#   domain = CONF['db']['host']
#   secret = CONF['db']['secret']
#   url = f'{domain}:9000/requesttoken?secret={secret}'

#   response = requests.request('GET', url, data={})
#   resp = json.loads(response.text)
#   TOKEN = resp['token']
#   return TOKEN


def run_interpretted_gsql(gsql: str):
  domain = CONF['db']['host']
  url = f'{domain}:14240/gsqlserver/interpreted_query'
  usr = CONF['db']['username']
  pwd = CONF['db']['password']

  response = requests.post(url, data=gsql, auth=(usr, pwd))
  obj = json.loads(response.text)
  if obj['error']:
    return 'error: ' + obj['message']
  return obj['results']

  
  ## WORKING CODE !!!!
  # data = 'INTERPRET QUERY () FOR GRAPH MyGraph { print "heloo"; }'
  # response = requests.post('https://customer360.i.tgcloud.io:14240/gsqlserver/interpreted_query', data=data, auth=('tigergraph', '123456'))
  # print(response.text)

# get_token()
