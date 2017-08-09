#!/bin/env python3
# -*- coding: GBK -*-
# 
# dispatch worker���̡����ڰ�ǰ�����ӷַ�����Ӧ��proxy worker��
# �������ڽ���proxy worker�����Ӻ󣬰����ӷ���dispacth worker��֮��dispatch workerֱ�Ӻ�proxy workerͨ�š�
# 
import sys, os
import logging, signal
from netutils import *
from miscutils import *
from myshm import *

def process_f_msg(msg, poll):
    msg_data = msg[1]
    x = msg_data[:2]
    if x in submsg_process_map:
        submsg_process_map[x](msg, poll)
    else:
        logging.error('BUG: unknown msg from main process(%s): %s', x, msg)

def process_f_PW_msg(msg, poll):
    msg_data, fid = msg[1], msg[2][0]
    pid = msg_data[2:].decode('utf8')
    pid = int(pid)
    pobj = proxy_worker_process(pid)
    pobj.ep = uds_ep(socket.fromfd(fid, socket.AF_UNIX, socket.SOCK_STREAM))
    os.close(fid)
    proxy_worker_pobj_list.append(pobj)
    poll.register(pobj, poll.POLLIN) # ���POLLIN�����ڷ��ֶԶ˹ر����ӡ�

def process_f_FE_msg(msg, poll):
    msg_data, fid = msg[1], msg[2][0]
    startup_msg_raw = msg_data[2:]

msg_process_map = {
    b'f' : process_f_msg, 
}
submsg_process_map = {
    b'PW' : process_f_PW_msg, 
    b'FE' : process_f_FE_msg, 
}

def dispatch_worker(ipc_uds_path):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    # �Ƚ����������̵�����
    ipc_ep = connect_to_main_process(ipc_uds_path, 'dispatch')
    
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
            elif type(fobj) == proxy_worker_process:
                pass
            else:
                logging.error('BUG: unknown fobj: %s', fobj)
        # ������յ�����Ϣ
        for msg in msg_list:
            msg_type = msg[0]
            logging.info('[dispatch_worker]recved msg: %s', msg)
            if msg_type in msg_process_map:
                msg_process_map[msg_type](msg, poll)
            else:
                logging.error('BUG: unknown msg from main process: %s', msg)
    os._exit(0)

# main
g_conf = None
proxy_worker_pobj_list = []

if __name__ == '__main__':
    pass

