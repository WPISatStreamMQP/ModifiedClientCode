import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import re
import math
import os

reso_to_qual_level = {
    "480x270": 1,
    "640x360": 2,
    "960x540": 3,
    "1280x720": 4,
    "1920x1080": 5,
    "3840x2160": 6,
}

def set_std_plot_params(fig):
    fig.update_layout(font = dict(size = 24))
    # Remove the background coloring.
    fig.update_layout({"plot_bgcolor": "rgba(0,0,0,0)",
                       "paper_bgcolor": "rgba(0,0,0,0)"})
    # Make the gridlines visible on the transparent background.
    fig.update_xaxes(showgrid = True, gridwidth = 1, gridcolor = "rgba(169,169,169,0.5)")
    fig.update_yaxes(showgrid = True, gridwidth = 1, gridcolor = "rgba(169,169,169,0.5)")

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
    
    if len(x) == 0:
        print("No data in JS log file. Not outputting logs.")
        return

    df = pd.DataFrame({'x': x, 'y': y_sec})
    num_col = df._get_numeric_data().columns[1]

    describe_num_df = df.mask(df == 0).describe()

    describe_num_df.reset_index(inplace=True)
    describe_num_df = describe_num_df[describe_num_df['index'] != 'count']
    for i in num_col:
        if i in ['index']:
            continue
        # title="Stalls Statistics"
        fig1 = px.bar(describe_num_df, x="index", y=i, text=i, labels={
            "x": "Statistics",
            "y": "Stalls(sec)",
        })
        #fig1.show()
    set_std_plot_params(fig1)
    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_Statistics_.html'.format(filename))
    fig1.write_html(path_Name)

    text_in = []
    for index in range(len(x)):
        text_in.append(y_sec[index])

    # title="Stalls (sec) / Time(sec) for: {}".format(filename)
    fig2 = px.line(df, x='x', y='y',labels={
        "x": "Time (sec)",
        "y": "Stalls(sec)",
    })
    fig2.update_traces(textposition="top right")
    set_std_plot_params(fig2)

    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_resultStallsResults_.html'.format(filename))
    fig2.write_html(path_Name)


def calculate_table(filename):
    # Getting input
    path_name = os.path.join(os.getcwd(), filename)
    df = pd.read_csv(path_name, sep="\\n", names=['Params'])

    # Read using regular expression
    log_df = df["Params"].str.extract(
        r"LOG  (?P<realtime_elapsed>\d+\.?\d*),(?P<current_time>\d+\.?\d*):(?P<fps>\d*),(?P<horizontal_resolution>\d+)x(?P<vert_res>\d*),(?P<bitrate>\d+),(?P<current_size_of_buffer>\d+\.?\d*)")
    log_df = log_df.apply(pd.to_numeric)
    log_df = log_df.dropna()
    summary_df = log_df.describe()

    # Generate figure
    summary_fig = go.Figure(data=[go.Table(
        header=dict(values=list(summary_df.reset_index().columns),
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=summary_df.reset_index().T,
                   fill_color='lavender',
                   align='left'))
    ])
    path_Name = os.path.join(os.getcwd(), 'Table_Results', '{}_Table_.html'.format(filename))
    summary_fig.write_html(path_Name)



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
                y.append(reso_to_qual_level[str(row_element[4])])
                x.append(float(row_element[2]))
                continue
            log_details = row_element[1]
            log_elements = log_details.split(",")
            x.append(float(log_elements[0]))
            y.append(reso_to_qual_level[str(log_elements[2])])

    if len(x) == 0:
        print("No data in JS log file. Not outputting logs.")
        return

    df = pd.DataFrame({'time_sec': x, 'quality_level': y})
    df["time_min"] = np.divide(df["time_sec"], 60)
    # title="Resolution vs Time for: {}".format(filename)
    """fig = px.line(df, x, y, labels={
        "x": "Time",
        "y": "Quality Level",
    })"""
    fig = px.line(x = df["time_min"], y = df["quality_level"], labels = {
        "x": "Time (min)",
        "y": "Quality Level"
    })
    #fig.update_yaxes(categoryorder='array',
    #                 categoryarray=['480x270', '640x360', '960x540','1280x720','1920x1080'])
    # Thicken the data lines.
    fig.update_traces(line = dict(width = 5))
    fig.update_yaxes(categoryorder = "array", categoryarray = list(range(1, 7))) # Range from 1 to 6 inclusive.
    set_std_plot_params(fig)
    path_Name = os.path.join(os.getcwd(), 'Qual_Results', '{}_resultQual_Time_.html'.format(filename))
    fig.write_html(path_Name)

    # plot the graph
    # fig.show()



