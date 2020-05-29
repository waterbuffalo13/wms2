from wms2B.app import app
from dash.dependencies import Input, Output, State
import pandas as pd
import dash
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.graph_objects as go
from pytimeparse.timeparse import timeparse


colors = dict(Meal = '#00ba03',
              Work = '#1c7813',
              Recreation = '#193c12',
              Exercise = '#000000',
              Rest = 'rgb(107, 127, 135)')

@app.callback([Output("schedule-table", "data"), Output('task_start', 'value'), Output('task_stop', 'value')],
              [Input('submit-schedule', 'n_clicks')],
              [State('task_content', 'value'), State('task_start', 'value'),
               State('task_stop', 'value'), State('task_type','value')])
def update_gantt_datatable(n_clicks, task_contents, start_task, stop_task, subtype_task):
    base = pd.read_csv("data/gantt.csv")
    # hours_expended = (datetime.strptime(stop_task, "%d/%m/%Y %H:%M") - datetime.strptime(start_task, "%d/%m/%Y %H:%M"))
    hours_expended_str = str(datetime.strptime(stop_task, "%d/%m/%Y %H:%M") - datetime.strptime(start_task, "%d/%m/%Y %H:%M"))
    if n_clicks is not None and n_clicks > 0:
        updated = add_to_csv(base, start_task, stop_task, task_contents, "---", subtype_task, hours_expended_str)
        start_task = stop_task
        stop_task = (datetime.strptime(start_task, "%d/%m/%Y %H:%M") + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M")
        # pie_figure = pie_layout(updated)
        return updated.to_dict('records'), start_task, stop_task
    else:
        dash.exceptions.PreventUpdate()
        # pie_figure = pie_layout(base)
        return base.to_dict('records'), start_task, stop_task



#dependent
def add_to_csv(base, start_task, stop_task, task_contents, task_nature, subtype_task, hours_expended_str):
    base = base.loc[:, ~base.columns.str.contains('^Unnamed')]
    created = datetime.now().strftime("%d/%m/%Y %H:%M:%S:%f")
    task_data = [[task_contents, created, start_task, stop_task, task_nature, subtype_task, hours_expended_str]]
    updated = pd.DataFrame(task_data, columns=['task_name', 'created_date', 'start_task', 'stop_task', "task_nature", 'task_subtype', 'hours_expended'])
    updated = pd.concat([base, updated])
    updated = updated[pd.notnull(updated["task_name"])]
    updated = updated.reset_index(drop=True)
    updated.to_csv("data/gantt.csv", index=False)
    return updated


# remove task
@app.callback([Output("gantt_chart", "figure"), Output('pie-chart', 'figure')],
              [Input('schedule-table', 'data_previous'), Input("submit-schedule", "n_clicks"),
               Input("schedule-table", "data")],
              [State('schedule-table', 'data')])
def update_graphs(old_table, n_clicks, data, new_table, ):
    gantt_df = pd.read_csv("data/gantt.csv")
    if old_table is None:
        ganttChart = convert_to_gantt_format(gantt_df)
        set_gantt_layout(ganttChart)
        pie_figure = pie_layout(gantt_df)
        return ganttChart, pie_figure
    else:
        for row in old_table:
            if row not in new_table:
                final_df = remove_from_csv(gantt_df, row)
                ganttChart = convert_to_gantt_format(final_df)
                set_gantt_layout(ganttChart)
                pie_figure = pie_layout(final_df)
                return ganttChart, pie_figure

def pie_layout(base):
    base["hours_expended_int"] = base["hours_expended"].apply(lambda x: timeparse(x) / (60 * 60))
    sleep_count = base.loc[base["task_name"] == "Sleep", "hours_expended_int"].sum()
    work_count = base.loc[base["task_name"] == "Work", "hours_expended_int"].sum()
    pie_figure = go.Figure(data=[
        go.Pie(labels=['Sleep', 'Work'], values=[sleep_count, work_count], hole=.4, textinfo='label+percent',
               automargin=False)])
    pie_figure.update_layout(autosize=True, margin=dict(l=10, r=10, b=10, t=10), paper_bgcolor="white",
                             showlegend=False, )
    pie_figure.update_yaxes(automargin=True)
    pie_figure.update_traces(hoverinfo='label+percent',
                             marker=dict(colors=['#171717', '#193c12', '#1c7813', '#990000']))
    return pie_figure
#dependent
def convert_to_gantt_format(final_df):
    df_gantt = final_df[["task_name", "start_task", "stop_task", "task_nature"]].copy()
    df_gantt.columns = ["Task", "Start", "Finish", "Resource"]
    df_gantt["Start"] = pd.to_datetime(df_gantt["Start"], format="%d/%m/%Y %H:%M")
    df_gantt["Finish"] = pd.to_datetime(df_gantt["Finish"], format="%d/%m/%Y %H:%M")
    add_or_remove = ff.create_gantt(df_gantt, group_tasks=True, showgrid_x=True, showgrid_y=True)

    return add_or_remove

#dependent
def remove_from_csv(current_df, row):
    x_df=pd.DataFrame.from_dict(row, orient="index", columns=["created_date"])
    final_df = pd.merge(current_df, x_df, on=['created_date', 'created_date'], how="outer", indicator=True, sort = True)
    final_df = final_df[final_df['_merge'] == 'left_only']
    final_df = final_df.drop(columns=["_merge"])
    final_df = final_df.reset_index(drop=True)
    final_df.to_csv("data/gantt.csv", index=False)

    return final_df

#dependent
def set_gantt_layout(ganttChart):
    ganttChart.update_layout(autosize=True, margin=dict(l=10, r=10, b=10, t=0), plot_bgcolor="lightgrey")
    ganttChart["layout"].pop("height", None)
    ganttChart["layout"].pop("width", None)
