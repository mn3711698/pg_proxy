#!/bin/env python3
# -*- coding: GBK -*-
# 
# proxy worker���̡��������ӳء�
# 
# �����̻�Ϊÿ��proxy worker����һ�鹲���ڴ棬������<proxy_shm_name>.<n>������proxy_shm_name�����������ļ������ã�ȱʡ�Ƕ˿ںš�
# ÿ�鹲���ڴ��Ϊ3���֣�
#   1) ��ͷ��16���ֽڰ���proxy worker��pid��������\x00��䡣��part_idx=-1ȥ���ʡ�
#   2) ��ϣ�����ڼ�¼��startup_msg_raw+be_addr��Ӧ�Ŀ���fe_be_pair����ϣ���е���ֵ��md5(startup_msg_raw+be_addr)+<2�ֽڵĿ���������>��
#      ��ֵ�Ĵ�С��18���ֽڡ�����1*PAGE_SIZE����������ͷ��16���ֽڣ����Ա���226���part_idx=0ȥ���ʡ�
#   3) 
# 
import sys, os

def proxy_worker(ipc_uds_path):
    pass

# main
g_conf = None
if __name__ == '__main__':
    pass

