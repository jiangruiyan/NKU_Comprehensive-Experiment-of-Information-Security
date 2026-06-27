/*udpserver.c*/
#include <netinet/in.h>
#include <stdio.h>
#include <errno.h>
#define SERVER_PORT 8888 
#define MAX_MSG_SIZE 1024 

void udps_respon(int sockfd) 
{ 
struct sockaddr_in addr; 
int addrlen, n; 
char msg[MAX_MSG_SIZE]; 
while(1) 
{ /* 从网络上读数据 */ 
n=recvfrom(sockfd,msg,MAX_MSG_SIZE,0, (struct sockaddr*)&addr, &addrlen); 
msg[n]=0; 
/* 显示服务端已经收到了信息 */ 
fprintf(stdout,"I have received：%s",msg);
/*将收到的信息发送给客户端*/ 
sendto(sockfd, msg,n,0,(struct sockaddr*)&addr,addrlen); 
} 
} 
int main(void)
{ 
int sockfd; 
struct sockaddr_in addr; 
sockfd=socket(AF_INET,SOCK_DGRAM,0);  
if(sockfd<0) 
{ 
fprintf(stderr,"Socket Error:%s\n",strerror(errno)); 
exit(1); 
} 
/*填充服务器地址结构*/
bzero(&addr,sizeof(struct sockaddr_in)); 
addr.sin_family=AF_INET;
addr.sin_addr.s_addr=htonl(INADDR_ANY); 
addr.sin_port=htons(SERVER_PORT);
/*绑定服务器地址*/ 
if(bind(sockfd, (struct sockaddr *)&addr, sizeof(struct sockaddr_in))<0) 
{ 
fprintf(stderr,"Bind Error:%s\n", strerror(errno)); 
exit(1); 
} 
udps_respon(sockfd); 
close(sockfd); 
} 


