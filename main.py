from typing import List
import streamlit as st
import streamlit.components.v1 as components
from tgApi import run_interpretted_gsql
import datetime
import plotly.graph_objects as go
import json
import copy
import pandas as pd
import graphistry

st.set_page_config(layout='wide')
graphistry.register(api=3, protocol="https", server="hub.graphistry.com",
                    username="canbax", password="good4all")

# time unit to seconds of that unit
time_unit2stamp = {'YEAR': 31622400, 'MONTH': 2678400,
                   'DAY': 86400, 'HOUR': 3600, 'MINUTE': 60, 'SECOND': 1}

curr_charts = []

with open('tg_conf.json', 'r') as f:
  CONF = json.loads(f.read())


def read_saved_metrics() -> List:
  with open('saved_metrics.json', 'r') as f:
    s = f.read()
    if len(s) > 1:
      return json.loads(s)
    return []


def write_saved_metrics(metrics):
  with open('saved_metrics.json', 'w+') as f:
    f.write(json.dumps(metrics))


def show_on_graphistry(nodes, edges):
  iframe_url = graphistry.bind(node='v_id').nodes(
      nodes).edges(edges, 'from_id', 'to_id').plot(render=False)
  components.iframe(iframe_url, height=750)


def get_gsql4chart(cnt_stat=20, start_date_str='2000-01-01T13:45:30', selected_type='Account', time_unit='YEAR', condition_gsql='', agg=''):
  time_prop = CONF['lifetimeProperties'][selected_type]
  graph_name = CONF['db']['graph_name']
  if len(condition_gsql) > 1:
    condition_gsql = 'AND (' + condition_gsql + ')'
  agg_prop = '1'
  if len(agg) > 0:
    agg_prop = 'x.' + agg
  gsql = """
  INTERPRET QUERY () FOR GRAPH """ + graph_name + """ {
  SumAccum<INT> @@cnt;
  ListAccum<INT> @@stats;
  ListAccum<DATETIME> @@dates;
  INT count_stat = """ + f'{cnt_stat}; DATETIME startDate = to_datetime("{start_date_str}");' + \
      'INT prev_cnt = 0; INT diff = 0; acc = {' + selected_type + '.*};' + """

  FOREACH i IN RANGE[1, count_stat] DO
    A = SELECT x From acc: x
        WHERE (x.""" + time_prop + ' > startDate AND x.' + time_prop + ' < datetime_add(startDate, INTERVAL 1 ' + time_unit + ')) ' + condition_gsql + """
        ACCUM @@cnt += """ + agg_prop + """;

    diff = @@cnt - prev_cnt;

    @@stats += diff;
    @@dates += startDate;
    startDate = datetime_add(startDate, INTERVAL 1 """ + time_unit + """);
    prev_cnt = @@cnt;

  END;

  print @@stats;
  print @@dates;
  }
  """
  return gsql


def get_gsql4graph(start_date_str='2000-01-01T00:00:00', end_date_str='2020-01-01T00:00:00', selected_type='Account', condition_gsql=''):
  graph_name = CONF['db']['graph_name']
  time_prop = CONF['lifetimeProperties'][selected_type]
  if len(condition_gsql) > 1:
    condition_gsql = 'AND (' + condition_gsql + ')'
  gsql = """
  INTERPRET QUERY () FOR GRAPH """ + graph_name + """ {
    SetAccum<EDGE> @@edgeSet;
  """ + f' DATETIME startDate = to_datetime("{start_date_str}");' + \
      f' DATETIME endDate = to_datetime("{end_date_str}");' + ' acc = {' + selected_type + '.*};' + """
  
  A = SELECT x From acc:x-(:e)-:x2
      WHERE (x.""" + time_prop + ' > startDate AND x.' + time_prop + ' < endDate) ' + condition_gsql + """
      ACCUM @@edgeSet += e;
  B = SELECT x2 From acc:x-(:e)-:x2
      WHERE (x.""" + time_prop + ' > startDate AND x.' + time_prop + ' < endDate) ' + condition_gsql + """;
        
  print A;
  print B;
  print @@edgeSet;
  }
  """
  return gsql


