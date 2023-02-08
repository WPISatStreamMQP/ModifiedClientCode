import os
import sys
import datetime
import socket
import pyshark
import asyncio
import csv
import time
import dns.resolver
import shutil
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyshark import LiveCapture
from threading import Thread
from urllib.parse import urlparse
import csv
import os , signal
import subprocess

ETH_HDR_LEN_B = 14
IP_HDR_LEN_MAX_B = 60
# The UDP max header length is 8 bytes, and the QUIC max header length is 20 bytes. So TCP at 60 bytes has the largest possible header.
TCP_HDR_LEN_MAX_B = 60 # 20 bytes usually, but 60 is the absolute max supported due to the size of the IHL field.
TOTAL_HDR_LEN_B = ETH_HDR_LEN_B + IP_HDR_LEN_MAX_B + TCP_HDR_LEN_MAX_B

STREAM_TIMEOUT_SEC = 1800 # Timeout streams after 30 minutes and assume it encountered errors.
GENERIC_TIMEOUT_SEC = 3 # When accessing a regular element, timeout after just three seconds.

URL_INPUT_FIELD_ID = "urlInput"
URL_CONFIRM_BUTTON_ID = "urlConfirmButton"
STREAM_DONE_LABEL_ID = "streamDoneLabel"
SAVE_BUTTON_ID = "save_btn"

CLIENT_PACKET_PCAP_FILENAME = "packets_client.pcap"
SERVER_PACKET_PCAP_FILENAME = "packets_server.pcap"
CLIENT_PACKET_CSV_FILENAME = "packets_client.csv"
SERVER_PACKET_CSV_FILENAME = "packets_server.csv"
UDPING_LOG_FILENAME = "UDPing_log.csv"

MLCNET_SERVER_HOSTNAMES = ["mlcneta.cs.wpi.edu", "mlcnetb.cs.wpi.edu", "mlcnetc.cs.wpi.edu", "mlcnetd.cs.wpi.edu"]

TSHARK_FILEOUTPUT_COMMAND = "tshark -r {pcapName} -t r -T fields "\
                            "-e _ws.col.Time -e frame.len -e ip.src -e ip.dst "\
                            "-E header=y -E separator=, "\
                            "-Y \"(ip.src == {serverIp}) || (ip.dst == {serverIp})\" "\
                            "> {csvName}"
PORT = 1234

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

