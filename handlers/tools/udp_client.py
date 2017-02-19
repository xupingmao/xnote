# from socket import *  

# HOST = '192.168.0.10'  
# PORT = 21567  
# BUFSIZE = 1024  

# ADDR = (HOST, PORT)  

# udpCliSock = socket(AF_INET, SOCK_DGRAM)  

# while True:  
#     data = input('>')  
#     if not data:  
#         break  
#     udpCliSock.sendto(bytes(data,encoding='utf-8'),ADDR)  
#     data,ADDR = udpCliSock.recvfrom(BUFSIZE)  
#     if not data:  
#         break  
#     print (data)  # data is byte

# udpCliSock.close()