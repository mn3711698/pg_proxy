#!/bin/env python3
# -*- coding: GBK -*-
# 
import sys, os

all = {
    'listen' : ('', 7777), 
    # admin_cnn���ڻ��hba/shadows���Լ��л�ʱ���ӵ��ӿ�ʱ�õģ���Ҫ�����û�Ȩ�ޡ�
    # pg_hba.conf�в�Ҫ�����ӳ����ڵ�host����trust����Ϊǰ�˵�һ�����ӵ�ʱ�����ɺ��auth�ģ���ʱ��˿�����host�����ӳص�host��
    'admin_cnn' : {'user':'zhb', 'password':''}, 
    'lo_oid' : 9999, 
    # ���ӿ���Ϣ
    'master' : ('127.0.0.1', 5432), 
    'slaver' : [('10.10.77.100', 5432), ], 
    'conn_params' : [
        {'database':'postgres', 'user':'zhb', 'client_encoding':'GBK', 'application_name':'psql'}, 
        {'database':'postgres', 'user':'user1', 'password':'123456', 'client_encoding':'GBK', 'application_name':'psql'}, 
    ], 
}
if 'host' not in all['admin_cnn']:
    all['admin_cnn']['host'] = all['master'][0]
    all['admin_cnn']['port'] = all['master'][1]
