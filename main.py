import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import pandas as pd

import os
from bs4 import BeautifulSoup

import codecs


def get_time_elapsed_stall_mapping(filename):
    x = []
    y = []
    myInt = 1000  # Convert from ms to sec
    previous_time = 0
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            row_element = line.strip().split()
            # ['LOG', 0.423....]
            if row_element[0] == 'START':
                continue
            if row_element[0] == 'QUAL':
                continue
            if row_element[0] == 'STALL':
                y.append(float(row_element[1]))
                x.append(previous_time)
                continue
            log_details = row_element[1]
            # log_details = 0.428,0:60,480x270,2049,0
            log_elements = log_details.split(",")
            x.append(float(log_elements[0]))
            y.append(0)
            y_dev = np.divide(y, myInt)  # convert STALLS from ms to sec
            y_sec = [round(x, 1) for x in y_dev]
            previous_time = float(log_elements[0])

    if not os.path.exists('Stall_Results'):
        os.makedirs('Stall_Results')

    df = pd.DataFrame({'x': x, 'y': y_sec})
    print(df.head())
    num_col = df._get_numeric_data().columns[1]

    describe_num_df = df.mask(df == 0).describe()

    describe_num_df.reset_index(inplace=True)
    describe_num_df = describe_num_df[describe_num_df['index'] != 'count']
    for i in num_col:
        if i in ['index']:
            continue
        fig1 = px.line(describe_num_df, x="index", y=i, text=i, labels={
            "x": "Statistics",
            "y": "Stalls(sec)",
        }, title="Stalls Statistics")
        fig1.update_traces(textposition="bottom right")
        # fig1.show()
    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_Statistics_.html'.format(filename))
    fig1.write_html(path_Name)

    text_in = []
    for index in range(len(x)):
        text_in.append(y_sec[index])

    fig2 = px.line(df, x='x', y='y', text=text_in, labels={
        "x": "Time (sec)",
        "y": "Stalls(sec)",
    }, title="Stalls (sec) / Time(sec)", render_mode="markers+text")
    fig2.update_traces(textposition="top right")
    # fig2.show()

    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_resultStallsResults_.html'.format(filename))
    fig2.write_html(path_Name)





def get_time_elapsed_qual_mapping(filename):
    x = []
    y = []
    previous_time = 0
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            row_element = line.strip().split()
            # ['LOG', 0.423....]
            if row_element[0] == 'START':
                continue
            if row_element[0] == 'STALL':
                continue
            if row_element[0] == 'QUAL':
                y.append(str(row_element[4]))
                x.append(float(row_element[2]))
                continue
            log_details = row_element[1]
            # log_details = 0.428,0:60,480x270,2049,0
            log_elements = log_details.split(",")
            x.append(float(log_elements[0]))
            y.append(str(log_elements[2]))

    # Plot
    df = pd.DataFrame({'x': x, 'y': y})
    # num_col = df._get_numeric_data().columns[1]
    fig = px.line(df, x, y, labels={
        "x": "Time",
        "y": "Quality",
    }, title="Quality Levels vs Time")
    # fig.show()

    if not os.path.exists('Qual_Results'):
        os.makedirs('Qual_Results')
    path_Name = os.path.join(os.getcwd(), 'Qual_Results', '{}_resultQual_Time_.html'.format(filename))
    fig.write_html(path_Name)
    print(x)
    print(len(x))
    print(y)


def analyze_size_of_buffer(log_file):
    # df = pd.read_csv(log_file, sep="\n", names=['Params'])

    path_name = os.path.join(os.getcwd(),log_file)

    df = pd.read_csv(path_name, sep="\\n", names=['Params'])

    log_df = df["Params"].str.extract(r"LOG  (?P<realtime_elapsed>\d+\.?\d*),(?P<current_time>\d+\.?\d*):(?P<current_fps>\d*),(?P<current_horizontal_resolution>\d+)x(?P<cur_vert_res>\d*),(?P<current_bitrate>\d+),(?P<current_size_of_buffer>\d+\.?\d*)")
    # log_df["current_size_of_buffer"]=pd.to_numeric(log_df["current_size_of_buffer"])
    log_df = log_df.apply(pd.to_numeric)
    # log_df["realtime_elapsed"]=pd.to_numeric(log_df["realtime_elapsed"])
    log_df = log_df.dropna()
    summary_csv = log_df.describe().to_csv()

    fig = px.line(log_df, x="realtime_elapsed", y="current_size_of_buffer", title='realtime_elapsed vs current_size_of_buffer').update_layout(
        xaxis_title="realtime_elapsed(Sec)", yaxis_title="current_size_of_buffer(Sec)",xaxis_tickformat=',d'
    )
    if not os.path.exists('Size_of_Buffer_Results'):
        os.makedirs('Size_of_Buffer_Results')
    path_Name = os.path.join(os.getcwd(), 'Size_of_Buffer_Results', '{}_Size_of_Buffer_Results_.html'.format(log_file))
    fig.write_html(path_Name)
    # return summary_csv,img

if __name__ == "__main__":
    logCounter = len(glob.glob1(os.getcwd(), "*.log"))
    print(str(logCounter) + " log files found")

    os.chdir(os.getcwd())
    for fileName in glob.glob("*.log"):
        print(fileName)
        get_time_elapsed_stall_mapping(fileName)
        get_time_elapsed_qual_mapping(fileName)
        analyze_size_of_buffer(fileName)

    output_doc = BeautifulSoup()
    output_doc.append(output_doc.new_tag("html"))
    output_doc.html.append(output_doc.new_tag("body"))
    path_html = (os.path.join(os.getcwd(), 'Stall_Results'))
    for file in os.listdir(path_html):
        if not file.lower().endswith('.html'):
            continue
        path_html2 = (os.path.join(path_html,file))
        with open(path_html2, 'r') as html_file:
            output_doc.body.extend(BeautifulSoup(html_file.read(), "html.parser").body)

    path3 = (os.path.join(path_html,"output1.html"))
    with open(path3, "w+") as file:
        file.write(str(output_doc.prettify()))