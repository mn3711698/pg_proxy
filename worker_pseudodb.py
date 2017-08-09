#!/bin/env python3
# -*- coding: GBK -*-
# 
# pseudo db worker���̣����ڴ���α���ݿ�pg_proxy��
# α���ݿ����Ϣ����proxy worker��pgmonitor worker�Ĺ����ڴ档
# 
import sys, os
import logging
from pgprotocol import *
from netutils import *
from miscutils import *
from myshm import *

def pseudodb_worker(ipc_uds_path):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    # �Ƚ����������̵�����
    ipc_ep = connect_to_main_process(ipc_uds_path, 'pseudodb')
    
    poll = spoller()
    poll.register(ipc_ep, poll.POLLIN)
    while True:
        x = poll.poll()
        for fobj, event in x:
            pass
    os._exit(0)

# main
g_conf = None
if __name__ == '__main__':
    pass