def runSingleTest(url, netInterface):
    global shouldContinueSniffing

    print("Listening on network interface: " + netInterface)

    serverIp = getServerIp(url)
    print("Server IP: " + serverIp)

    print("Test will time out and terminate if video stream takes longer than %s seconds."%STREAM_TIMEOUT_SEC)
    print("Assuming total header length of %s bytes."%TOTAL_HDR_LEN_B)

    print("\nCurrent users:")
    subprocess.Popen("w", shell = True).wait()

    print("\n`ip route` output:")
    subprocess.Popen("ip route", shell = True).wait()

    print("\nCPU utilization")
    subprocess.Popen("ps aux --sort -pcpu | grep -v USER | head -n 20", shell = True).wait()
    print("\n")

    # Start the server packet capture.
    print("Starting Wireshark sniffer on server.")
    startTSharkOnServer(url)

    # Start UDPing on the server. Do this early-ish because it may take some time to get going and we want our UDPing client to find it immediately once it starts.
    print("Starting UDPing on server.")
    startUDPingOnServer(url, PORT)

    # Start the client packet capture.
    # NOTE: I do this before anything else because after calling Thread.start(), it takes some time for the sniffing to actually get going. If I do it later, it's possible for it to miss part of the relevant data. It does include some extra stuff since it's so early, but it's necessary.
    shouldContinueSniffing = True
    asyncio.set_event_loop(asyncio.new_event_loop())
    sniffThread = Thread(target = capturePackets, args = [netInterface])
    print("Starting Wireshark sniffer on client (here).")
    sniffThread.start()

    # Start UDPing
    asyncio.set_event_loop(asyncio.new_event_loop())
    pingThread = Thread(target=startUDPing)
    print("Starting UDPing on client (here).")
    pingThread.start()
    
    options = Options()
    options.add_argument("-headless")
    #options.add_argument("-P")
    #options.add_argument("headlessTester")
    print("Options set. Launching browser")
    ffDriver = webdriver.Firefox(options = options)
    print("Browser launched")

    pathToIndex = "file://" + os.path.join(os.getcwd(), "index.html")

    print("Navigating browser to " + pathToIndex)
    ffDriver.get(pathToIndex)

    print(ffDriver.title)

    # Enter the URL for the manifest to be streamed in the input field.
    print("Inputting URL to webpage.")
    web_urlInput = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_INPUT_FIELD_ID)))
    web_urlInput.clear()
    web_urlInput.send_keys(url)

    now_iso = datetime.datetime.now().isoformat()

    # Start the stream.
    # I include the time so that you can watch the console output and know roughly how long it's been running for.
    # Asterisks are to call attention to when the stream actually started.
    print("\n************* Starting stream at time " + now_iso)
    web_urlConfirmButton = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_CONFIRM_BUTTON_ID)))
    web_urlConfirmButton.click()

    try:
        web_doneLabel = WebDriverWait(ffDriver, STREAM_TIMEOUT_SEC).until(EC.visibility_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
        # Successfully loaded the done label, so the stream finished. This means the log will have been saved by the JS script.
        print("************* Stream completed.\n")
    except TimeoutException:
        print("************* Timeout limit reached before stream completed.\n")
        # Since the stream failed to finish, it has not saved the log. Do that for it.
        web_saveButton = ffDriver.find_element(By.ID, SAVE_BUTTON_ID)
        web_saveButton.click()
    

    
    ########################### TEST IS COMPLETE at this point. Analysis is next.

    print("Stopping UDPing on client (here).")
    killUDPingProcess()
    pingThread.join()

    print("Stopping UDPing on server.")
    killUDPingOnServer(url)

    print("Stopping server packet sniffer.")
    killTSharkOnServer(url)
    
    print("Stopping client (here) packet sniffer.")
    shouldContinueSniffing = False
    sniffThread.join()
    print("Packet sniffer stop signal sent.")

    # Ran this here because it takes time so we can use this wait to allow the local capture to stop.
    print("Downloading packet capture from server.")
    downloadPacketsFromServer(url)

    print("Waiting 5 seconds for live capture to complete.")
    time.sleep(5)

    print("Processing file output from live capture.")
    processPackets(CLIENT_PACKET_PCAP_FILENAME, CLIENT_PACKET_CSV_FILENAME, serverIp)
    processPackets(SERVER_PACKET_PCAP_FILENAME, SERVER_PACKET_CSV_FILENAME, serverIp)

    # Make a directory for this run of the test.
    workingDirectory = os.getcwd()
    myHostname = socket.gethostname()
    resultsDirName = "Results_" + now_iso.replace(":", "_") + "_" + myHostname # Replace colons with underscores because Windows is evil.
    resultsDirPath = os.path.join(workingDirectory, resultsDirName)
    os.mkdir(resultsDirPath)
    print("Results will be saved in directory " + resultsDirPath)

    web_doneLabel = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
    # After the save button is clicked, the done label will be filled with the title of the saved file.
    logName = web_doneLabel.get_attribute("textContent")
    downloadsPath = os.path.join(os.path.expanduser("~"), "Downloads") # This works on both Linux and Windows, assuming the downloads folder is the default.
    currentPath = os.path.join(os.getcwd())
    # Still have to search for the most recent file that contains the name because the JS player doesn't know if it was downloaded with a duplicate identifier (like `(1)`, `(2)`, etc) appended.
    mostRecentFileName = getLatestFileContainsNamePath(downloadsPath, logName)
    if (mostRecentFileName == ""):
        print("No JavaScript log file located. File will not be moved.")
    else:
        mostRecentFilePath = os.path.join(downloadsPath, mostRecentFileName)

        # Move the data files to the results directory.
        movedLogFilePath = os.path.join(resultsDirPath, mostRecentFileName)
        shutil.move(mostRecentFilePath, movedLogFilePath)
        print("JavaScript log data moved to " + movedLogFilePath)
    
    mostRecentFileNameUDPing = getLatestFileContainsNamePath(currentPath, UDPING_LOG_FILENAME)
    if(mostRecentFileNameUDPing == ""):
        print("No UDPing log file located. File will not be moved.")
    else:
        mostRecentFilePathUDPing = os.path.join(currentPath, mostRecentFileNameUDPing)

        # Move the data files to the results directory.
        movedLogFilePathUDPing = os.path.join(resultsDirPath, mostRecentFileNameUDPing)
        shutil.move(mostRecentFilePathUDPing, movedLogFilePathUDPing)
        print("UDPing log data moved to " + movedLogFilePathUDPing)

    # Output packet capture data to the results directory.
    # Move client packet data.
    print("Outputting Wireshark captured packets")
    clientPacketPcapFileName = CLIENT_PACKET_PCAP_FILENAME
    clientPacketPcapFilePath = os.path.join(workingDirectory, clientPacketPcapFileName)
    newClientPacketPcapFilePath = os.path.join(resultsDirPath, clientPacketPcapFileName)
    print("Moving client packet PCAP file to " + newClientPacketPcapFilePath)
    shutil.move(clientPacketPcapFilePath, newClientPacketPcapFilePath)

    clientPacketCsvFileName = CLIENT_PACKET_CSV_FILENAME
    clientPacketCsvFilePath = os.path.join(workingDirectory, clientPacketCsvFileName)
    newClientPacketCsvFilePath = os.path.join(resultsDirPath, clientPacketCsvFileName)
    print("Moving client packet CSV to " + newClientPacketCsvFilePath)
    shutil.move(clientPacketCsvFilePath, newClientPacketCsvFilePath)

    # Move server packet data.
    serverPacketPcapFileName = SERVER_PACKET_PCAP_FILENAME
    serverPacketPcapFilePath = os.path.join(workingDirectory, serverPacketPcapFileName)
    newServerPacketPcapFilePath = os.path.join(resultsDirPath, serverPacketPcapFileName)
    print("Moving server packet PCAP file to " + newServerPacketPcapFilePath)
    shutil.move(serverPacketPcapFilePath, newServerPacketPcapFilePath)

    serverPacketCsvFileName = SERVER_PACKET_CSV_FILENAME
    serverPacketCsvFilePath = os.path.join(workingDirectory, serverPacketCsvFileName)
    newServerPacketCsvFilePath = os.path.join(resultsDirPath, serverPacketCsvFileName)
    print("Moving server packet CSV file to " + newServerPacketCsvFilePath)
    shutil.move(serverPacketCsvFilePath, newServerPacketCsvFilePath)

    print("Closing browser")
    ffDriver.quit()
    print("Test completed. Exiting")

# NON-BLOCKING. Will immediately return after launching tshark.
def startTSharkOnServer(url):
    hostname = getHostname(url)
    if (hostname not in MLCNET_SERVER_HOSTNAMES):
        return
    # We are accessing an MLCNet server, so we can do SSH commands to it.
    # The ampersands detach from the process so this function doesn't block until tshark terminates.
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"tshark -w ~/output.pcap -s {snaplen} &\" &".format(host = hostname,
                                                                                                       snaplen = TOTAL_HDR_LEN_B))

