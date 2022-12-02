// cUDPingLnx.cpp (V1.0): the client of UDPing in Linux
//
// Author:  Huahui Wu
//          flashine@gmail.com
//
// History
//   Version 1.0 - 2005 Mar 08
//
// Description:
//	 cUDPingLnx.cpp
//		Very simple, Works in conjunction with sUDPingWin.cpp 
//		(a Windows server) or sUDPingLnx (a Linux server).
//		The program attempts to connect to the server and port
//		specified on the command line. The client keeps sending 
//		packets to the server and receiving the bounced packets 
//		from server and calculating the time difference.
//
// Compile and Link: 
//	 g++ cUDPingLnx.cpp -o cUDPingLnx -lpthread
//
// Run (Usage): 
//		cUDPingLnx -p portnumber -h hostname 
//			-s packet_size_in_bytes -n packet_number_per_second
//		where the default values are:
//			hostname	: localhost		
//			portnumber	:	1234
//			packet_size	:	12
//			packet_number:	5
//
// License: 
//   This software is released into the public domain.
//   You are free to use it in any way you like.
//   This software is provided "as is" with no expressed
//   or implied warranty.  I accept no liability for any
//   damage or loss of business that this software may cause.
//
//

#include <fstream>
#include <string>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <netdb.h>
#include <pthread.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <iostream>


#ifndef INADDR_NONE
#define INADDR_NONE 0xffffffff /* should be in <netinet/in.h> */
#endif


#define MAX_PKT_SIZE 4096
#define MAX_PKT_NUM 100



struct Ping_Pkt{
	int seq;
	struct timeval tv;
	unsigned char padding[MAX_PKT_SIZE];
};

//global variables
int pkt_sent=0, pkt_rcvd=0;
double p; //loss rate
int rtt_min = 2000, rtt_max = 0;
double rtt_avg = 0;
char* nmServer; //server name
short nPort; //port number
short sPkt;  //packet size in bytes
short nPkt;  //packet number per second
struct timeval initTv; // the timeval when PING starts
unsigned int fileSeq;



// Function prototype
void DatagramClient(char *szServer, short nPort);
void *SendFunc(void *); 
void CleanUp(int);

int	theSocket;
struct sockaddr_in saServer;


////////////////////////////////////////////////////////////


//std::ofstream out_file; // output file
std::ofstream out_file_csv; // output file csv
//std::ofstream seqFileOut;


int main(int argc, char **argv)
{
  int nRet;
//    std::ifstream seqFileIn;

    //--------------------

//    seqFileIn.open("sequeceFile.txt", std::ios::in);
//    // If "sequenceFile.txt" exists, read the last sequence from it and increment it by 1.
//    if (seqFileIn.is_open())
//    {
//        seqFileIn >> fileSeq;
//        fileSeq++;
//    }
//    else
//        fileSeq = 1; // if it does not exist, start from sequence 1.v
    //--------------------
//    std::string fileName = "UDPing_log" + std::to_string(fileSeq) + ".txt";
//    std::string fileName_csv = "UDPing_log" + std::to_string(fileSeq) + ".csv";
    std::string fileName_csv = "UDPing_log.csv";
//    out_file.open (fileName,std::ios::app);
    out_file_csv.open (fileName_csv);


    if(!out_file_csv){
        std::cerr << "Error creating file" << std::endl;
        return 1;
    }

  //use getopt to parse the command line
  // > cUDPingLnx -p portnumber -h hostname -s packet_size_in_bytes -n packet_number_per_second
  // where the default values are:
  //		portnumber	:	1234
  //		packet_size	:	16
  //		packet_number:	5
  int c;
  nmServer="localhost";
  nPort = 1234; //port number
  sPkt = sizeof(int)+sizeof(timeval);  //minimum packet size in bytes
  nPkt = 5;  //packet number per second
  
  while ((c = getopt(argc, argv, "p:h:s:n:")) != EOF)
    {
      switch (c)
        {
	case 'p':
	  printf("portnumber: %d\n", atoi(optarg));
	  nPort = atoi(optarg);
	  break;
	  
	case 'h':
	  printf("hostname: %s\n", optarg);
	  nmServer = optarg;
	  break;
	  
	case 's':
	  printf("packet size: %d\n", atoi(optarg));
	  sPkt = atoi(optarg);
	  if (sPkt > MAX_PKT_SIZE)
	    sPkt = MAX_PKT_SIZE;
	  break;
	  
	case 'n':
	  printf("packet number per second: %d\n", atoi(optarg));
	  nPkt = atoi(optarg);
	  if (nPkt > MAX_PKT_NUM)
	    nPkt = MAX_PKT_NUM;
	  break;
	  
	case '?':
	  printf("ERROR: illegal option %s\n", argv[optind-1]);
	  printf("Usage:\n");
	  printf("\t%s -p portnumber -h hostname -s packet_size_in_bytes -n packet_number_per_second\n", argv[0]);
	  exit(1); 
	  break;
	  
	default:
	  printf("WARNING: no handler for option %c\n", c);
	  printf("Usage:\n");
	  printf("\t%s -p portnumber -h hostname -s packet_size_in_bytes -n packet_number_per_second\n", argv[0]);
	  exit(1);
	  break;
        }
    }

  printf("Usage:\n");
  printf("\t%s -p portnumber -h hostname -s packet_size_in_bytes -n packet_number_per_second\n", argv[0]);

  //
  // Go do all the stuff a datagram client does
  //
  signal(SIGINT, CleanUp);
  DatagramClient(nmServer, nPort);
  
}