def find_metric(name: str, obj_list: List):
  for obj in obj_list:
    if obj['name'] == name:
      return obj
  return None


def find_metric_idx(name: str, obj_list: List):
  cnt = 0
  for obj in obj_list:
    if obj['name'] == name:
      return cnt
    cnt = cnt + 1
  return -1


def delete_metric(name: str):
  metrics = read_saved_metrics()
  idx = find_metric_idx(name, metrics)
  if idx > -1:
    del metrics[idx]
  write_saved_metrics(metrics)


def add_update_metric(metric, name: str):
  metrics = read_saved_metrics()
  idx = find_metric_idx(name, metrics)
  if idx > -1:
    metrics[idx] = metric
  else:
    metrics.append(metric)
  write_saved_metrics(metrics)


def build_UI():
  st.title('Temporal Analysis')

  metrics = read_saved_metrics()

  metric_names = []
  for metric in metrics:
    metric_names.append(metric['name'])
  st.header('Timely Metrics')
  selected_metric_name = st.selectbox('Saved Metrics:', tuple(metric_names))
  the_metric = find_metric(selected_metric_name, metrics)

  curr_metric_name = 'metric 0'
  curr_metric_agg = ''
  curr_metric_color = '#ff0000'
  curr_metric_gsql = ''
  curr_metric_obj_type = list(CONF['lifetimeProperties'].keys())[0]

  if the_metric is not None:
    curr_metric_name = the_metric['name']
    curr_metric_color = the_metric['color']
    curr_metric_gsql = the_metric['gsql']
    curr_metric_obj_type = the_metric['object_type']
    curr_metric_agg = the_metric['agg']

  statCol1, statCol2, statCol3, statCol4 = st.beta_columns(4)
  with statCol1:
    curr_metric_name = st.text_input('Metric Name', curr_metric_name)
  with statCol2:
    curr_metric_color = st.color_picker('color', curr_metric_color)
  with statCol3:
    obj_types = tuple(CONF['lifetimeProperties'].keys())
    curr_metric_obj_type = st.selectbox('Object Type: ', obj_types,
                                        obj_types.index(curr_metric_obj_type))
  with statCol4:
    curr_metric_agg = st.text_input('Aggregate', curr_metric_agg)

  curr_metric_gsql = st.text_input('Rule', curr_metric_gsql)

  # set the date and time
  col1, col2 = st.beta_columns(2)
  with col1:
    start_date = st.date_input('Start Date',     datetime.datetime(
        2000, 1, 1), min_value=datetime.datetime(1900, 1, 1))
  with col2:
    start_time = st.time_input('and Time', datetime.time(0, 0))
  TIME_UNITS = ('YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND')
  # time unit and count
  col3, col4 = st.beta_columns(2)
  with col3:
    curr_time_unit = st.selectbox('Time Unit: ', TIME_UNITS)
  with col4:
    curr_num_data_points = st.number_input('Number of data points',
                                           max_value=1000, value=20, min_value=0, step=1)

  col2, col3 = st.beta_columns(2)
  is_any_clicked = False
  is_clicked = False
  new_metrics = copy.deepcopy(metrics)

  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    new_metrics.append({'name': curr_metric_name, 'color': curr_metric_color,
                        'gsql': curr_metric_gsql, 'object_type': curr_metric_obj_type, 'agg': curr_metric_agg})

  is_clicked = col2.button('Add/Update Metric')
  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    if the_metric is None:
      the_metric = {}
    the_metric['name'] = curr_metric_name
    the_metric['color'] = curr_metric_color
    the_metric['gsql'] = curr_metric_gsql
    the_metric['object_type'] = curr_metric_obj_type
    the_metric['agg'] = curr_metric_agg
    add_update_metric(the_metric, curr_metric_name)

  is_clicked = col3.button('Delete Metric')
  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    delete_metric(curr_metric_name)

  show_chart(read_saved_metrics(), start_date, start_time,
             curr_num_data_points, curr_time_unit)
  show_graph_UI(metrics, start_date, start_time,
                curr_num_data_points, curr_time_unit)