def killTSharkOnServer(url):
    hostname = getHostname(url)
    if (hostname not in MLCNET_SERVER_HOSTNAMES):
        return
    # We are accessing an MLCNet server, so we can do SSH commands to it.
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"pkill -15 tshark\"".format(host = hostname))

# NON-BLOCKING. Will immediately return after launching sUDPingLnx.
def startUDPingOnServer(url,port):
    print("Starting UDPing on the server.")
    hostname = getHostname(url)
    if (hostname not in MLCNET_SERVER_HOSTNAMES):
        return
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"~/UDPing/sUDPingLnx {host}:{port} &\" &".format(host = hostname, port = port))

def killUDPingOnServer(url):
    print("Killing UDPing on the server.")
    hostname = getHostname(url)
    if (hostname not in MLCNET_SERVER_HOSTNAMES):
        return
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"pkill -15 sUDPingLnx\"".format(host = hostname))



def downloadPacketsFromServer(url):
    hostname = getHostname(url)
    if (hostname not in MLCNET_SERVER_HOSTNAMES):
        return
    # We are accessing an MLCNet server, so we can do SSH commands to it.

    # Copy the packet file from the server over to linux.cs.wpi.edu, then from linux.cs.. back to glomma. We need to do two transfers because downloading from glomma will run over the satellite (slowly), and uploading directly to Glomma from MLCNetA will fail because Glomma's acknowledgement messages will be returned over the satellite and MLCNet doesn't expect that.
    
    # Copies from host to linux.cs...
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"scp -i ~/.ssh/id_rsa_script ~/output.pcap linux.cs.wpi.edu:~/output.pcap\""
              .format(host = hostname))
    # Copies from linux.cs.. to here.
    os.system("ssh -i ~/.ssh/id_rsa_script linux.cs.wpi.edu \"scp -i ~/.ssh/id_rsa_script ~/output.pcap glomma:{workingDir}/packets_server.pcap\""
              .format(workingDir = os.getcwd()))
    # Delete packet file from the host.
    os.system("ssh -i ~/.ssh/id_rsa_script {host} \"rm ~/output.pcap\"".format(host = hostname))
    # Delete packet file from linux.cs...
    os.system("ssh -i ~/.ssh/id_rsa_script linux.cs.wpi.edu \"rm ~/output.pcap\"")