////////////////////////////////////////////////////////////

void DatagramClient(char *szServer, short nPort)
{
  struct hostent *hp;

  printf("Pinging %s with %d bytes of data:\n\n", szServer, sPkt);
//  out_file << "Pinging " << szServer << "  with "<< sPkt << " bytes of data:\n\n"; // to file
  out_file_csv << "Pinging " << szServer << "  with "<< sPkt << " bytes of data:,\n\n"; // to file

  
  //
  // Find the server
  //
  // Convert the host name as a dotted-decimal number.

   bzero((void *) &saServer, sizeof(saServer));
   printf("Looking up %s...\n", szServer);
//   out_file << "Looking up," << szServer << "... \n"; // to file
   if ((hp = gethostbyname(szServer)) == NULL) {
     perror("host name error");
//     out_file << "host name error"; // to file
     out_file_csv << "host name error,\n"; // to file
     exit(1);
   }
   bcopy(hp->h_addr, (char *) &saServer.sin_addr, hp->h_length);

   //
   // Create a UDP/IP datagram socket
   //
   theSocket = socket(AF_INET,			// Address family
		      SOCK_DGRAM,		// Socket type
		      IPPROTO_UDP);	// Protocol
   if (theSocket < 0){
       perror("Failed in creating socket");
//       out_file << "Failed in creating socket"; // to file
       out_file_csv << "Failed in creating socket,\n"; // to file
       exit(1);
   }
   
   //
   // Fill in the address structure for the server
   //
   saServer.sin_family = AF_INET;
   saServer.sin_port = htons(nPort);	// Port number from command line

   Ping_Pkt ping_pkt; 
   int nRet;

   ping_pkt.seq = 0; //prepare the first packet

   gettimeofday(&initTv, NULL);
   ping_pkt.tv = initTv;

   //send the first packet to setup the socket
   pkt_sent = 1;
   nRet = sendto(theSocket,		// Socket
		 (const char*)&ping_pkt,// Data buffer
		 sPkt,			// Length of data
		 0,			// Flags
		 (struct sockaddr *)&saServer,	// Server address
		 sizeof(struct sockaddr)); // Length of address
   if (nRet < 0 ){
       perror("sending");
//       out_file << "sending"; // to file
       close(theSocket);
       exit(1);
   } 

   pthread_t idA, idB; /* ids of threads */
   void *MyThread(void *);
   
   if (pthread_create(&idA, NULL, SendFunc, (void *)"Send") != 0) {
     perror("pthread_create");
//     out_file << "pthread_create"; // to file
     exit(1);
   }
 
   // Wait for the first reply
   //
   memset(&ping_pkt, 0, sizeof(Ping_Pkt));

   int nFromLen;
   int rtt;
   int tSent; // the time when each packet was sent in millisecond
   struct timeval curTv;

   out_file_csv << "server," << "bytes," << "rtt(ms)," << "seq," << "tSent(ms) \n";
   while(1){
     nFromLen = sizeof(struct sockaddr);
     nRet = recvfrom(theSocket,	// Socket
		     (char*)&ping_pkt, // Receive buffer
		     sPkt, // Length of receive buffer
		     0,	   // Flags
		     (struct sockaddr *)&saServer, // Sender's address
		     (socklen_t *)&nFromLen);  // Length of address buffer
     if (nRet < 0){
       perror("receiving");
//       out_file << "receiving"; // to file
       close(theSocket);
       exit(1);
     }

     pkt_rcvd ++;


     //get current tv
     gettimeofday(&curTv, NULL);

     //get rtt in millisecond
     rtt =(int)((curTv.tv_sec - ping_pkt.tv.tv_sec) * 1000 +
		+ (curTv.tv_usec - ping_pkt.tv.tv_usec)/1000 + 0.5);
     
     //get tSent in millisecond
     tSent =(int)((ping_pkt.tv.tv_sec - initTv.tv_sec) * 1000 +
		+ (ping_pkt.tv.tv_usec - initTv.tv_usec)/1000 + 0.5);
 
     if (rtt < rtt_min){
       rtt_min = rtt;
     }
     if (rtt > rtt_max){
       rtt_max = rtt;
     }
     
     rtt_avg = ((pkt_rcvd - 1) * rtt_avg + rtt) / pkt_rcvd;
     //
     // Display the data that was received
     //
     /*printf("Reply from %s: bytes=%d rtt=%dms seq=%d tSent=%dms\n",
	    nmServer, sPkt, rtt, ping_pkt.seq, tSent);*/
//     out_file << "Reply from " << nmServer << ": bytes=" <<  sPkt << " rtt=" << rtt << "ms" << " seq="
//     << ping_pkt.seq << " tSent=" <<  tSent << "ms\n" ; // to file
     out_file_csv << nmServer << "," << sPkt << "," << rtt << "," << ping_pkt.seq << "," << tSent << "\n";
   }



   
   (void)pthread_join(idA, NULL);
   printf("The sending thread is finished\n");

   close(theSocket);
   return;
}