def show_chart(metrics, start_date, start_time, curr_num_data_points, curr_time_unit):
  global curr_charts
  curr_charts = []
  if metrics is None or len(metrics) < 1:
    return
  fig = go.Figure()
  for metric in metrics:
    d = str(start_date) + 'T' + str(start_time)
    gsql = get_gsql4chart(curr_num_data_points, d,
                          metric['object_type'], curr_time_unit, metric['gsql'], metric['agg'])
    try:
      res = run_interpretted_gsql(gsql)
    except Exception as e:
      st.error('GSQL ERROR')
      st.error(e)
      return
    fig.add_trace(go.Bar(
        y=res[0]['@@stats'],
        text=res[0]['@@stats'],
        textposition='outside',
        x=res[1]['@@dates'],
        name=metric['name'],
        marker_color=metric['color']
    ))
    curr_charts.append(
        {'name': metric['name'], 'x': res[1]['@@dates'], 'y': res[0]['@@stats']})

  # Here we modify the tickangle of the xaxis, resulting in rotated labels.
  fig.update_layout(barmode='group', xaxis_tickangle=-45)
  st.plotly_chart(fig, use_container_width=True)


def get_estimated_graph_elem_cnt(d1: datetime.datetime, d2: datetime.datetime):
  global curr_charts
  cnt = 0
  for metric in curr_charts:
    x = metric['x']
    y = metric['y']
    for idx, xi in enumerate(x):
      d = datetime.datetime.strptime(xi, '%Y-%m-%d %H:%M:%S')
      if d >= d1 and d <= d2:
        cnt += y[idx]
  return cnt


def show_graph_UI(metrics, start_date, start_time, curr_num_data_points, curr_time_unit):
  st.header('Show as Graph')
  start_date = datetime.datetime.combine(start_date, start_time)
  ts = (start_date - datetime.datetime(1970, 1, 1)).total_seconds()
  date_arr = [start_date]
  for i in range(curr_num_data_points):
    d = datetime.datetime.fromtimestamp(
        ts + (i + 1) * time_unit2stamp[curr_time_unit])
    date_arr.append(d)

  (s1, s2) = st.select_slider('select range',
                              date_arr, value=(date_arr[0], date_arr[-1]))
  # s1 = datetime.datetime.strptime(s1, '%Y-%m-%d %H:%M:%S')
  # s2 = datetime.datetime.strptime(s2, '%Y-%m-%d %H:%M:%S')
  is_get_graph = st.button(
      'Get Graph elements in range ' + str(s1) + ' - ' + str(s2))
  if is_get_graph and metrics is not None and len(metrics) > 0:
    nodes = []
    edges = []
    for metric in metrics:
      gsql = get_gsql4graph(s1, s2, metric['object_type'], metric['gsql'])
      try:
        res = run_interpretted_gsql(gsql)
      except Exception as e:
        st.error('GSQL ERROR')
        st.error(e)
        return
      src_nodes = extract_node_attributes(res[0]['A'])
      nodes.extend(src_nodes)
      tgt_nodes = extract_node_attributes(res[1]['B'])
      nodes.extend(tgt_nodes)
      edgeSet = res[2]['@@edgeSet']
      edges.extend(edgeSet)

    if len(nodes) < 1:
      st.text('Empty response!')
      return
    df1 = pd.DataFrame(nodes)
    df2 = pd.DataFrame(edges)
    show_on_graphistry(df1, df2)


def extract_node_attributes(nodes):
  l = []
  for node in nodes:
    att = node['attributes']
    att['v_id'] = node['v_id']
    att['v_type'] = node['v_type']
    l.append(att)
  return l


def show_gsql_error_msg(resp):
  if isinstance(resp, str) and resp.startswith('ERROR!'):
    st.error('GSQL error: ' + resp)


build_UI()
