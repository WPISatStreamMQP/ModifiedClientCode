import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import re
import math
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

    # delete all 0 values from the dataframe
    df = df[df.y != 0]
    # whisker plot
    fig3 = px.box(df, y="y", labels={   "y": "Stalls(sec)",}, title="Stalls (sec) / Time(sec) for: {}".format(filename))
    path_Name = os.path.join(os.getcwd(), 'Stall_Results', '{}_resultStallsResults_whisker_.html'.format(filename))
    fig3.write_html(path_Name)


    return pd.DataFrame({'x': x, 'y': y_sec})


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
    summary_fig.update_layout(title="Table Summary Statistics for: {}".format(filename))
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
                     categoryarray=['480x270', '640x360', '960x540','1280x720','1920x1080','3840x2160'])
    path_Name = os.path.join(os.getcwd(), 'Qual_Results', '{}_resultQual_Time_.html'.format(filename))
    fig.write_html(path_Name)

    return pd.DataFrame({'x': x, 'y': y})



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

    return pd.DataFrame({'x': log_df["realtime_elapsed"], 'y': log_df["current_size_of_buffer"]})

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

    return pd.DataFrame({'x': df1['tSent(ms) '], 'y': df1['rtt(ms)']})

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
                "index":"Time(s)",
                "frame.len":"bitrate(Mbit/s)"
            }
               ,title='Throughput')
    fig2.update_layout(showlegend=False)
    fig2.update_layout(title_text='Throughput for: {}'.format(filtered_packets))

    path_Name = os.path.join(os.getcwd(), 'Throughput_Results', '{}_Throughput_Results_.html'.format(filtered_packets))
    fig2.write_html(path_Name)

    return pd.DataFrame({'x': df_new['index'], 'y': df_new['frame.len']})

if __name__ == "__main__":
    # get all the files in the current directory and analyze them
    empty_files = []
    all_stalls_df = pd.DataFrame(columns=['x', 'y'])
    all_qual_map = pd.DataFrame(columns=['x', 'y'])
    all_buffer_sizes = pd.DataFrame(columns=['x', 'y'])
    all_throughput = pd.DataFrame(columns=['x', 'y'])
    all_UDPing = pd.DataFrame(columns=['x', 'y'])
    print("All the files will be analyzed and the cumulative results will be saved as csv files in the All_Results folder")
    print("For the combined results you can rename the files eg (bola,throughput, segment size, etc)")
    print("Do you want to rename the files for the combined results? (y/n)")
    rename = input()
    if rename == "y" or rename == "Y":
        print("Enter the name you want to add to the file name: eg (All_Throughput_Results_[name].csv)")
        name = input()
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
                all_qual_map = all_qual_map.append(get_time_elapsed_qual_mapping(file_path), ignore_index=True)
                all_stalls_df = all_stalls_df.append(get_time_elapsed_stall_mapping(file_path), ignore_index=True)
                all_buffer_sizes = all_buffer_sizes.append(analyze_size_of_buffer(file_path), ignore_index=True)
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
                all_UDPing = all_UDPing.append(analyze_UDPing_logs(file_path), ignore_index=True)
                print("Done analyzing UDPing " + file)
            if file.endswith("packets_client.csv") or file.endswith("packets_server.csv"):
                # skip empty files
                if os.stat(os.path.join(root, file)).st_size == 0:
                    print("Skipping empty file: " + file)
                    empty_files.append(file)
                    continue
                file_path = os.path.join(root, file)
                print("Analyzing  " + file)
                all_throughput = all_throughput.append(analyze_packets(file_path), ignore_index=True)
                print("Done analyzing " + file)


# create a new directory to store all the results
current_dir = os.getcwd()
new_dir = os.path.join(current_dir, "All_Results")
if not os.path.exists(new_dir):
    os.makedirs(new_dir)
print("--" * 50)

# delete all the files in the directory if they exist and create new ones with the same name and write the dataframes to them
for file in os.listdir(new_dir):
    if file.startswith("All") and file.endswith(".csv"):
        print("File", file, "already exists, deleting it...")
        os.remove(os.path.join(new_dir, file))


all_stalls_df = all_stalls_df.rename(columns={"x": "Time(sec)", "y": "Stall_Duration(sec)"})
all_stalls_df.to_csv(os.path.join(new_dir, 'All_Stalls_Results.csv'), index=False)
all_qual_map = all_qual_map.rename(columns={"x": "Time(sec)", "y": "Quality"})
all_qual_map.to_csv(os.path.join(new_dir, 'All_Qual_Mapping_Results.csv'), index=False)
all_buffer_sizes = all_buffer_sizes.rename(columns={"x": "Time(sec)", "y": "Buffer_Size(sec)"})
all_buffer_sizes.to_csv(os.path.join(new_dir, 'All_Buffer_Sizes_Results.csv'), index=False)
all_throughput = all_throughput.rename(columns={"x": "Time(sec)", "y": "bitrate(Mbit/s)"})
all_throughput.to_csv(os.path.join(new_dir, 'All_Throughput_Results.csv'), index=False)
all_UDPing = all_UDPing.rename(columns={"x": "tSent(ms)", "y": "rtt(ms)"})
all_UDPing.to_csv(os.path.join(new_dir, 'All_UDPing_Results.csv'), index=False)


if rename == "y" or rename == "Y":
    os.rename(os.path.join(new_dir, 'All_Stalls_Results.csv'),
                os.path.join(new_dir, 'All_Stalls_Results_' + name + '.csv'))
    os.rename(os.path.join(new_dir, 'All_Qual_Mapping_Results.csv'),
                os.path.join(new_dir, 'All_Qual_Mapping_Results_' + name + '.csv'))
    os.rename(os.path.join(new_dir, 'All_Buffer_Sizes_Results.csv'),
                os.path.join(new_dir, 'All_Buffer_Sizes_Results_' + name + '.csv'))
    os.rename(os.path.join(new_dir, 'All_Throughput_Results.csv'),
                os.path.join(new_dir, 'All_Throughput_Results_' + name + '.csv'))
    os.rename(os.path.join(new_dir, 'All_UDPing_Results.csv'),
                os.path.join(new_dir, 'All_UDPing_Results_' + name + '.csv'))
else:
    print("Files not renamed")


print("File for all the results created successfully at " + new_dir)
print("--" * 40 )
if len(empty_files) > 0:
    print("Skipped " + str(len(empty_files)) + " files")
    print("The following files were skipped because they were empty:" + str(empty_files))
else:
    print("No files were skipped")


