# encoding=utf-8
# Created by xupingmao on 2017/04/20
# TCP代理转发

import socket
import threading

# Note For best match with hardware and network realities, 
# the value of bufsize should be a relatively small power of 2, for example, 4096.
# 接收数据缓存大小
PKT_BUFF_SIZE = 4096
TIMEOUT = 5.0

# 调试日志封装
def send_log(*content):
    print(threading.current_thread().name, *content)

# 单向流数据传递
def tcp_mapping_worker(conn_receiver, conn_sender):
    while True:
        try:
            data = conn_receiver.recv(PKT_BUFF_SIZE)
        except Exception as e:
            send_log('Event: Connection closed. Thread Count: ', len(threading.enumerate()), e)
            break

        if not data:
            send_log('Info: No more data is received.')
            break

        try:
            conn_sender.sendall(data)
        except Exception:
            send_log('Error: Failed sending data.')
            break

        # send_log('Info: Mapping data > %s ' % repr(data))
        send_log('Info: Mapping > %s -> %s > %d bytes.' % (conn_receiver.getpeername(), conn_sender.getpeername(), len(data)))

# 端口映射请求处理
def tcp_mapping_request(local_conn, remote_ip, remote_port):
    remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        remote_conn.connect((remote_ip, remote_port))
        if hasattr(local_conn, "settimeout"):
            local_conn.settimeout(TIMEOUT)
        if hasattr(remote_conn, "settimeout"):
            remote_conn.settimeout(TIMEOUT)
    except Exception:
        local_conn.close()
        send_log('Error: Unable to connect to the remote server.')
        return

    # 并发的处理Request和Response，提高转发效率
    send_thread = threading.Thread(target=tcp_mapping_worker, args=(local_conn, remote_conn))
    # 全部返回之后才可以关闭socket，最好放在一个单独的队列里关闭
    recv_thread = threading.Thread(target=tcp_mapping_worker, args=(remote_conn, local_conn))

    send_thread.start()
    recv_thread.start()

    # 等待进程结束
    send_thread.join()
    recv_thread.join()

    # 关闭socket连接
    local_conn.close()
    remote_conn.close()

# 端口映射函数
# (local_ip, local_port) 是监听地址
def tcp_mapping(remote_ip, remote_port, local_ip, local_port):
    local_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 设置socket重用
    local_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    local_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    
    local_server.bind((local_ip, local_port))
    local_server.listen(20)

    send_log('Event: Starting mapping service on ' + local_ip + ':' + str(local_port) + ' ...')

    while True:
        try:
            (local_conn, local_addr) = local_server.accept()
        except (KeyboardInterrupt, Exception):
            # KeyboardInterrupt 不能立即关闭
            local_server.close()
            send_log('Event: Stop mapping service.')
            break
        # 使用线程池优化
        threading.Thread(target=tcp_mapping_request, args=(local_conn, remote_ip, remote_port)).start()

        send_log('Event: Receive mapping request from %s:%d.' % local_addr)


# 主函数
if __name__ == '__main__':
    # tcp_mapping("127.0.0.1", 1234, "0.0.0.0", 1081)
    tcp_mapping("127.0.0.1", 8080, "0.0.0.0", 1081)