def startUDPing():
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop()
    asyncio.get_child_watcher()
    print("Starting cUDPing process")
    # This will block until UDPing returns (when it finishes).
    os.system("./cUDPingLnx -p 1234 -h mlcneta.cs.wpi.edu")
    print("cUDPing process successfully killed.")

def killUDPingProcess():
    name = 'cUDPing'
    try:

        # iterating through each instance of the process
        for line in os.popen("ps ax | grep " + name + " | grep -v grep"):
            fields = line.split()

            # extracting Process ID from the output
            pid = fields[0]

            # terminating process
            print("Sending SIGINT to cUDPing")
            os.kill(int(pid), signal.SIGINT)

    except:
        print("Error Encountered while trying to kill cUDPing")

def getServerIp(url):
    host = getHostname(url)
    dnsResult = dns.resolver.resolve(host, "A") # Search for `A` (IPv4) records.
    if len(dnsResult) == 0:
        return ""
    return dnsResult[0].to_text()

def getHostname(url):
    if not url:
        return ""
    parsedUrl = urlparse(url)

    host = parsedUrl.hostname
    return host

def capturePackets(netInterface):
    global shouldContinueSniffing, packets
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop()
    asyncio.get_child_watcher()
    liveCapture = NonPromLiveCapture(interface = netInterface, output_file = CLIENT_PACKET_PCAP_FILENAME)
    for _ in liveCapture.sniff_continuously():
        if not shouldContinueSniffing:
            print("Stopping live capture.")
            liveCapture.close()
            break

def processPackets(pcapFileName, csvFileName, serverIp):
    # This will return once the tshark command completes. I.e., it will block until processing is done.
    tsharkCommand = TSHARK_FILEOUTPUT_COMMAND.format(pcapName = pcapFileName,
                                                     csvName = csvFileName,
                                                     serverIp = serverIp)
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

def main():
    if (len(sys.argv) < 3):
        print("Either URL or network interface arguments were not received.")
        return
    url = sys.argv[1] # URL should be the first element in the input.
    print("Received URL: " + url)
    netInterface = sys.argv[2] # Network interface should be the second element in the input.

    runSingleTest(url, netInterface)

if __name__ == "__main__":
    main()