void *SendFunc(void *arg) 
{ 
  // Send data to the server
  //
  Ping_Pkt ping_pkt; 
  int nRet;
  
  for (int i =1; ; i ++){
    ping_pkt.seq = i;
    gettimeofday(&ping_pkt.tv, NULL);
    
    pkt_sent ++;
    nRet = sendto(theSocket,		// Socket
		  (const char*)&ping_pkt,	// Data buffer
		  sPkt,			// Length of data
		  0,			// Flags
		  (struct sockaddr *)&saServer,	// Server address
		  sizeof(struct sockaddr)); // Length of address
    if (nRet < 0)
      {
	perror("sending");
	close(theSocket);
	exit(1);
      }
    usleep(1000000/nPkt);
  }
} 

void CleanUp(int arg1){
//    std::cout << std::fixed << std::setprecision(2) << rtt_avg;
//    std::cout << std::fixed << std::setprecision(2) << p;
  p = (100.0 * (pkt_sent-pkt_rcvd)) / pkt_sent;
  printf("Ping statistics for %s:\n", nmServer);
//  out_file << "Ping statistics for " << nmServer << ":\n"; //out file
  printf("\tPackets: Sent = %d, Received = %d, Lost = %d (%6.2f %%loss),\n", pkt_sent, pkt_rcvd, pkt_sent-pkt_rcvd, p);
//  out_file << "Packets: Sent = " << pkt_sent << ", Received = " << pkt_rcvd << ", Lost = " << pkt_sent-pkt_rcvd
//  << " (  " << p << " %loss),\n"; // out file
  printf("Approximate round trip times in milli-seconds:\n");
//  out_file << "Approximate round trip times in milli-seconds:\n"; // out file
  printf("\tMinimum = %dms, Maximum = %dms, Average = %6.2fms\n", rtt_min, rtt_max, rtt_avg);
//  out_file << "\tMinimum = " << rtt_min <<"ms, Maximum = "<< rtt_max << "ms, Average = "<< rtt_avg <<"ms\n";
  out_file_csv << "Ping statistics \n";
  out_file_csv << "Sent," << pkt_sent << "\n";
  out_file_csv << "Received," << pkt_rcvd << "\n";;
  out_file_csv << "Lost," << pkt_sent-pkt_rcvd << "\n";;
  out_file_csv << "Minimum rtt(ms)," << rtt_min << "\n";;
  out_file_csv << "Maximum rtt(ms)," << rtt_max << "\n";;
  out_file_csv << "Average rtt(ms)," <<  rtt_avg << "\n";
//  out_file.close();
  out_file_csv.close();
//  seqFileOut.open("sequeceFile.txt", std::ios::out);
//  seqFileOut << fileSeq;
  std::cout << "Output saved to file" << std::endl;
  close(theSocket);
  exit(0);
}
