from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyshark import LiveCapture, FileCapture
from threading import Thread
import os
import sys
import datetime
import socket
import pyshark
import asyncio
import csv
import time

ETH_HDR_LEN_B = 14
IP_HDR_LEN_MAX_B = 60
# The UDP max header length is 8 bytes, and the QUIC max header length is 20 bytes. So TCP at 60 bytes has the largest possible header.
TCP_HDR_LEN_MAX_B = 60 # 20 bytes usually, but 60 is the absolute max supported due to the size of the IHL field.
TOTAL_HDR_LEN_B = ETH_HDR_LEN_B + IP_HDR_LEN_MAX_B + TCP_HDR_LEN_MAX_B

STREAM_TIMEOUT_SEC = 900 # Timeout streams after 15 minutes and assume it encountered errors.
GENERIC_TIMEOUT_SEC = 3 # When accessing a regular element, timeout after just three seconds.

URL_INPUT_FIELD_ID = "urlInput"
URL_CONFIRM_BUTTON_ID = "urlConfirmButton"
STREAM_DONE_LABEL_ID = "streamDoneLabel"
SAVE_BUTTON_ID = "save_btn"

PACKET_PCAP_FILENAME = "packets.pcap"
PACKET_CSV_FILENAME = "packets.csv"

TSHARK_FILEOUTPUT_COMMAND = "tshark -r {pcapName} -t r -T fields -e _ws.col.Time -e frame.len -e ip.src -e ip.dst -E header=y -E separator=, > {csvName}"

class NonPromLiveCapture(LiveCapture):
    def get_parameters(self, packet_count=None):
        params = super(LiveCapture, self).get_parameters(packet_count = packet_count)
        for interface in self.interfaces:
            params += ["-i", interface]
        if self.bpf_filter:
            params += ["-f", self.bpf_filter]
        params += ["-p"] # Disable promiscuous mode.

        # Set Snap Length to the length of the header. This'll make it ignore the data of the packet.
        params += ["-s", str(TOTAL_HDR_LEN_B)]
        return params

# NOTE: This flag is used to tell the packet sniffing thread when to stop. Make sure to set it to False at some point or the capture will never stop!
shouldContinueSniffing = True

