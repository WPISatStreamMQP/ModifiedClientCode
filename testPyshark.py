import pyshark
from pyshark import LiveCapture
from threading import Thread
import time
import asyncio
import csv

INTERFACE = "Wi-Fi"

shouldContinueSniffing = True

class Packet:
    def __init__(self, frame_time, frame_length):
        self.frame_time = str(frame_time)
        self.frame_length = str(frame_length)
    def __iter__(self):
        return iter([self.frame_time, self.frame_length])
packets = []

class NonPromLiveCapture(LiveCapture):
    def get_parameters(self, packet_count=None):
        params = super(LiveCapture, self).get_parameters(packet_count = packet_count)
        for interface in self.interfaces:
            params += ["-i", interface]
        if self.bpf_filter:
            params += ["-f", self.bpf_filter]
        params += ["-p"] # Disable promiscuous mode.
        return params

def capturePackets(eventLoop):
    global shouldContinueSniffing
    asyncio.set_event_loop(eventLoop)
    print("Start sniffer")
    capture = NonPromLiveCapture(interface = INTERFACE)
    for packet in capture.sniff_continuously():
        if not shouldContinueSniffing:
            print("End sniffer")
            break

        frame_time_rel = packet.frame_info.time_relative
        frame_length = packet.frame_info.len

        packets.append(Packet(frame_time_rel, frame_length))

def outputPackets(fileName, packets):
    with open(fileName, "w", newline = "") as csv_file:
        csvWriter = csv.writer(csv_file, delimiter = ",")
        isHeaderPrinted = False
        for packet in packets:
            if not isHeaderPrinted:
                csvWriter.writerow(vars(packet))
                isHeaderPrinted = True
            csvWriter.writerow(list(packet))

def main():
    eventLoop = asyncio.get_event_loop()
    print("Created sniffer")
    sniffThread = Thread(target = capturePackets, args = [eventLoop])
    print("Starting sniffer")
    sniffThread.start()

    print("Waiting 5 seconds")
    time.sleep(5)

    print("Telling sniffer to stop")
    global shouldContinueSniffing
    shouldContinueSniffing = False
    sniffThread.join()
    print("Stopped sniffer")

    #print(packets)
    #for packet in packets:
    #    print(packet.frame_time)

    outputPackets("packets.csv", packets)

    # TODO: Re-enable promiscuous mode.
    # capture = NonPromLiveCapture(interface = INTERFACE)
    # print("Sniffing")
    # capture.sniff(packet_count = 10)
    # print(capture)
    # ct = 0
    # # TODO: We only need the header of the packet. Tell Pyshark to only collect that (SNAP length). Might be a custom parameter added to the Pyshark setup similar to disabling promisc. Will keep the data smaller.
    # for packet in capture:
    #     # print(dir(packet))
    #     # print("sniff_time: " + str(packet.sniff_time))
    #     # print("sniff_timestamp: " + str(packet.sniff_timestamp))
    #     # print("length: " + str(packet.length))
    #     # print("dir(frame_info): " + str(dir(packet.frame_info)))

    #     print("frame_info.len: " + str(packet.frame_info.len))
    #     print("frame_info.time_relative: " + str(packet.frame_info.time_relative))
    #     print("")

    #     # tlayer = getattr(packet, "transport_layer", None)
    #     # if (tlayer is not None):
    #     #     print("Transport layer:")
    #     #     print(tlayer)
    #     #     print(dir(tlayer))

    #     # layer = getattr(packet, "tcp", None)
    #     # if layer is not None:
    #     #     print("Packet is TCP")
    #     #     print(dir(layer))
    #     #     print("Equal to packet[tlayer]? " + str(layer == packet[tlayer]))
    #     #     #print_packet_time(layer)
    #     #     #break
        
    #     # layer = getattr(packet, "udp", None)
    #     # if layer is not None:
    #     #     print("Packet is UDP")
    #     #     print(dir(layer))
    #     #     #print_packet_time(layer)
    #     #     #break

def print_packet_time(transport_layer):
    #print("time_delta: " + str(transport_layer.time_delta))
    print("time_relative: " + str(transport_layer.time_relative))

if __name__ == "__main__":
    main()