def analyze_size_of_buffer(log_file):
    path_name = os.path.join(os.getcwd(),log_file)

    df = pd.read_csv(path_name, sep="\\n", names=['Params'])

    log_df = df["Params"].str.extract(r"LOG  (?P<realtime_elapsed>\d+\.?\d*),(?P<current_time>\d+\.?\d*):(?P<current_fps>\d*),(?P<current_horizontal_resolution>\d+)x(?P<cur_vert_res>\d*),(?P<current_bitrate>\d+),(?P<current_size_of_buffer>\d+\.?\d*)")
    # log_df["current_size_of_buffer"]=pd.to_numeric(log_df["current_size_of_buffer"])
    log_df = log_df.apply(pd.to_numeric)
    # log_df["realtime_elapsed"]=pd.to_numeric(log_df["realtime_elapsed"])
    log_df = log_df.dropna()
    log_df["realtime_elapsed_minutes"] = log_df["realtime_elapsed"] / 60
    fig = px.line(log_df, x="realtime_elapsed_minutes", y="current_size_of_buffer").update_layout(
        xaxis_title="realtime_elapsed(Min)", yaxis_title="current_size_of_buffer(Min)",xaxis_tickformat=',d'
    )
    set_std_plot_params(fig)
    fig.update_xaxes(showgrid = True, gridwidth = 1, gridcolor = "rgba(169,169,169,0.5)",
                     dtick = 1)
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
    # title='UDPing RTT vs Time for: {}'.format(log_file)
    fig = px.scatter(df1, x='tSent(ms) ', y='rtt(ms)')
    set_std_plot_params(fig)
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
    # title="RTT(ms) Statistics for: {}".format(log_file)
    fig = px.bar(df_summary)
    set_std_plot_params(fig)
    fig.update_xaxes(title_text="Statistics")
    fig.update_yaxes(title_text="RTT(sec)")
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Summary_.html'.format(log_file))
    fig.write_html(path_Name)

    # whisker plot for RTT values in UDPing logs
    # title="RTT(sec) Statistics from UDPing for: {}".format(log_file)
    fig = px.box(data_frame=df1, x="rtt(ms)", orientation="h")
    fig.update_xaxes(title_text="RTT(sec)")
    set_std_plot_params(fig)
    title='UDPing RTT vs Time for: {}'.format(log_file)
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Whisker_.html'.format(log_file))
    fig.write_html(path_Name)

    # save df2 as csv
    path_Name = os.path.join(os.getcwd(), 'UDPing_Results', '{}_UDPing_Results_Summary.csv'.format(log_file))
    df2.to_csv(path_Name, index=False)

# function for calculating the throughput
def analyze_packets(filtered_packets):

    # read only the first 2 columns
    df_new = pd.read_csv(filtered_packets, usecols=[0, 1])

    """# Preprocessing"""


    def grouping_attr(index):
        return math.floor(df_new['_ws.col.Time'].loc[index])

    df_new = df_new.groupby(grouping_attr)['frame.len'].sum().reset_index()
    df_new['frame.len'] = df_new['frame.len'].multiply(8e-6)  # multiply to get Mbit/s
    

    fig2 = px.line(df_new,x="index",y="frame.len",
            labels={
                "index":"Time (sec)",
                "frame.len":"Bitrate (Mbit/sec)"
            })
    fig2.update_layout(font = dict(size = 24))
    # Remove the background coloring.
    fig2.update_layout({"plot_bgcolor": "rgba(0,0,0,0)",
                       "paper_bgcolor": "rgba(0,0,0,0)"})
    # Make the gridlines visible on the transparent background.
    fig2.update_xaxes(showgrid = True, gridwidth = 1, gridcolor = "rgba(169,169,169,0.5)",
                      linewidth = 2, linecolor = 'black')
    fig2.update_yaxes(showgrid = True, gridwidth = 1, gridcolor = "rgba(169,169,169,0.5)",
                      rangemode = "tozero")
    #fig2.add_hline(y = 0, line_color = "rgba(0,0,0,0)")
    #fig2.update_layout(title_text='Throughput for: {}'.format(filtered_packets))

    path_Name = os.path.join(os.getcwd(), 'Throughput_Results', '{}_Throughput_Results_.html'.format(filtered_packets))
    fig2.write_html(path_Name)



if __name__ == "__main__":
    # get all the files in the current directory and analyze them
    empty_files = []
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.startswith("Tester") and file.endswith(".log"):
                # skip empty files
                if os.stat(os.path.join(root, file)).st_size == 0:
                    print("Skipping empty file: " + file)
                    empty_files.append(file)
                    continue
                file_path = os.path.join(root, file)
                print("Analyzing " + file)
                get_time_elapsed_qual_mapping(file_path)
                get_time_elapsed_stall_mapping(file_path)
                analyze_size_of_buffer(file_path)
                print("Done analyzing " + file)
                print("--" * 20)
                print("Calculating Table " + file)
                calculate_table(file_path)
                print("Done calculating Table " + file)
            # get all the files named "UDPing_log.csv"
            if file.endswith("UDPing_log.csv"):
                # skip empty files
                if os.stat(os.path.join(root, file)).st_size == 0:
                    print("Skipping empty file: " + file)
                    empty_files.append(file)
                    continue
                file_path = os.path.join(root, file)
                print("Analyzing UDPing " + file)
                analyze_UDPing_logs(file_path)
                print("Done analyzing UDPing " + file)
            if file.endswith("packets_client.csv") or file.endswith("packets_server.csv"):
                # skip empty files
                if os.stat(os.path.join(root, file)).st_size == 0:
                    print("Skipping empty file: " + file)
                    empty_files.append(file)
                    continue
                file_path = os.path.join(root, file)
                print("Analyzing  " + file)
                analyze_packets(file_path)
                print("Done analyzing " + file)


print("--" * 40 )
if len(empty_files) > 0:
    print("Skipped " + str(len(empty_files)) + " files")
    print("The following files were skipped because they were empty:" + str(empty_files))
else:
    print("No files were skipped")

