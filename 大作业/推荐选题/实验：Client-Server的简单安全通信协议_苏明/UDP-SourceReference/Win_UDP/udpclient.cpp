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
return; 
} 
if ( LOBYTE( wsaData.wVersion ) != 2 || 
HIBYTE( wsaData.wVersion ) != 2 ) { 
WSACleanup( ); 
return; 
} 
SOCKET sockCli=socket(AF_INET,SOCK_DGRAM,0); 
SOCKADDR_IN addrSrv; 
addrSrv.sin_family=AF_INET; 
addrSrv.sin_port=htons(5050); 
addrSrv.sin_addr.S_un.S_addr=inet_addr("127.0.0.1"); //服务器假设为本机
char recvBuf[200]; 
char sendBuf[200]; 
int len=sizeof(SOCKADDR); 
printf("Say some words send to server:\n"); 
gets(sendBuf);  //从控制台输入数据
sendto(sockCli,sendBuf,strlen(sendBuf)+1,0,(SOCKADDR*)&addrSrv,len); 
//发送给服务器
recvfrom(sockCli,recvBuf,strlen(recvBuf)+1,0,(SOCKADDR*)&addrSrv,&len); 
//接收服务器的应答
if(recvBuf[0]!=0) 
{
printf("response from sever:%s, IP is %s",recvBuf,inet_ntoa(addrSrv.sin_addr)); 
} 
closesocket(sockCli);
WSACleanup( ); 
} 
