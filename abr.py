import pandas as pd
import os
import csv
import numpy as np
import plotly.graph_objects as go
import glob

def produce_graph(path, df):
    # function to find the closest value in a series to a given value
    def find_closest_value(series, value):
        return series.iloc[(series - value).abs().argsort()[0]]

    def find_missing_and_out_of_order_values(data):
        missing_values = []
        out_of_order_values = []

        for i, value in enumerate(data):
            # Check if the current value is missing
            if i not in data:
                missing_values.append(i)

            # Check if the current value is out of order
            if i > 0 and value < data[i-1]:
                out_of_order_values.append(data[i-1])
                out_of_order_values.append(value)

        return missing_values, out_of_order_values

    # Read the csv file and skip the first two rows
    # df = pd.read_csv('.\\5s\\Run0\\UDPing_log.csv', skiprows=[0, 1])


    # Loop through each row in the dataframe
    break_index = None
    for index, row in df.iterrows():
        # Check if the row contains "Ping statistics" and nothing else
        if "Ping statistics" in row[0]:
            # If it does, break out of the loop
            break_index = index
            break

    # Slice the dataframe to include only the rows up to the "Ping statistics" row
    df = df.iloc[:break_index]
    df = df.rename(columns={'tSent(ms) ': 'tSent(ms)'})
    df['tSent(s)'] = df['tSent(ms)'] / 1000
    df['tSent(min)'] = df['tSent(s)'] / 60
    # create normal_seq column
    df['normal_seq'] = df['seq'].diff().apply(lambda x: 1 if pd.isna(x)
                                            or x == 0 else 1 if x == 1 else 0)

    # Create the missing_seq and out_of_order_seq columns
    seq_in_list = df['seq'].tolist()
    missing_values, out_of_order_values = find_missing_and_out_of_order_values(
        seq_in_list)

    df['out_of_order_seq'] = df['seq'].apply(
        lambda x: 0 if x in out_of_order_values else 1)

    # create a new column 'missing_seq'
    df['missing_seq'] = np.nan

    # loop over the missing values and find the closest value in the 'seq' column
    for value in missing_values:
        closest_value = find_closest_value(df['seq'], value)
        # set the 'missing_seq' value to 0 for the closest value
        df.loc[df['seq'] == closest_value, 'missing_seq'] = 0

    # fill any remaining missing values in the 'missing_seq' column with 1
    df['missing_seq'].fillna(1, inplace=True)


    def set_std_plot_params(fig):
        fig.update_layout(font=dict(size=24))
        # Remove the background coloring.
        fig.update_layout({"plot_bgcolor": "rgba(0,0,0,0)",
                        "paper_bgcolor": "rgba(0,0,0,0)"})
        # Make the gridlines visible on the transparent background.
        fig.update_xaxes(showgrid=True, gridwidth=1,
                        gridcolor="rgba(169,169,169,0.5)")
        fig.update_yaxes(showgrid=True, gridwidth=1,
                        gridcolor="rgba(169,169,169,0.5)", tickvals=[0, 1])


    # Create the scatter plot
    fig = go.Figure()

    # Add scatter traces for each column
    for column in ['out_of_order_seq', 'missing_seq']:
        fig.add_trace(go.Scatter(
            x=df['tSent(min)'],
            y=df[column],
            mode='markers+lines',
            name="Out of Order Sequences" if column == 'out_of_order_seq' else "Missing Sequences",
            line=dict(color='red') if column == 'out_of_order_seq' else dict(
                color='blue'),
            line_shape='spline',
            line_smoothing=0.7,
            line_width=1.5,
            marker=dict(size=7)
        ))

    # Update layout with axis labels
    fig.update_layout(
        xaxis_title='Time(min)',
        yaxis_title='In Order(1) / Out of Order(0)',
        font=dict(size=18)
    )

    set_std_plot_params(fig)

    # Get the current file path
    #filepath = os.path.splitext(__file__)[0]

    # Save the plot as a PNG file using the file path as the name
    #fig.write_image(filepath + '.png')
    #print(filepath)
    fig.write_image(path + ".svg", width = 1200, height = 500)

# Search for files named "UDPing_log.csv" in "Bola", "Dynamic", and "ThruAll" folders and their subfolders

for setting in settings:
    file_paths = glob.glob('./{}/**/UDPing_log.csv'.format(setting), recursive=True)
    # Read all files found into a single DataFrame
    for path in file_paths:
        df = pd.read_csv(path, skiprows=[0, 1])
        produce_graph(path, df)