def main(netInterface):
    global packets, shouldContinueSniffing
    # TODO: Log any settings at the beginning of running this script. EG the timeout setting, the URL, etc.

    if (len(sys.argv) < 2):
        print("No URL argument received")
    url = sys.argv[1] # URL should be the first element in the input.
    print("Received URL: " + url)

    # Start the packet capture.
    # NOTE: I do this before anything else because after calling Thread.start(), it takes some time for the sniffing to actually get going. If I do it later, it's possible for it to miss part of the relevant data. It does include some extra stuff since it's so early, but it's necessary.
    shouldContinueSniffing = True
    eventLoop = asyncio.get_event_loop()
    sniffThread = Thread(target = capturePackets, args = [netInterface, eventLoop])
    print("Starting Wireshark sniffer.")
    sniffThread.start()

    options = Options()
    print("Options created")
    #options.add_argument("-headless")
    #options.add_argument("-P")
    #options.add_argument("headlessTester")
    print("Options set. Launching browser")
    ffDriver = webdriver.Firefox(options = options)
    print("Browser launched")

    pathToIndex = os.path.join(os.getcwd(), "index.html")

    print("Navigating browser to " + pathToIndex)
    ffDriver.get(pathToIndex)

    print(ffDriver.title)

    # Enter the URL for the manifest to be streamed in the input field.
    print("Inputting URL to webpage.")
    web_urlInput = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_INPUT_FIELD_ID)))
    web_urlInput.clear()
    web_urlInput.send_keys(url)

    # Start the stream.
    print("Starting stream.")
    web_urlConfirmButton = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_CONFIRM_BUTTON_ID)))
    web_urlConfirmButton.click()

    try:
        web_doneLabel = WebDriverWait(ffDriver, STREAM_TIMEOUT_SEC).until(EC.visibility_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
        # Successfully loaded the done label, so the stream finished. This means the log will have been saved by the JS script.
        print("Stream completed.")
    except TimeoutException:
        print("Timeout limit reached before stream completed.")
        # Since the stream failed to finish, it has not saved the log. Do that for it.
        web_saveButton = ffDriver.find_element(By.ID, SAVE_BUTTON_ID)
        web_saveButton.click()
    
    print("Stopping packet sniffer")
    shouldContinueSniffing = False
    sniffThread.join()
    print("Packet sniffer stopped")
    print("Waiting 5 seconds for live capture to complete.")
    time.sleep(5)

    print("Processing file output from live capture.")
    processPackets(PACKET_PCAP_FILENAME)

    # Make a directory for this run of the test.
    workingDirectory = os.getcwd()
    now_iso = datetime.datetime.now().isoformat().replace(":", "_") # Replace colons with underscores because Windows is evil.
    myHostname = socket.gethostname()
    resultsDirName = "Results_" + now_iso + "_" + myHostname
    resultsDirPath = os.path.join(workingDirectory, resultsDirName)
    os.mkdir(resultsDirPath)
    print("Results will be saved in directory " + resultsDirPath)

    web_doneLabel = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
    # After the save button is clicked, the done label will be filled with the title of the saved file.
    logName = web_doneLabel.get_attribute("textContent")
    downloadsPath = os.path.join(os.path.expanduser("~"), "Downloads") # This works on both Linux and Windows, assuming the downloads folder is the default.
    # Still have to search for the most recent file that contains the name because the JS player doesn't know if it was downloaded with a duplicate identifier (like `(1)`, `(2)`, etc) appended.
    mostRecentFileName = getLatestFileContainsNamePath(downloadsPath, logName)
    if (mostRecentFileName == ""):
        print("No JavaScript log file located. File will not be moved.")
    else:
        mostRecentFilePath = os.path.join(downloadsPath, mostRecentFileName)

        # Move the data files to the results directory.
        movedLogFilePath = os.path.join(resultsDirPath, mostRecentFileName)
        os.rename(mostRecentFilePath, movedLogFilePath)
        print("JavaScript log data moved to " + movedLogFilePath)

    # Output packet capture data to the results directory.
    print("Outputting Wireshark captured packets")
    packetPcapFileName = PACKET_PCAP_FILENAME
    packetPcapFilePath = os.path.join(workingDirectory, packetPcapFileName)
    newPacketPcapFilePath = os.path.join(resultsDirPath, packetPcapFileName)
    print("Moving packet PCAP file to " + newPacketPcapFilePath)
    os.rename(packetPcapFilePath, newPacketPcapFilePath)
    packetCsvFileName = PACKET_CSV_FILENAME
    packetCsvFilePath = os.path.join(workingDirectory, packetCsvFileName)
    newPacketCsvFilePath = os.path.join(resultsDirPath, packetCsvFileName)
    print("Moving packet CSV to " + packetCsvFilePath)
    os.rename(packetCsvFilePath, newPacketCsvFilePath)

    print("Exiting browser")
    ffDriver.quit()
    print("Test completed. Exiting")

def capturePackets(netInterface, eventLoop):
    global shouldContinueSniffing, packets
    asyncio.set_event_loop(eventLoop)
    liveCapture = NonPromLiveCapture(interface = netInterface, output_file = PACKET_PCAP_FILENAME)
    for _ in liveCapture.sniff_continuously():
        if not shouldContinueSniffing:
            print("Stopping live capture.")
            liveCapture.close()
            break

def processPackets(fileName):
    # This will return once the tshark command completes. I.e., it will block until processing is done.
    tsharkCommand = TSHARK_FILEOUTPUT_COMMAND.format(pcapName = PACKET_PCAP_FILENAME, csvName = PACKET_CSV_FILENAME)
    os.system(tsharkCommand)

def outputPackets(fileName, packets):
    with open(fileName, "w", newline = "") as csv_file:
        csvWriter = csv.writer(csv_file, delimiter = ",")
        isHeaderPrinted = False
        for packet in packets:
            if not isHeaderPrinted:
                csvWriter.writerow(vars(packet))
                isHeaderPrinted = True
            csvWriter.writerow(list(packet))

def getLatestFileContainsNamePath(dirPath, name):
    #files = sorted((f for f in os.listdir(dirPath) if f.find(name) != -1), 
    #               key=lambda f: os.stat(os.path.join(dirPath, f)).st_mtime)
    files = sorted((f for f in os.listdir(dirPath) if f.find(name) != -1), 
                   key=lambda f: os.path.getmtime(os.path.join(dirPath, f)))
    if (len(files) == 0):
        # There were no files located.
        return ""
    mostRecent = files[-1]
    return mostRecent

if __name__ == "__main__":
    main(netInterface = "Wi-Fi")