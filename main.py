import streamlit as st
from tgApi import run_interpretted_gsql
import datetime
import plotly.graph_objects as go
import json


def read_saved_metrics():
  with open('saved_metrics.json', 'r') as f:
    return json.loads(f.read())


def getGSQL(cnt_stat=20, start_date_str='2000-01-01T13:45:30', selected_type='Account', time_unit='YEAR'):

  gsql = """
  INTERPRET QUERY () FOR GRAPH MyGraph {
  SumAccum<INT> @@cnt;
  ListAccum<INT> @@stats;
  ListAccum<DATETIME> @@dates;
  INT count_stat = """ + f'{cnt_stat}; DATETIME startDate = to_datetime("{start_date_str}");' + \
      'INT prev_cnt = 0; INT diff = 0; acc = {' + selected_type + '.*};' + """

  FOREACH i IN RANGE[1, count_stat] DO
    A = SELECT x From acc: x
        WHERE(x.CreatedDate > startDate AND x.CreatedDate < datetime_add(startDate, INTERVAL 1 """ + time_unit + """))
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


def build_UI():
  st.title('Temporal Analysis')

  print(read_saved_metrics())

  selected_metric = st.selectbox('Saved Metrics:', ('Metric 0', 'Metric 1'))
  st.write('Selected metric:', selected_metric)

  # set the date and time
  statCol1, statCol2, statCol3 = st.beta_columns(3)
  with statCol1:
    obj_type = st.text_input('Metric Name', 'Metric 0')
    st.write('You selected:', obj_type)

  with statCol2:
    obj_type = st.color_picker('color')
    st.write('Color: ', obj_type)

  with statCol3:
    obj_type = st.selectbox('Object Type: ', ('Account', 'Campaign'))
    st.write('You selected:', obj_type)

  st.text_input('Rule')

  # set the date and time
  col1, col2 = st.beta_columns(2)
  with col1:
    d = st.date_input('Start Date',     datetime.date(2019, 7, 6))
    st.write('Your birthday is:', d)
    print(str(d))
  with col2:
    t = st.time_input('and Time', datetime.time(8, 45))
    st.write('Alarm is set for', t)
    print(str(t))

  TIME_UNITS = ('YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND')
  # time unit and count
  col3, col4 = st.beta_columns(2)
  with col3:
    obj_type = st.selectbox('Time Unit: ', TIME_UNITS)
    st.write('You selected:', obj_type)
  with col4:
    cnt = st.number_input('Number of data points',
                          max_value=1000, min_value=0, step=1)
    st.write('You selected:', cnt)
    print(str(t))


def show_plot(metrics):

  fig = go.Figure()
  for metric in metrics:
    fig.add_trace(go.Bar(
        x=metric['x'],
        y=metric['y'],
        name=metric['name'],
        marker_color=metric['color']
    ))

  # Here we modify the tickangle of the xaxis, resulting in rotated labels.
  fig.update_layout(barmode='group', xaxis_tickangle=-45)
  st.plotly_chart(fig, use_container_width=True)


def build_metrics_from_response(res):
  metrics = []
  y = res[0]['@@stats']
  x = res[1]['@@dates']
  print(x)
  print(y)
  metrics.append({'x': x, 'y': y, 'name': 'asd', 'color': '#ff0000'})
  return metrics


# # print(res)
# print(res[0]['@@stats'])
# print(res[1]['@@dates'])
build_UI()

res = run_interpretted_gsql(getGSQL())
show_plot(build_metrics_from_response(res))