#!/bin/env python3
# -*- coding: GBK -*-
# 
# work worker�������̣���Ҫ����: 
#   .) ����CancelRequest
#   .) �����ʼ�
# 
import sys, os
import logging, signal
from netutils import *
from miscutils import *

# ��Ϣ��������
# ����msg : (msg_type, msg_data, fd_list)

# ��CancelRequest��Ϣmsg_raw������������дӿ�
def process_cancel_request_msg(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(g_conf['master'])
        s.sendall(msg[1])
        s.close()
    except Exception as ex:
        logging.warning('Exception while sending CancelRequest: %s', str(ex))
    
    for slaver in g_conf['slaver_list']:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(slaver)
            s.sendall(msg[1])
            s.close()
        except Exception as ex:
            logging.warning('Exception while sending CancelRequest: %s', str(ex))

def process_promote_result_msg(msg):
    msg_data = msg[1].decode('utf8')
    if msg_data[0] == 'E': # 'E' + errmsg
        # ������Ҫ���ͱ����ʼ�
        logging.warning('promote fail:%s' % (msg_data[1:], ))
    else: # 'S' + m_ip,m_port;s_ip,s_port;...
        logging.info('promote succeed:%s' % (msg_data[1:], ))
        addr_list = [x.split(',') for x in msg_data[1:].split(';')]
        g_conf['master'] = (addr_list[0][0], int(addr_list[0][1]))
        s_list = []
        for addr in addr_list[1:]:
            s_list.append((addr[0], int(addr[1])))
        g_conf['slaver_list'] = s_list

def process_mail_msg(msg):
    msg_data = msg[1].decode('utf8')
    logging.info('mail msg:%s' % (msg_data, ))

# ���������̵���Ϣ����
msg_process_map = {
    b'c' : process_cancel_request_msg,  # ����CancelRequest
    b'P' : process_promote_result_msg,  # �������
    b'M' : process_mail_msg,            # �����ʼ�
}

def work_worker(ipc_uds_path):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    # �Ƚ����������̵�����
    ipc_ep = connect_to_main_process(ipc_uds_path, 'work')
    
    poll = spoller()
    poll.register(ipc_ep, poll.POLLIN)
    while True:
        msg_list = []
        x = poll.poll()
        for fobj, event in x:
            if fobj == ipc_ep:
                if event & poll.POLLOUT:
                    x = fobj.send()
                    if x == None:
                        poll.register(fobj, poll.POLLIN)
                if event & poll.POLLIN:
                    x = fobj.recv()
                    if x[0] != -1:
                        continue
                    msg_list.append(x[1])
            else:
                logging.error('BUG: unknown fobj: %s', fobj)
        # ������յ�����Ϣ
        for msg in msg_list:
            msg_type = msg[0]
            logging.info('[work_worker]recved msg: %s', msg)
            if msg_type in msg_process_map:
                msg_process_map[msg_type](msg)
            else:
                logging.error('BUG: unknown msg from main process: %s', msg)
    os._exit(0)

# main
g_conf = None

if __name__ == '__main__':
    pass

