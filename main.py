from typing import List
import streamlit as st
from tgApi import run_interpretted_gsql
import datetime
import plotly.graph_objects as go
import json
import copy

with open('tg_conf.json', 'r') as f:
  CONF = json.loads(f.read())


def read_saved_metrics() -> List:
  with open('saved_metrics.json', 'r') as f:
    return json.loads(f.read())


def write_saved_metrics(metrics):
  with open('saved_metrics.json', 'w+') as f:
    f.write(json.dumps(metrics))


def getGSQL(cnt_stat=20, start_date_str='2000-01-01T13:45:30', selected_type='Account', time_unit='YEAR', condition_gsql=''):
  time_prop = CONF['lifetimeProperties'][selected_type]
  if len(condition_gsql) > 1:
    condition_gsql = 'AND (' + condition_gsql + ')'
  print(condition_gsql)
  gsql = """
  INTERPRET QUERY () FOR GRAPH MyGraph {
  SumAccum<INT> @@cnt;
  ListAccum<INT> @@stats;
  ListAccum<DATETIME> @@dates;
  INT count_stat = """ + f'{cnt_stat}; DATETIME startDate = to_datetime("{start_date_str}");' + \
      'INT prev_cnt = 0; INT diff = 0; acc = {' + selected_type + '.*};' + """

  FOREACH i IN RANGE[1, count_stat] DO
    A = SELECT x From acc: x
        WHERE (x.""" + time_prop + ' > startDate AND x.' + time_prop + ' < datetime_add(startDate, INTERVAL 1 ' + time_unit + ')) ' + condition_gsql + """
        ACCUM @@cnt += 1;

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


def show_metric_config_UI():
  st.title('Temporal Analysis')

  metrics = read_saved_metrics()

  metric_names = []
  for metric in metrics:
    metric_names.append(metric['name'])

  selected_metric_name = st.selectbox('Saved Metrics:', tuple(metric_names))
  the_metric = find_metric(selected_metric_name, metrics)

  curr_metric_name = 'metric 0'
  curr_metric_color = '#ff0000'
  curr_metric_gsql = ''
  curr_metric_obj_type = list(CONF['lifetimeProperties'].keys())[0]

  if the_metric is not None:
    curr_metric_name = the_metric['name']
    curr_metric_color = the_metric['color']
    curr_metric_gsql = the_metric['gsql']
    curr_metric_obj_type = the_metric['object_type']

  statCol1, statCol2, statCol3 = st.beta_columns(3)
  with statCol1:
    curr_metric_name = st.text_input('Metric Name', curr_metric_name)
  with statCol2:
    curr_metric_color = st.color_picker('color', curr_metric_color)
  with statCol3:
    obj_types = tuple(CONF['lifetimeProperties'].keys())
    curr_metric_obj_type = st.selectbox('Object Type: ', obj_types,
                                        obj_types.index(curr_metric_obj_type))

  curr_metric_gsql = st.text_input('Rule', curr_metric_gsql)

  # set the date and time
  col1, col2 = st.beta_columns(2)
  with col1:
    start_date = st.date_input('Start Date',     datetime.date(
        2000, 1, 1), min_value=datetime.date(1900, 1, 1))
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

  col1, col2, col3 = st.beta_columns(3)
  is_any_clicked = False
  is_clicked = False
  new_metrics = copy.deepcopy(metrics)

  is_clicked = col1.button('Show Chart')
  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    new_metrics.append({'name': curr_metric_name, 'color': curr_metric_color,
                        'gsql': curr_metric_gsql, 'object_type': curr_metric_obj_type})

  is_clicked = col2.button('Add/Update Metric')
  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    the_metric['name'] = curr_metric_name
    the_metric['color'] = curr_metric_color
    the_metric['gsql'] = curr_metric_gsql
    the_metric['object_type'] = curr_metric_obj_type
    add_update_metric(the_metric, curr_metric_name)

  is_clicked = col3.button('Delete Metric')
  is_any_clicked = is_clicked or is_any_clicked
  if is_clicked:
    delete_metric(curr_metric_name)

  if is_any_clicked:
    print('yooo')
    show_chart(read_saved_metrics(), start_date, start_time,
               curr_num_data_points, curr_time_unit)


def show_chart(metrics, start_date, start_time, curr_num_data_points, curr_time_unit):
  fig = go.Figure()
  for metric in metrics:
    d = str(start_date) + 'T' + str(start_time)
    gsql = getGSQL(curr_num_data_points, d,
                   metric['object_type'], curr_time_unit, metric['gsql'])
    
    res = run_interpretted_gsql(gsql)
    print(res)
    fig.add_trace(go.Bar(
        y=res[0]['@@stats'],
        x=res[1]['@@dates'],
        name=metric['name'],
        marker_color=metric['color']
    ))

  # Here we modify the tickangle of the xaxis, resulting in rotated labels.
  fig.update_layout(barmode='group', xaxis_tickangle=-45)
  st.plotly_chart(fig, use_container_width=True)


show_metric_config_UI()
# show_chart(read_saved_metrics())
