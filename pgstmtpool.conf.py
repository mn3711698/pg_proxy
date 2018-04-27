#!/bin/env python3
# -*- coding: GBK -*-
# 
import sys, os

# admin_cnn, master����ָ����
# ����pseudo_cnn/user_pwds����������û���auth������md5����ô����Ҫָ�����롣
# admin_cnn����ָ�����룬����û���auth������md5����ô������pg_shadow�е�md5��ͷ���Ǹ����룬����������������롣
all = {
    'listen' : ('', 7777), 
    # pseudo_cnn���������ӳ�֮��ͨ��ʱ�õ����Ӳ���(����ָ��host/port/database)�����û��ָ����ʹ��admin_cnn��
    'pseudo_cnn' : {'user':'zhb', 'password':''}, 
    # admin_cnn���ڻ��hba/shadows���Լ��л�ʱ���ӵ��ӿ�ʱ�õģ���Ҫ�����û�Ȩ�ޡ�
    # pg_hba.conf�в�Ҫ�����ӳ����ڵ�host����trust����Ϊǰ�˵�һ�����ӵ�ʱ�����ɺ��auth�ģ���ʱ��˿�����host�����ӳص�host��
    'admin_cnn' : {'user':'zhb', 'password':''}, 
    'enable_ha' : True, 
    'ha_after_fail_cnt' : 10, 
    'ha_check_interval' : 3, 
    'lo_oid' : 9999, 
    'trigger_file' : 'trigger', 
    # cache
    'cache_threshold_to_file' : 10*1024, 
    'cache_root_dir' : 'querycache', 
    # ���ӿ���Ϣ
    # worker_min_cnt�е�idx��ֵ��ʾ����idx+1��ǰ������ʱ��Ҫ��worker����worker_per_fe_cnt��ʾÿ���ٸ�ǰ��������Ҫһ��������ӡ�
    'worker_min_cnt' : [1]*2 + [2]*4 + [3]*4, 
    'worker_per_fe_cnt' : 10, 
    'idle_timeout' : 60*60*24, 
    'master' : ('127.0.0.1', 5432), 
    'slaver' : [('127.0.0.1', 5433),], 
    # user_pwds�����û����룬�ӿ�worker����Щ�������ӵ��ӿ⡣����û���auth������md5����Ҫָ����
    # ���auth������password/scram-sha256�����ָ�����룬�����trust�����ָ������ֵ��
    # �����ָ��Ҳ����md5 auth����ô���������ӿ�worker��
    'user_pwds' : {
        'user2' : '123456', 
    }, 
}
