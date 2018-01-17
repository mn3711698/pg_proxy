#!/bin/env python3
# -*- coding: GBK -*-
# 
import sys, os

# admin_cnn, master����ָ����
# conn_params�Ǹ��б��б��е�Ԫ�������Ӳ���(������host��port)����ǰ�˺�����һ��ƥ���ʱ��Ż�����slaver worker��
all = {
    'listen' : ('', 7777), 
    # pseudo_cnn���������ӳ�֮��ͨ��ʱ�õ����Ӳ���(����ָ��host/port/database)�����û��ָ����ʹ��admin_cnn��
    'pseudo_cnn' : {'user':'zhb', 'password':''}, 
    # admin_cnn���ڻ��hba/shadows���Լ��л�ʱ���ӵ��ӿ�ʱ�õģ���Ҫ�����û�Ȩ�ޡ�
    # pg_hba.conf�в�Ҫ�����ӳ����ڵ�host����trust����Ϊǰ�˵�һ�����ӵ�ʱ�����ɺ��auth�ģ���ʱ��˿�����host�����ӳص�host��
    'admin_cnn' : {'user':'zhb', 'password':''}, 
    'enable_ha' : True, 
    'ha_after_fail_cnt' : 10, 
    'lo_oid' : 9999, 
    'trigger_file' : 'trigger', 
    # ���ӿ���Ϣ
    # worker_min_cnt�е�idx��ֵ��ʾ����idx+1��ǰ������ʱ��Ҫ��worker����worker_per_fe_cnt��ʾÿ���ٸ�ǰ��������Ҫһ��������ӡ�
    'worker_min_cnt' : [1]*2 + [2]*4 + [3]*4, 
    'worker_per_fe_cnt' : 10, 
    'master' : ('127.0.0.1', 5432), 
    'slaver' : [('127.0.0.1', 5433),], 
    'conn_params' : [
        {'database':'postgres', 'user':'zhb'}, 
        {'database':'postgres', 'user':'zhb', 'client_encoding':'GBK', 'application_name':'psql'}, 
        {'database':'postgres', 'user':'user1', 'client_encoding':'GBK', 'application_name':'psql', 'password':'123456'}, 
    ], 
}
