#include <stdio.h> 
#include <Winsock2.h> 
#pragma comment(lib, "WS2_32.lib") 

void main() 
{ 
WORD wVersionRequested; 
WSADATA wsaData; 
int err; 

wVersionRequested = MAKEWORD( 2, 2 ); 

err = WSAStartup( wVersionRequested, &wsaData ); 
if ( err != 0 ) { 
  printf("There is no usable winsock DLL");
  return; 
} 

if ( LOBYTE( wsaData.wVersion ) != 2 || HIBYTE( wsaData.wVersion ) != 2 ) { 
  /* winsockDLL的版本不是2.2*/ 
  WSACleanup( ); 
  return; 
} 
//创建数据报套接字，绑定端口5050
SOCKET sockSrv=socket(AF_INET, SOCK_DGRAM, 0); 
SOCKADDR_IN addrSrv; 
addrSrv.sin_family=AF_INET; 
addrSrv.sin_port=htons(5050); 
addrSrv.sin_addr.S_un.S_addr=htonl(INADDR_ANY); 
bind(sockSrv,(SOCKADDR*)&addrSrv,sizeof(SOCKADDR)); 

char recvBuf[200]; //接收缓冲区
char sendBuf[200]; //发送缓冲区
SOCKADDR_IN addrCli;  //用户保存客户端地址
int len = sizeof(SOCKADDR); 
recvfrom(sockSrv,recvBuf,200,0,(SOCKADDR*)&addrCli,&len); 
//接收客户端发送的数据，客户端的地址将保存在变量addrCli中
if(recvBuf[0]!=0) 
{
	printf("I have received:%s from %s\n",recvBuf,inet_ntoa(addrCli.sin_addr));
	sprintf(sendBuf,"I have received:%s",recvBuf);
	sendto(sockSrv,sendBuf,strlen(sendBuf)+1,0,(SOCKADDR*)&addrCli,len); 
}
closesocket(sockSrv); 
WSACleanup();

} 


