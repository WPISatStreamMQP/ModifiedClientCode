import pyshark
from pyshark import LiveCapture

INTERFACE = "Wi-Fi"

class NonPromLiveCapture(LiveCapture):
    def get_parameters(self, packet_count=None):
        params = super(LiveCapture, self).get_parameters(packet_count = packet_count)
        for interface in self.interfaces:
            params += ["-i", interface]
        if self.bpf_filter:
            params += ["-f", self.bpf_filter]
        params += ["-p"] # Disable promiscuous mode.
        return params

def main():
    # TODO: Re-enable promiscuous mode.
    capture = NonPromLiveCapture(interface = INTERFACE)
    print("Sniffing")
    capture.sniff(packet_count = 50)
    print(capture)
    ct = 0
    # TODO: We only need the header of the packet. Tell Pyshark to only collect that (SNAP length). Might be a custom parameter added to the Pyshark setup similar to disabling promisc. Will keep the data smaller.
    for packet in capture:
        #print(dir(packet))

        layer = getattr(packet, "tcp", None)
        if layer is not None:
            print("Packet is TCP")
            #print(dir(layer))
            print_packet_time(layer)
            #break
        
        layer = getattr(packet, "udp", None)
        if layer is not None:
            print("Packet is UDP")
            #print(dir(layer))
            print_packet_time(layer)
            #break

def print_packet_time(transport_layer):
    #print("time_delta: " + str(transport_layer.time_delta))
    print("time_relative: " + str(transport_layer.time_relative))

if __name__ == "__main__":
    main()