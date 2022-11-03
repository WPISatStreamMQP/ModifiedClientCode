import sys
import re
import plotly.express as px
import matplotlib.pyplot as plt

stall_log_pat = r"STALL  ([\d]+) ms$"

def main():
    if len(sys.argv) < 2:
        return

    fileName = sys.argv[1]
    logFile = open(fileName, "r")

    stallsMs = []
    while True:
        line = logFile.readline()

        if not line:
            break
        
        stallMatch = re.search(stall_log_pat, line)
        if not stallMatch:
            continue
        stallLengthMs_str = stallMatch.group(1)
        stallLengthMs = int(stallLengthMs_str)
        stallsMs.append(stallLengthMs)
    
    #print(stallsMs)
    plotTitle = "Stall lengths of " + fileName
    fig = px.box(y = stallsMs, title = plotTitle)
    fig.update_layout(yaxis_title = "Stall Length (ms)")
    fig.update_yaxes(range = [0, 22000], dtick = 2000)

    #fig.write_image(fileName + ".png", width = 500, height = 500)
    fig.show()

if __name__ == "__main__":
    main()