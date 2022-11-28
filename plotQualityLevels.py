import sys
import re
import plotly.express as px
import matplotlib.pyplot as plt

log_pat = r"LOG  (.+)$"
quality_levels = ["480x270", "640x360", "960x540", "1280x720", "1920x1080", "3840x2160"]

def main():
    if len(sys.argv) < 2:
        return

    fileName = sys.argv[1]
    logFile = open(fileName, "r")

    qualityLevelCts = dict.fromkeys(quality_levels, 0)
    while True:
        line = logFile.readline()

        if not line:
            break

        logMatch = re.search(log_pat, line)
        if not logMatch:
            continue
        
        logData = logMatch.group(1)
        logElements = logData.split(",")
        resolution = logElements[2]
        qualityLevelCts[resolution] = qualityLevelCts[resolution] + 1
    
    #print(qualityLevelCts)
    plotTitle = "Quality levels of " + fileName + " - 0.5 sec log interval"
    print(qualityLevelCts.keys())
    print(qualityLevelCts.values())
    fig = px.histogram(x = qualityLevelCts.keys(), y = qualityLevelCts.values(), title = plotTitle)
    fig.update_layout(xaxis_title = "Quality Level (Resolution)", yaxis_title = "Number of Occurrences")
    #fig.show()

if __name__ == "__main__":
    main()