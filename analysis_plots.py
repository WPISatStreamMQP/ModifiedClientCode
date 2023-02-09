import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import re

import os




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
                if row_element[1] == 'started':
                    continue
                y.append(float(row_element[1]))
                x.append(previous_time)
                continue
            log_details = row_element[1] #
            log_elements = log_details.split(",")
            x.append(float(log_elements[0]))
            y.append(0)
            y_dev = np.divide(y, myInt)  # convert STALLS from ms to sec
            y_sec = [round(x, 1) for x in y_dev]
            previous_time = float(log_elements[0])

    df = pd.DataFrame({'x': x, 'y': y_sec})
    num_col = df._get_numeric_data().columns[1]

    describe_num_df = df.mask(df == 0).describe()

    describe_num_df.reset_index(inplace=True)
    describe_num_df = describe_num_df[describe_num_df['index'] != 'count']
    for i in num_col:
        if i in ['index']:
            continue
        fig1 = px.bar(describe_num_df, x="index", y=i, text=i, labels={
            "x": "Statistics",
            "y": "Stalls(sec)",
        }, title="Stalls Statistics")
        #fig1.show()
    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_Statistics_.html'.format(filename))
    fig1.write_html(path_Name)

    text_in = []
    for index in range(len(x)):
        text_in.append(y_sec[index])

    fig2 = px.line(df, x='x', y='y',labels={
        "x": "Time (sec)",
        "y": "Stalls(sec)",
    }, title="Stalls (sec) / Time(sec) for: {}".format(filename))
    fig2.update_traces(textposition="top right")

    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_resultStallsResults_.html'.format(filename))
    fig2.write_html(path_Name)


def get_time_elapsed_qual_mapping(filename):
    x = []
    y = []
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            row_element = line.strip().split()
            if row_element[0] == 'START':
                continue
            if row_element[0] == 'STALL':
                continue
            if row_element[0] == 'QUAL':
                y.append(str(row_element[4]))
                x.append(float(row_element[2]))
                continue
            log_details = row_element[1]
            log_elements = log_details.split(",")
            x.append(float(log_elements[0]))
            y.append(str(log_elements[2]))

    df = pd.DataFrame({'x': x, 'y': y})
    fig = px.line(df, x, y, labels={
        "x": "Time",
        "y": "Resolution",
    }, title="Resolution vs Time for: {}".format(filename))
    fig.update_yaxes(categoryorder='array',
                     categoryarray=['480x270', '640x360', '960x540','1280x720','1920x1080'])
    path_Name = os.path.join(os.getcwd(), 'Qual_Results', '{}_resultQual_Time_.html'.format(filename))
    fig.write_html(path_Name)


def analyze_size_of_buffer(log_file):
    path_name = os.path.join(os.getcwd(),log_file)

    df = pd.read_csv(path_name, sep="\\n", names=['Params'])

    log_df = df["Params"].str.extract(r"LOG  (?P<realtime_elapsed>\d+\.?\d*),(?P<current_time>\d+\.?\d*):(?P<current_fps>\d*),(?P<current_horizontal_resolution>\d+)x(?P<cur_vert_res>\d*),(?P<current_bitrate>\d+),(?P<current_size_of_buffer>\d+\.?\d*)")
    # log_df["current_size_of_buffer"]=pd.to_numeric(log_df["current_size_of_buffer"])
    log_df = log_df.apply(pd.to_numeric)
    # log_df["realtime_elapsed"]=pd.to_numeric(log_df["realtime_elapsed"])
    log_df = log_df.dropna()
    fig = px.line(log_df, x="realtime_elapsed", y="current_size_of_buffer", title='realtime_elapsed vs current_size_of_buffer').update_layout(
        xaxis_title="realtime_elapsed(Sec)", yaxis_title="current_size_of_buffer(Sec)",xaxis_tickformat=',d'
    )
    path_Name = os.path.join(os.getcwd(), 'Size_of_Buffer_Results', '{}_Size_of_Buffer_Results_.html'.format(log_file))
    fig.write_html(path_Name)

#  function for analyzing UDPing logs
def analyze_UDPing_logs(log_file):
    df = pd.read_csv(log_file, skiprows=1)
    server_list = df['server'].tolist()
    ping_statistics_row = server_list.index('Ping statistics ')
    # split the dataframe into two dataframes
    df1 = df.iloc[:ping_statistics_row]
    df2 = df.iloc[ping_statistics_row:]
    df1['tSent(ms) '] = df1['tSent(ms) '].apply(lambda x: x / 1000)
    # Plot the RTT vs Time
    fig = px.scatter(df1, x='tSent(ms) ', y='rtt(ms)', title='UDPing RTT vs Time for: {}'.format(log_file))
    fig.update_xaxes(title_text="Time sent (sec)")
    fig.update_yaxes(title_text="RTT(sec)")
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_.html'.format(log_file))
    fig.write_html(path_Name)
    # Plot the summary statistics
    df_summary = df1.describe()
    df_summary.drop(['bytes'], axis=1, inplace=True)
    df_summary.drop(['seq'], axis=1, inplace=True)
    df_summary.drop(['tSent(ms) '], axis=1, inplace=True)
    df_summary.drop(['count'], axis=0, inplace=True)
    fig = px.bar(df_summary, title="RTT(ms) Statistics for: {}".format(log_file))
    fig.update_xaxes(title_text="Statistics")
    fig.update_yaxes(title_text="RTT(sec)")
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Summary_.html'.format(log_file))
    fig.write_html(path_Name)
    # whisker plot for RTT values in UDPing logs
    fig = px.box(data_frame=df1, x="rtt(ms)", orientation="h",
                 title="RTT(sec) Statistics from UDPing for: {}".format(log_file))
    fig.update_xaxes(title_text="RTT(sec)")
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Whisker_.html'.format(log_file))
    fig.write_html(path_Name)

    # save df2 as csv
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Summary.csv'.format(log_file))
    df2.to_csv(path_Name, index=False)



if __name__ == "__main__":
    # get all the files in the current directory and analyze them
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.endswith(".log") and file != "geckodriver.log":
                file_path = os.path.join(root, file)
                print("Analyzing " + file)
                get_time_elapsed_qual_mapping(file_path)
                get_time_elapsed_stall_mapping(file_path)
                analyze_size_of_buffer(file_path)
                print("Done analyzing " + file)
            # get all the files named "UDPing_log.csv"
            if file.endswith("UDPing_log.csv"):
                file_path = os.path.join(root, file)
                print("Analyzing UDPing " + file)
                analyze_UDPing_logs(file_path)
                print("Done analyzing UDPing " + file)


    print("Done analyzing all files")




