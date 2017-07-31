#!/bin/evn python3
# -*- coding: GBK -*-
# 
# pg_proxy.py [conf_file]
#   �����ļ�conf_file�Ǹ�python�ļ���������һ��dict����pg_proxy_conf�����ֵ����������Щ�
# 
#   'listen' : (host, port)                               ָ��������ip�Ͷ˿ڡ�
#   'master' : (host, port)                               ָ�������ַ��
#   'conninfo' : {'name':value, ...}                      ָ���������ӵ�master��promote���û���/���ݿ�/����ȣ������ǳ����û���
#                                                         ����ָ����name�У�user/pw/db/conn_retry_num/conn_retry_interval/query_interval/lo_oid��user����ָ����
#   'promote' : (host, port)                              ָ����������Ϊ����Ĵӿ�ĵ�ַ��
#   'slaver_list' : [(host, port), ...]                   ָ������ֻ�����ӵĴӿ��б�
#   'idle_cnn_timeout' : 300                              ָ���������ӵ�lifetime����λ���롣
#   'active_cnn_timeout' : 300                            ָ������ӿ���ʱ�����ƣ��������ʱ�䳬ʱ����ô�ͶϿ�fe�����ӡ����Ϊ0�ǾͲ����ƿ���ʱ�䡣(Ŀǰ��֧����չ��ѯЭ��)
#   'recv_sz_per_poll' : 4                                ÿ��pollһ�������������ն������ݣ���λ��K��
#   'disable_conds_list' : [[(name, value), ...], ...]    ��active_cnn_timeout>0�������øò���ָ�������ƿ���ʱ������ӡ�����ָ����name��user/database�Լ��������Գ�����startup��Ϣ���е�������
#   'pg_proxy_pw' : 'pg2pg'                               ָ�����ӵ�α���ݿ�pg_proxy��ʱ����Ҫ�����롣
#   'log' : {'name' : value, ...}                         ָ��logging��ص����ã�����ָ�������У�filename, level��level������Ϊlogging.DEBUG/INFO/WARNING/ERROR��
#                                                         ��ָ��filename����stderr�����
#   ע��master/promote/slaver_list��֧��unix domain socket��listenҲ��֧��unix domain socket��
# 
# pg_proxy�����û���������ת����������ߴӿ⣬�û����������'@ro'�����Ӷ�ת�����ӿ⣬��roundrobin��ʽ��ѡ��ӿ⡣
# 
# ������down�������ָ����promote���ã���ô�ͻ��������Ϊ���⡣���ָ����promote����ôslaver_list�е�
# �ӿ�������ӵ�promote����ӿ⣬������ֱ�����ӵ�master�������������б��봴��һ��OIDΪ9999������Ϊ�յĴ����
# ������OID������lo_oid�����ã�ȱʡֵΪ9999���ô����������promote������trigger�ļ���
# ����ӿ��ϵ�recovery.conf�е�trigger_file��Ҫ��Ϊ'trigger_file'��
#
# ������psql���ӵ�α���ݿ�pg_proxy�鿴��ǰ״̬��ȱʡ������pg2pg���û������⡣����4����: connection/process/server/startupmsg��
# ֻ֧�ֵ����select��ѯ������process/server��֧�ֲ�ѯ��������ѡ��
# .) connection : ����ÿ��fe/be���ӶԵ���Ϣ����������ӺͿ������ӡ�
# .) process    : ����ÿ�����ӽ��̵�������Ϣ��
# .) server     : ����ÿ�����ݿ�server��������Ϣ��
# .) startupmsg : ����ÿ�����ӵ�startup��Ϣ�����Լ������Ƿ���С�
#
# pg_proxy.pyֻ֧��postgres version 3Э�飬��֧��SSL���ӣ���֤��������ֻ֧��trust/password/md5��������֤����û�в��ԡ�
# ������pg_hba.conf��ʱ����Ҫע�����ADDRESS���������pg_proxy.py���ڵķ�������IP��ַ��
# ������ò�Ҫ���ó�trust����������֪���û���/���ݿ�����˭�����Ե�¼���ݿ⡣
#
# pg_proxy.py��Ҫpython 3.3�����ϰ汾����֧��windows��ֻ֧��session��������ӳأ���֧������/��伶������ӳء�
# ��֧�ָ������ӣ��޸ļ��д������֧�֣������������Ӳ���֧�ֳع��ܣ�Ҳ����˵�����ƿͻ��˶Ͽ����Ӻ󣬵�be�˵�����ҲӦ�öϿ���
# 
# pg_proxy.py�Ľṹ���£�
# .) ����������ʱ����AF_UNIX socket(�����������̺��ӽ���֮��ͨ��)�Լ�AF_INET socket(��������pg�ͻ��˵�����)��
# .) Ȼ�󴴽�n�����ӳؽ���(P)���Լ�һ����������(W)���ڴ�������������(M)���������󣬱��緢��CancelRequest�������л�����ȵȡ�
# .) M��P֮��ͨ��UDS(unix domain socket)ͨ�ţ�����֮�����Ϣ�У�
#    .) M->P ���pending_fe_connection�Ѿ����յ�StartupMessage����ôM�������ļ��������Լ�StartupMessage���͸�P��P��ѡ������ǣ�P�еĿ��е�BE����
#       ��StartupMessage��pending_fe_connectionƥ�䣻�������P��û��ƥ������ӣ���ô��ѡ��������ٵ�P���ӿ��ѡ������roundrobin��ʽ��
#    .) P->M �����ӽ������߶Ͽ���ʱ��P���������Ϣ����M��
# .) M��W֮����Ҫ��M��W���͹���������Ϣ����ǰ�Ĺ���������Ϣ�У�����CancelRequest�������л������
# 
import sys, os, struct, socket, time, errno
import traceback
import signal
import sqlite3
import re, logging

from netutils import *
from miscutils import *
from pgprotocol import *
from pgmonitor import *

# 
# 
# �����̺��ӽ���֮��ͨ�ŵ���Ϣ���ͣ�
# 'f'���͵���Ϣ�������̷���proxy�ӽ��̵ģ���������ļ���������
# 's'���͵���Ϣ���ӽ�����������ʱ����Լ��Ľ��̺ŷ��������̡�
# 'c'���͵���Ϣ�������̰�CancelRequest�����������̡�
# 'C'���͵���Ϣ��proxy�ӽ��̷��������̵ģ��������ӳɹ���Ϣ��
# 'D'���͵���Ϣ��proxy�ӽ��̷��������̵ģ��������ӶϿ���Ϣ��
# 'P'���͵���Ϣ�������̷����ӽ��̵ģ��������ӿ��л������
# 
# ��ʾproxy�����е�fe_be_pair
class proxy_conn_info(object):  
    def __init__(self, pair_id, fe_ip, fe_port, be_ip, be_port, startup_msg_raw, status_time, use_num):
        self.pair_id = pair_id
        
        self.fe_ip = fe_ip
        self.fe_port = fe_port
        self.be_ip = be_ip
        self.be_port = be_port
        
        self.startup_msg_raw = startup_msg_raw
        self.startup_msg = process_Startup(startup_msg_raw[4:])
        self.status_time = status_time
        self.use_num = use_num
    def fe_disconnected(self, status_time):
        self.fe_ip = ''
        self.fe_port = 0
        self.status_time = status_time
    def update(self, fe_ip, fe_port, status_time, use_num):
        self.fe_ip = fe_ip
        self.fe_port = fe_port
        self.status_time = status_time
        self.use_num = use_num
    
class worker_process_base(object):
    def __init__(self, pid, idx):
        self.pid = pid
        self.idx = idx
        self.ep = None # ���ӽ��̵�socket���ӡ��ӽ���������ʱ�����ӵ������̵�UDS(unix domain socket)��
    def fileno(self):
        return self.ep.fileno()
    def close(self):
        if self.ep:
            self.ep.close()
            self.ep = None
    def is_connected(self):
        return self.ep != None
    def put_msg(self, msg_type, msg_data, fdlist = None):
        logging.debug('[%d]put_msg: %s %s %s', self.pid, msg_type, msg_data, fdlist)
        self.ep.put_msg(msg_type, msg_data, fdlist)
    def fd_is_sent(self, fd):
        return self.ep.fd_is_sent(fd)
class proxy_worker_process(worker_process_base):
    def __init__(self, pid, idx):
        super().__init__(pid, idx)
        self.proxy_conn_info_map = {} # pair_id -> proxy_conn_info  ��������
        self.startup_msg_raw_to_conn_map = {} # startup_msg_raw -> idle_cnn_num   ����������
        self.pending_cnn_num = 0 # �Ѿ����͸�proxy���̵���û�л�Ӧ'C'/'D'��Ϣ��������������
        self.closing_fe_cnn_list = []
    def close(self):
        super().close()
        for cnn in self.closing_fe_cnn_list:
            cnn.close()
        self.closing_fe_cnn_list.clear()
    def add_closing_fe_cnn(self, fe_cnn):
        self.closing_fe_cnn_list.append(fe_cnn)
    def close_fe_cnn(self):
        del_cnns = []
        for cnn in self.closing_fe_cnn_list:
            if self.fd_is_sent(cnn.fileno()):
                cnn.close()
                del_cnns.append(cnn)
        for cnn in del_cnns:
            self.closing_fe_cnn_list.remove(cnn)
        del_cnns.clear()
    def has_matched_idle_conn(self, startup_msg_raw, be_addr):
        if (startup_msg_raw not in self.startup_msg_raw_to_conn_map) or \
           (self.startup_msg_raw_to_conn_map[startup_msg_raw] <= 0):
            return False
        for id in self.proxy_conn_info_map:
            ci = self.proxy_conn_info_map[id]
            if ci.startup_msg_raw == startup_msg_raw and be_addr == (ci.be_ip, ci.be_port):
                return True
        return False
    def remove_idle_conn(self, startup_msg_raw):
        self.startup_msg_raw_to_conn_map[startup_msg_raw] -= 1
    def get_active_cnn_num(self):
        return self.get_total_cnn_num() - self.get_idle_cnn_num() + (self.pending_cnn_num if self.pending_cnn_num > 0 else 0)
    def get_total_cnn_num(self):
        return len(self.proxy_conn_info_map)
    def get_idle_cnn_num(self):
        num = 0
        for k in self.startup_msg_raw_to_conn_map:
            num += self.startup_msg_raw_to_conn_map[k]
        return num
    def get_pending_cnn_num(self):
        return self.pending_cnn_num
    # 
    def handle_event(self, poll, event):
        if event & poll.POLLOUT:
            x = self.ep.send()
            if x == None:
                logging.debug('[proxy_worker_process][%d]send done', self.pid)
                poll.register(self, poll.POLLIN)
        if event & poll.POLLIN:
            x = self.ep.recv()
            if x[0] != -1:
                return
            logging.debug('[proxy_worker_process][%d]recv: %s', self.pid, x[1])
            msg = x[1]
            msg_data = msg[1]
            msg_len = struct.unpack('>i', msg_data[:4])[0]
            sub_data = msg_data[4:msg_len]
            if msg[0] == b'C': # b'C'��Ϣ���ݸ�ʽ��len + pair_id;ip,port;ip,port;time;use_num;main_use_idle_cnn;proxy_use_idle_cnn + startup_msg_raw��len������startup_msg_raw��
                sub_data = sub_data.decode('latin1')
                startup_msg_raw = msg_data[msg_len:]
                pair_id, fe_addr, be_addr, status_time, use_num, main_use_idle_cnn, proxy_use_idle_cnn = sub_data.split(';')
                pair_id = int(pair_id)
                fe_ip, fe_port = fe_addr.split(',')
                fe_port = int(fe_port)
                be_ip, be_port = be_addr.split(',')
                be_port = int(be_port)
                status_time = int(status_time)
                use_num = int(use_num)
                main_use_idle_cnn = int(main_use_idle_cnn)
                proxy_use_idle_cnn = int(proxy_use_idle_cnn)
                
                logging.debug('(main_use_idle_cnn, proxy_use_idle_cnn) = (%d, %d)', main_use_idle_cnn, proxy_use_idle_cnn)
                conn_info = self.proxy_conn_info_map.get(pair_id, None)
                if not conn_info: # ȫ�µ�fe_be_pair
                    conn_info = proxy_conn_info(pair_id, fe_ip, fe_port, be_ip, be_port, startup_msg_raw, status_time, use_num)
                    self.proxy_conn_info_map[pair_id] = conn_info
                else: # ���õ�fe_be_pair
                    # TODO: ���conn_info�е���Ϣ�Ƿ�����Ϣ�е�һ��
                    # ֻ��Ҫ����3����������ġ�
                    conn_info.update(fe_ip, fe_port, status_time, use_num)
                
                if main_use_idle_cnn == 0:
                    self.pending_cnn_num -= 1
                if startup_msg_raw not in self.startup_msg_raw_to_conn_map:
                    self.startup_msg_raw_to_conn_map[startup_msg_raw] = 0
                self.startup_msg_raw_to_conn_map[startup_msg_raw] += main_use_idle_cnn - proxy_use_idle_cnn
            elif msg[0] == b'D': # b'D'��Ϣ���ݸ�ʽ��len + pair_id;1/0;time;main_use_idle_cnn;proxy_use_idle_cnn + startup_msg_raw��1��ʾ��ȫ�Ͽ���0��ʾֻ��s_fe�Ͽ���len������startup_msg_raw��
                sub_data = sub_data.decode('latin1')
                startup_msg_raw = msg_data[msg_len:]
                pair_id, is_complete_disconn, status_time, main_use_idle_cnn, proxy_use_idle_cnn = (int(x) for x in sub_data.split(';'))
                
                if startup_msg_raw not in self.startup_msg_raw_to_conn_map:
                    self.startup_msg_raw_to_conn_map[startup_msg_raw] = 0
                logging.debug('(main_use_idle_cnn, proxy_use_idle_cnn) = (%d, %d)', main_use_idle_cnn, proxy_use_idle_cnn)
                conn_info = self.proxy_conn_info_map.get(pair_id, None)
                if not conn_info: # ȫ�µ�fe_be_pair��֮ǰû�з���'C'��Ϣ��
                    self.startup_msg_raw_to_conn_map[startup_msg_raw] += main_use_idle_cnn - proxy_use_idle_cnn
                    if main_use_idle_cnn == 0:
                        self.pending_cnn_num -= 1
                    logging.debug('can not find proxy_conn_info for pair_id(%d)', pair_id)
                    return
                # TODO:���conn_info�е���Ϣ�Ƿ�����Ϣ�е�һ��
                if is_complete_disconn: # ȫ�µ�fe_be_pair��֮ǰ���͹�'C'��Ϣ������ ���е�fe_be_pair
                    self.proxy_conn_info_map.pop(pair_id)
                    if not conn_info.fe_ip: # ���е�fe_be_pair
                        if self.startup_msg_raw_to_conn_map[startup_msg_raw] <= 0:
                            logging.error('BUG: idle_cnn_num <= 0: %d', conn_info.pair_id)
                        self.startup_msg_raw_to_conn_map[startup_msg_raw] -= 1
                else: # ȫ�µ�fe_be_pair��֮ǰ���͹�'C'��Ϣ������ ���õ�fe_be_pair
                    conn_info.fe_disconnected(status_time)
                    self.startup_msg_raw_to_conn_map[startup_msg_raw] += 1
                    if not conn_info.fe_ip:
                        if main_use_idle_cnn == 0:
                            self.pending_cnn_num -= 1
                        self.startup_msg_raw_to_conn_map[startup_msg_raw] += main_use_idle_cnn - proxy_use_idle_cnn
                
class work_worker_process(worker_process_base):
    def handle_event(self, poll, event):
        if event & poll.POLLOUT:
            x = self.ep.send()
            if x == None:
                logging.debug('[work_worker_process][%d]send done', self.pid)
                poll.register(self, poll.POLLIN)
        if event & poll.POLLIN:
            x = self.ep.recv()
            if x[0] == -1:
                logging.debug('[work_worker_process][%d]recv: %s', self.pid, x[1])

class fe_disconnected_exception(Exception): pass
class be_disconnected_exception(Exception): pass
class fe_be_pair(object):
    next_pair_id = 0
    recv_sz_per_poll = 4
    oldest_ready_for_query_recved_time = time.time()
    def __init__(self, ep, enable_active_cnn_timeout = True):
        self.ep_to_main = ep
        self.s_fe = None
        self.s_be = None
        self.startup_msg = None
        self.startup_msg_raw = None
        
        self.first_ready_for_query_recved = False
        self.auth_msg_seq = [] # auth������FE<->BE֮�佻������Ϣ���С���(FE/BE, msg)�б�
        self.auth_msg_idx = 0
        self.auth_simulate = False
        self.auth_simulate_failed = False
        self.discard_all_command_complete_recved = False
        self.discard_all_ready_for_query_recved = False
        
        self.s_fe_buf1 = b''
        self.s_fe_msglist = []
        self.s_fe_buf2 = b''
        self.s_be_buf1 = b''
        self.s_be_msglist = []
        self.s_be_buf2 = b''
        
        self.id = fe_be_pair.next_pair_id
        fe_be_pair.next_pair_id += 1
        self.status_time = time.time()
        self.use_num = 1;
        
        self.main_use_idle_cnn = 0
        self.proxy_use_idle_cnn = 0
        
        self.enable_active_cnn_timeout = enable_active_cnn_timeout
        self.query_recved_time = time.time()
        self.ready_for_query_recved_time = time.time()
    # ����True��ʾfe/be���Ѿ��رգ�����False��ʾֻ��fe�رգ���pair���ɸ��á�
    # ��������������close�������/��������/authģ������
    def close(self, poll, ex, fe_be_to_pair_map):
        if self.s_fe:
            poll.unregister(self.s_fe)
            fe_be_to_pair_map.pop(self.s_fe)
            self.s_fe.close()
        if not self.auth_simulate:
            poll.unregister(self.s_be)
        fe_be_to_pair_map.pop(self.s_be)
        
        if type(ex) == be_disconnected_exception or not self.first_ready_for_query_recved:
            self.s_be.close()
            # �������̷�����Ϣ
            self.send_disconnect_msg_to_main(poll, True)
            return True
        else:
            self.s_fe = None
            self.auth_msg_idx = 0
            
            if not self.auth_simulate:
                self.s_be_buf1 = self.s_fe_buf1
                self.s_fe_buf1 = b''
            else:
                self.s_be_buf1 = b''
                self.s_fe_buf1 = b''
            self.s_fe_msg_list = []
            self.s_fe_buf2 = b''
            # ��BE����abort��discard all���
            self.s_be_msglist = []
            if not self.auth_simulate:
                self.s_be_buf2 += make_Query2(b'abort')
                self.s_be_buf2 += make_Query2(b'discard all')
            if self.s_be_buf2:
                poll.register(self.s_be, poll.POLLOUT|poll.POLLIN)
            else:
                poll.register(self.s_be, poll.POLLIN)
            fe_be_to_pair_map[self.s_be] = self
            self.auth_simulate = False
            # �������̷�����Ϣ
            self.send_disconnect_msg_to_main(poll, False)
            return False
    # startup_msg_raw������ͷ�Ǳ�ʾ��Ϣ���ȵ�4���ֽ�
    # ������be���µ�����
    def start(self, poll, fe_be_to_pair_map, be_addr, startup_msg, fd):
        self.s_fe = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        os.close(fd)
        self.s_fe.settimeout(0)
        
        self.startup_msg = startup_msg
        self.startup_msg_raw = make_StartupMessage1(self.startup_msg)
        self.s_be = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_be.settimeout(0)
        ret = self.s_be.connect_ex(be_addr)
        if ret not in NONBLOCK_CONNECT_EX_OK:
            self.s_fe.close()
            raise RuntimeError('connect_ex fail:%s' % (os.strerror(ret), ))
        logging.debug('[FE] %s', self.startup_msg)
        self.s_be_buf2 = self.startup_msg_raw
        
        poll.register(self.s_be, poll.POLLOUT|poll.POLLIN)
        poll.register(self.s_fe, poll.POLLIN)
        fe_be_to_pair_map[self.s_fe] = self
        fe_be_to_pair_map[self.s_be] = self
        
        if self.enable_active_cnn_timeout:
            self.query_recved_time = self.ready_for_query_recved_time = time.time()
    # ����be����
    def start2(self, poll, fe_be_to_pair_map, be_addr, startup_msg, fd):
        self.auth_msg_idx = 0
        self.auth_simulate = True
        self.auth_simulate_failed = False
        poll.unregister(self.s_be)
        
        self.s_fe = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        os.close(fd)
        self.s_fe.settimeout(0)
        
        logging.debug('start auth_simulate: %s %s %s %s', self.auth_msg_idx, self.s_fe_buf1, self.s_fe_msglist, self.s_fe_buf2)
        logging.debug('[FE] %s', startup_msg)
        while True:
            if self.auth_msg_idx >= len(self.auth_msg_seq):
                break
            x = self.auth_msg_seq[self.auth_msg_idx]
            if x[0] == 'BE':
                logging.debug('[BE] %s', x[1])
                self.s_fe_buf2 += make_Msg1(x[1])
                self.auth_msg_idx += 1
            else:
                break
        poll.register(self.s_fe, poll.POLLIN|poll.POLLOUT)
        fe_be_to_pair_map[self.s_fe] = self
        fe_be_to_pair_map[self.s_be] = self
        
        if self.enable_active_cnn_timeout:
            self.query_recved_time = self.ready_for_query_recved_time = time.time()
    def handle_event(self, poll, fobj, event):
        s_str = ('s_fe' if fobj==self.s_fe else 's_be')
        # recv
        if event & poll.POLLIN:
            try:
                data = myrecv(fobj, 1024*self.recv_sz_per_poll)
                if data == None:
                    return
                if not data:
                    raise RuntimeError("the %s's peer (%s) closed the connection" % (s_str, fobj.getpeername()))
            except (OSError, RuntimeError) as ex:
                logging.info('[%s]Exception: %s', s_str, str(ex))
                if fobj == self.s_fe:
                    raise fe_disconnected_exception()
                else:
                    raise be_disconnected_exception()
            if fobj == self.s_fe:
                self.s_be_buf1 += data
                ret = parse_fe_msg(self.s_be_buf1)
                self.s_be_msglist.extend(ret[1])
                self.s_be_buf1 = self.s_be_buf1[ret[0]:]
                
                if self.s_be_msglist: logging.debug('')
                for msg in self.s_be_msglist:
                    logging.debug('[FE] %s', msg)
                    if msg[0] == 'Terminate':
                        raise fe_disconnected_exception()
                    self.s_be_buf2 += make_Msg1(msg, is_from_be = False)
                    if self.enable_active_cnn_timeout:
                        self.query_recved_time = time.time()
                    if not self.first_ready_for_query_recved:
                        self.auth_msg_seq.append(('FE', msg))
                self.s_be_msglist = []
            else: # s_be
                self.s_fe_buf1 += data
                ret = parse_be_msg(self.s_fe_buf1)
                self.s_fe_msglist.extend(ret[1])
                self.s_fe_buf1 = self.s_be_buf1[ret[0]:]
                
                for msg in self.s_fe_msglist:
                    logging.debug('[BE] %s', msg)
                    self.s_fe_buf2 += make_Msg1(msg, is_from_be = True)
                    if self.enable_active_cnn_timeout and msg[0] == 'ReadyForQuery':
                        self.ready_for_query_recved_time = time.time()
                        self.query_recved_time = 0
                    if not self.first_ready_for_query_recved:
                        self.auth_msg_seq.append(('BE', msg))
                        if msg[0] == 'ReadyForQuery': 
                            self.first_ready_for_query_recved = True
                            # ��½��ɣ���Ҫ�������̷�����Ϣ��
                            self.send_connect_msg_to_main(poll, True)
                self.s_fe_msglist = []
        # send
        if event & poll.POLLOUT:
            try:
                if fobj == self.s_fe:
                    n = fobj.send(self.s_fe_buf2)
                    self.s_fe_buf2 = self.s_fe_buf2[n:]
                else:
                    n = fobj.send(self.s_be_buf2)
                    self.s_be_buf2 = self.s_be_buf2[n:]
            except OSError as ex:
                logging.info('[%s]Exception: %s', s_str, str(ex))
                if fobj == self.s_fe:
                    raise fe_disconnected_exception()
                else:
                    raise be_disconnected_exception()
        # register eventmask
        if self.s_fe_buf2:
            poll.register(self.s_fe, poll.POLLOUT|poll.POLLIN)
        else:
            poll.register(self.s_fe, poll.POLLIN)
        if self.s_be_buf2:
            poll.register(self.s_be, poll.POLLOUT|poll.POLLIN)
        else:
            poll.register(self.s_be, poll.POLLIN)
    # ����pair���¼�����
    def handle_event2(self, poll, fobj, event):
        if fobj != self.s_be:
            raise SystemError('BUG: handle_event2 fobj != self.s_be (%s, %s)' % (fobj, self.s_be))
        if event & poll.POLLIN:
            try:
                data = myrecv(self.s_be, 1024*4)
                if data == None:
                    return
                if not data:
                    raise RuntimeError("the s_be's peer (%s) closed the connection" % (fobj.getpeername(), ))
            except (OSError, RuntimeError) as ex:
                logging.info('[s_be]Exception: %s', str(ex))
                raise be_disconnected_exception()
            # ����Ƿ���յ�discard all�������Ӧ��
            self.s_be_buf1 += data
            ret = parse_be_msg(self.s_be_buf1)
            self.s_be_msglist.extend(ret[1])
            self.s_be_buf1 = self.s_be_buf1[ret[0]:]
            for msg in self.s_be_msglist:
                logging.debug('[idle fe_be_pair] recved: %s', msg)
                if msg[0] == 'CommandComplete' and msg[2] == b'DISCARD ALL\x00':
                    self.discard_all_command_complete_recved = True
                    self.discard_all_ready_for_query_recved = False
                elif msg[0] == 'ReadyForQuery':
                    self.discard_all_ready_for_query_recved = True
            self.s_be_msglist = []
        if event & poll.POLLOUT:
            try:
                n = self.s_be.send(self.s_be_buf2)
                self.s_be_buf2 = self.s_be_buf2[n:]
            except OSError as ex:
                logging.info('[%s]Exception: %s', s_str, str(ex))
                raise be_disconnected_exception()
            if not self.s_be_buf2:
                poll.register(self.s_be, poll.POLLIN)
    # authģ������е��¼�����ֻ��s_fe���¼���û��s_be�ġ�
    def handle_event_simulate(self, poll, fobj, event):
        if fobj != self.s_fe:
            raise SystemError('BUG: handle_event_simulate fobj != self.s_fe (%s %s)' % (fobj, self.s_fe))
        if event & poll.POLLIN:
            try:
                data = myrecv(self.s_fe, 1024*4)
                if data == None:
                    return
                if not data:
                    raise RuntimeError("the s_fe's peer (%s) closed the connection" % (fobj.getpeername(), ))
            except (OSError, RuntimeError) as ex:
                logging.info('[s_fe]Exception: %s', str(ex))
                raise fe_disconnected_exception()
            self.s_fe_buf1 += data
            ret = parse_fe_msg(self.s_fe_buf1)
            self.s_fe_msglist.extend(ret[1])
            self.s_fe_buf1 = self.s_fe_buf1[ret[0]:]
            for msg in self.s_fe_msglist:
                msg2 = self.auth_msg_seq[self.auth_msg_idx][1]
                logging.debug('[FE] %s <-> %s', msg, msg2)
                if msg != msg2:
                    self.auth_simulate_failed = True
                    logging.info('unmatched msg from FE: msg(%s) != msg2(%s)', msg, msg2)
                    if msg[0] == 'PasswordMessage' and msg2[0] == 'PasswordMessage':
                        self.s_fe_buf2 += make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'28P01'), (b'M', b'invalid password')])
                    break
                else:
                    self.auth_msg_idx += 1
            if not self.auth_simulate_failed:
                # ƥ��ɹ�����FE��������BE����Ϣ��
                logging.debug('match %d msg from FE. ', len(self.s_fe_msglist))
                while True:
                    if self.auth_msg_idx >= len(self.auth_msg_seq):
                        break
                    x = self.auth_msg_seq[self.auth_msg_idx]
                    if x[0] == 'BE':
                        logging.debug('[BE] %s', x[1])
                        self.s_fe_buf2 += make_Msg1(x[1])
                        self.auth_msg_idx += 1
                    else:
                        break
            self.s_fe_msglist = []
        if event & poll.POLLOUT:
            try:
                n = self.s_fe.send(self.s_fe_buf2)
            except (OSError, RuntimeError) as ex:
                logging.info('[s_fe]Exception: %s', str(ex))
                raise fe_disconnected_exception()
            self.s_fe_buf2 = self.s_fe_buf2[n:]
            if self.s_fe_buf2:
                return
            if self.auth_simulate_failed:
                raise fe_disconnected_exception()
            if self.auth_msg_idx >= len(self.auth_msg_seq):
                logging.debug('auth_simulate done: fe:(%s %s %s) be:(%s %s %s)', 
                              self.s_fe_buf1, self.s_fe_msg_list, self.s_fe_buf2, self.s_be_buf1, self.s_be_msglist, self.s_be_buf2)
                self.auth_simulate = False
                self.discard_all_command_complete_recved = False
                self.discard_all_ready_for_query_recved = False
                self.use_num += 1
                
                poll.register(self.s_fe, poll.POLLIN)
                poll.register(self.s_be, poll.POLLIN)
                # ��½��ɣ���Ҫ�������̷�����Ϣ��
                self.send_connect_msg_to_main(poll, False)
                
                if self.enable_active_cnn_timeout:
                    self.ready_for_query_recved_time = time.time()
                    self.query_recved_time = 0
    # b'C'��Ϣ���ݸ�ʽ��len + pair_id;ip,port;ip,port;time;use_num;main_use_idle_cnn;proxy_use_idle_cnn + startup_msg_raw��len������startup_msg_raw��
    def send_connect_msg_to_main(self, poll, is_new):
        self.status_time = time.time()
        addr = self.s_fe.getpeername()
        msg_data = '%d' % self.id
        msg_data += ';%s,%d' % (addr[0], addr[1])
        addr = self.s_be.getpeername()
        msg_data += ';%s,%d' % (addr[0], addr[1])
        msg_data += ';%d;%d;%d;%d' % (self.status_time, self.use_num, self.main_use_idle_cnn, self.proxy_use_idle_cnn)
        
        msg_data = msg_data.encode('latin1')
        msg_data = struct.pack('>i', len(msg_data)+4) + msg_data
        msg_data += self.startup_msg_raw
        self.ep_to_main.put_msg(b'C', msg_data, [])
        poll.register(self.ep_to_main, poll.POLLIN|poll.POLLOUT)
        self.main_use_idle_cnn = -1
        self.proxy_use_idle_cnn = -1
    # b'D'��Ϣ���ݸ�ʽ��len + pair_id;1/0;time;main_use_idle_cnn;proxy_use_idle_cnn + startup_msg_raw��1��ʾ��ȫ�Ͽ���0��ʾֻ��s_fe�Ͽ���len������startup_msg_raw��
    def send_disconnect_msg_to_main(self, poll, is_complete_disconn):
        self.status_time = time.time()
        if is_complete_disconn:
            msg_data = '%d;1;%d' % (self.id, self.status_time)
        else:
            msg_data = '%d;0;%d' % (self.id, self.status_time)
        msg_data += ';%d;%d' % (self.main_use_idle_cnn, self.proxy_use_idle_cnn)
        
        msg_data = msg_data.encode('latin1')
        msg_data = struct.pack('>i', len(msg_data)+4) + msg_data
        msg_data += self.startup_msg_raw
        self.ep_to_main.put_msg(b'D', msg_data, [])
        poll.register(self.ep_to_main, poll.POLLIN|poll.POLLOUT)
        self.main_use_idle_cnn = -1
        self.proxy_use_idle_cnn = -1
# 
# �ҵ����õ�ƥ���idle pair
# ����(pair, has_matched)
#   pair != None, has_matched = True     ��ƥ��Ŀ��õ�idle pair
#   pair = None,  has_matched = True     ��ƥ��ĵ���Ŀǰ�������ܵ�idle pair
#   pair = None,  has_matched = False    û��ƥ���idle pair
def find_matched_idle_pair(idle_pair_list, be_addr):
    pair = None
    has_matched = False
    if not idle_pair_list:
        return (pair, has_matched)
    for p in idle_pair_list:
        if not p.s_be:
            logging.info('[find_matched_idle_pair] p.s_be is None')
            continue
        if p.s_be.getpeername() != be_addr:
            continue
        has_matched = True
        if p.discard_all_command_complete_recved and p.discard_all_ready_for_query_recved:
            pair = p
            break
    return (pair, has_matched)
def proxy_worker(ipc_uds_path):
    # �Ƚ����������̵�����
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(ipc_uds_path)
    s.sendall(b's' + struct.pack('>ii', 8, os.getpid()))
    ipc_ep = uds_ep(s)
    
    poll = spoller()
    poll.register(ipc_ep, poll.POLLIN)
    fe_be_to_pair_map = {} # s_fe/s_be -> fe_be_pair
    startup_msg_raw_to_idle_pair_map = {} # �ɸ��õ�pair��startup_msg_raw -> [pair1, ...]
    idle_pair_map = {} # (startup_msg_raw, be_ip, be_port) -> [pair1, ...]
    msglist_from_main = []
    waiting_fmsg_list = [] # �ȴ������'f'��Ϣ�б�
    
    while True:
        x = poll.poll(0.1)
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
                    msg = x[1]
                    logging.debug('[proxy_worker] uds_ep recved: %s', msg)
                    msglist_from_main.append(msg) # ���������̵���Ϣ���¼�forѭ��֮�⴦��
            else: # fe or be
                pair = fe_be_to_pair_map.get(fobj, None)
                if not pair:
                    logging.debug('fe_be_pair had been removed')
                    continue
                try:
                    if pair.s_fe:
                        if pair.auth_simulate:
                            pair.handle_event_simulate(poll, fobj, event)
                        else:
                            pair.handle_event(poll, fobj, event)
                    else:
                        pair.handle_event2(poll, fobj, event)
                except (fe_disconnected_exception, be_disconnected_exception) as ex:
                    if pair.startup_msg_raw not in startup_msg_raw_to_idle_pair_map:
                        startup_msg_raw_to_idle_pair_map[pair.startup_msg_raw] = []
                    idle_pair_list = startup_msg_raw_to_idle_pair_map[pair.startup_msg_raw]
                    
                    if pair.close(poll, ex, fe_be_to_pair_map):
                        if pair in idle_pair_list:
                            idle_pair_list.remove(pair)
                    else:
                        idle_pair_list.append(pair)
        # �����fe_be_pair�Ƿ�ʱ
        if g_conf['active_cnn_timeout'] > 0:
            t = time.time()
            if t - fe_be_pair.oldest_ready_for_query_recved_time >= g_conf['active_cnn_timeout']: # g_conf is global var
                pair_set = set()
                for s in fe_be_to_pair_map:
                    pair = fe_be_to_pair_map[s]
                    if not pair.s_fe or not pair.enable_active_cnn_timeout or pair.query_recved_time > 0:
                        continue
                    pair_set.add(pair)
                oldest_time = time.time()
                for pair in pair_set:
                    if pair.startup_msg_raw not in startup_msg_raw_to_idle_pair_map:
                        startup_msg_raw_to_idle_pair_map[pair.startup_msg_raw] = []
                    idle_pair_list = startup_msg_raw_to_idle_pair_map[pair.startup_msg_raw]
                    if t - pair.ready_for_query_recved_time >= g_conf['active_cnn_timeout']:
                        logging.info('close s_fe in fe_be_pair because active_cnn_timeout: %d', pair.id)
                        pair.close(poll, fe_disconnected_exception(), fe_be_to_pair_map)
                        idle_pair_list.append(pair)
                    else:
                        if pair.ready_for_query_recved_time < oldest_time:
                            oldest_time = pair.ready_for_query_recved_time
                fe_be_pair.oldest_ready_for_query_recved_time = oldest_time
        # �������������̵���Ϣ
        for msg in msglist_from_main:
            if msg[0] == b'f': # len + ip,port,use_idle_cnn + startup_msg_raw��len������startup_msg_raw
                msg_len = struct.unpack('>i', msg[1][:4])[0]
                ip, port, use_idle_cnn = msg[1][4:msg_len].decode('latin1').split(',')
                addr = (ip, int(port))
                use_idle_cnn = int(use_idle_cnn)
                startup_msg_raw = msg[1][msg_len:]
                startup_msg = process_Startup(startup_msg_raw[4:])
                fd = msg[2][0]
                
                idle_pair_list = startup_msg_raw_to_idle_pair_map.get(startup_msg_raw, None)
                pair, has_matched = find_matched_idle_pair(idle_pair_list, addr)
                if has_matched:
                    if pair:
                        idle_pair_list.remove(pair)
                        pair.main_use_idle_cnn = use_idle_cnn
                        pair.proxy_use_idle_cnn = 1
                        pair.start2(poll, fe_be_to_pair_map, addr, startup_msg, fd)
                    else: # ���е�fe_be_pairĿǰ���������ã���Ҫ�ȴ���
                        waiting_fmsg_list.append((addr, startup_msg, fd, startup_msg_raw, use_idle_cnn))
                else:
                    if g_conf['active_cnn_timeout'] <= 0 or match_conds(startup_msg, addr, g_conf['disable_conds_list']): # g_conf is global var
                        pair = fe_be_pair(ipc_ep, False)
                    else:
                        pair = fe_be_pair(ipc_ep, True)
                    pair.main_use_idle_cnn = use_idle_cnn
                    pair.proxy_use_idle_cnn = 0
                    pair.start(poll, fe_be_to_pair_map, addr, startup_msg, fd)
            else:
                logging.error('unknown msg from main process: %s', msg)
        if msglist_from_main:
            msglist_from_main.clear()
        # ����waiting_fmsg_list
        del_list = []
        for msg in waiting_fmsg_list:
            addr = msg[0]
            startup_msg = msg[1]
            fd = msg[2]
            startup_msg_raw = msg[3]
            use_idle_cnn = msg[4]
            
            idle_pair_list = startup_msg_raw_to_idle_pair_map.get(startup_msg_raw, None)
            pair, has_matched = find_matched_idle_pair(idle_pair_list, addr)
            if has_matched:
                if pair:
                    idle_pair_list.remove(pair)
                    pair.main_use_idle_cnn = use_idle_cnn
                    pair.proxy_use_idle_cnn = 1
                    pair.start2(poll, fe_be_to_pair_map, addr, startup_msg, fd)
                    del_list.append(msg)
            else: # û��ƥ���idle pair, �����ϴμ���ʱ���ҵ�ƥ�䵫�������õ�pair�Ѿ�close���ˡ�
                if g_conf['active_cnn_timeout'] <= 0 or match_conds(startup_msg, addr, g_conf['disable_conds_list']): # g_conf is global var
                    pair = fe_be_pair(ipc_ep, False)
                else:
                    pair = fe_be_pair(ipc_ep, True)
                pair.main_use_idle_cnn = use_idle_cnn
                pair.proxy_use_idle_cnn = 0
                pair.start(poll, fe_be_to_pair_map, addr, startup_msg, fd)
                del_list.append(msg)
        for msg in del_list:
            waiting_fmsg_list.remove(msg)
        del_list = None
        # �رճ�ʱ�Ŀ���fe_be_pair
        t = time.time()
        for k in startup_msg_raw_to_idle_pair_map:
            close_list = []
            idle_pair_list = startup_msg_raw_to_idle_pair_map [k]
            for pair in idle_pair_list:
                if t - pair.status_time >= g_conf['idle_cnn_timeout']: # g_conf is global var
                    close_list.append(pair)
            for pair in close_list:
                logging.info('[proxy process] close idle fe_be_pair because idle_cnn_timeout:%d', pair.id)
                idle_pair_list.remove(pair)
                pair.close(poll, be_disconnected_exception(), fe_be_to_pair_map)
            close_list = None

# ��CancelRequest��Ϣmsg_raw������������дӿ�
def send_cancel_request(msg_raw):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(g_conf['master'])
        s.sendall(msg_raw)
        s.close()
    except Exception as ex:
        logging.warning('Exception: %s', str(ex))
    
    for slaver in g_conf['slaver_list']:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(slaver)
            s.sendall(msg_raw)
            s.close()
        except Exception as ex:
            logging.warning('Exception: %s', str(ex))
def process_promote_result(msg_data):
    if msg_data[0] == 'E':
        # ������Ҫ���ͱ����ʼ�
        logging.warning('promote fail:%s' % (msg_data[1:], ))
    else:
        addr_list = msg_data[1:].split(';')
        g_conf['master'] = (addr_list[0][0], int(addr_list[0][1]))
        s_list = []
        for addr in addr_list[1:]:
            s_list.append((addr[0], int(addr[1])))
        g_conf['slaver_list'] = s_list
def work_worker(ipc_uds_path):
    # �Ƚ����������̵�����
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(ipc_uds_path)
    s.sendall(b's' + struct.pack('>ii', 8, os.getpid()))
    ipc_ep = uds_ep(s)
    
    poll = spoller()
    poll.register(ipc_ep, poll.POLLIN)
    while True:
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
                    msg = x[1]
                    logging.debug('[work_worker] uds_ep recved: %s', msg)
                    if msg[0] == b'c': # CancelRequest��Ϣ
                        send_cancel_request(msg[1])
                    elif msg[0] == b'P': # ���������Ϣ
                        msg_data = msg[1].decode('utf8')
                        process_promote_result(msg_data)
                    else:
                        logging.error('unknown msg from main process: %s', msg)
            else:
                logging.error('BUG: unknown fobj: %s' % (fobj, ))
# TODO: ͨ��DELETE�������ر�ĳЩ���ӡ�
class pseudo_pg_pg_proxy(pseudo_pg):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy_pobj_list = None
    def select_table(self, tablename, sql):
        if tablename == 'connection':
            return self.select_table_connection(tablename, sql)
        elif tablename == 'process':
            return self.select_table_process(tablename, sql)
        elif tablename == 'server':
            return self.select_table_server(tablename, sql)
        elif tablename == 'startupmsg':
            return self.select_table_startupmsg(tablename, sql)
        else:
            err = 'undefined table %s. only support select on table connection|startupmsg|process|server.' % (tablename, )
            err = err.encode(self.client_encoding)
            return make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'42P01'), (b'M', err)])
    # sqlite3��صĹ��ú���
    def sqlite3_begin(self, create_table_sql):
        db = sqlite3.connect(':memory:')
        c = db.cursor()
        c.execute(create_table_sql)
        return c
    def sqlite3_end(self, c, tablename, sql):
        data = b''
        c.execute(sql)
        row_cnt = 0
        for row in c:
            col_val_list = []
            for v in row:
                v = '%s' % (v, ); v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            data += make_DataRow2(col_val_list)
            row_cnt += 1
        data += make_CommandComplete2(('SELECT %d'%row_cnt).encode(self.client_encoding))
        row_desc = self.make_row_desc((col_desc[0].encode('latin') for col_desc in c.description))
        data = row_desc + data
        c.connection.close()
        return data
    def select_table_connection(self, tablename, sql):
        # ��Ҫ���� RowDescription / DataRow / CommandComplete
        try:
            c = self.sqlite3_begin('create table %s(pid int, id int, fe_ip text, fe_port int, be_ip text, be_port int, user text, database text, status_time text, use_num int)' % (tablename, ))
            for p in self.proxy_pobj_list:
                for x in p.proxy_conn_info_map:
                    cnn = p.proxy_conn_info_map[x]
                    user = get_param_val_from_startupmsg(cnn.startup_msg, 'user').rstrip(b'\x00').decode('latin1')
                    db = get_param_val_from_startupmsg(cnn.startup_msg, 'database').rstrip(b'\x00').decode('latin1')
                    t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cnn.status_time))
                    c.execute("insert into %s values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % 
                              (tablename, p.pid, cnn.pair_id, cnn.fe_ip, cnn.fe_port, cnn.be_ip, cnn.be_port, user, db, t, cnn.use_num))
            data = self.sqlite3_end(c, tablename, sql)
        except sqlite3.Error as ex:
            err = str(ex)
            data = make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'42601'), (b'M', err.encode(self.client_encoding))])
        return data
    def select_table_process(self, tablename, sql):
        # ��Ҫ���� RowDescription / DataRow / CommandComplete
        data = self.make_row_desc((b'pid', b'total_cnn_num', b'idle_cnn_num', b'pending_cnn_num'))
        row_cnt = 0
        for p in self.proxy_pobj_list:
            col_val_list = []
            v = '%d' % p.pid; v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            v = '%d' % p.get_total_cnn_num(); v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            v = '%d' % p.get_idle_cnn_num(); v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            v = '%d' % p.get_pending_cnn_num(); v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            data += make_DataRow2(col_val_list)
            row_cnt += 1
        data += make_CommandComplete2(('SELECT %d'%row_cnt).encode(self.client_encoding))
        return data
    def select_table_server(self, tablename, sql):
        # ��Ҫ���� RowDescription / DataRow / CommandComplete
        data = self.make_row_desc((b'server', b'total_cnn_num', b'idle_cnn_num'))
        
        server_info = {} # (host, port) -> [total_cnn_num, idle_cnn_num]
        for p in self.proxy_pobj_list:
            for x in p.proxy_conn_info_map:
                cnn = p.proxy_conn_info_map[x]
                key = (cnn.be_ip, cnn.be_port)
                if key not in server_info:
                    server_info[key] = [0, 0]
                info = server_info[key]
                info[0] += 1
                if not cnn.fe_ip:
                    info[1] += 1
        
        row_cnt = 0
        for k in server_info:
            info = server_info[k]
            col_val_list = []
            v = '%s:%d' % (k[0], k[1]); v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            v = '%d' % info[0]; v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            v = '%d' % info[1]; v = v.encode(self.client_encoding); col_val_list.append((len(v), v))
            data += make_DataRow2(col_val_list)
            row_cnt += 1
        data += make_CommandComplete2(('SELECT %d'%row_cnt).encode(self.client_encoding))
        return data
    def select_table_startupmsg(self, tablename, sql):
        # ��Ҫ���� RowDescription / DataRow / CommandComplete
        try:
            c = self.sqlite3_begin('create table %s(pid int, id int, idle text, msg text)' % (tablename, ))
            for p in self.proxy_pobj_list:
                for x in p.proxy_conn_info_map:
                    cnn = p.proxy_conn_info_map[x]
                    idle = ('False' if cnn.fe_ip else 'True')
                    msg = ''
                    for param in cnn.startup_msg[3]:
                        msg += param[0].rstrip(b'\x00').decode('latin1') + '=' + param[1].rstrip(b'\x00').decode('latin1') + ' '
                    c.execute("insert into %s values('%s', '%s', '%s', '%s')" % (tablename, p.pid, cnn.pair_id, idle, msg))
            data = self.sqlite3_end(c, tablename, sql)
        except sqlite3.Error as ex:
            err = str(ex)
            data = make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'42601'), (b'M', err.encode(self.client_encoding))])
        return data


# 'P'���͵���Ϣ��'E' + errmsg ���� 'S' + m_ip,m_port;s_ip,s_port;...
def make_P_msg_data(success, *args):
    if not success:
        data = 'E' + args[0]
    else:
        m, s_list = args
        data = 'S%s,%d' % (m[0], m[1])
        for s in s_list:
            data += ';%s,%d' % (s[0], s[1])
    return data.encode('utf8')
# 
# ִ���л�����
def do_switch(poll):
    global master_mon
    logging.info('do_switch')
    if not g_conf['promote']:
        put_msg_to_work_worker(poll, b'P', make_P_msg_data(False, 'the master(%s) is down, but no promote provided' % (g_conf['master'], )))
        master_mon.close(is_down=False)
        return
    # TODO:�Ƿ���Ҫ��kill�����еĹ������̣��Է������ж������Ѿ�down����
    # ���ӵ�promoteִ����������
    promote = g_conf['promote']
    pw = g_conf['conninfo']['pw'].encode('latin1')
    user = g_conf['conninfo']['user'].encode('latin1')
    database = g_conf['conninfo']['db'].encode('latin1')
    lo_oid = g_conf['conninfo']['lo_oid']
    try:
        s, param_dict, key_data = make_pg_login(promote[0], promote[1], password=pw, user=user, database=database)
        res = execute(s, ("select lo_export(%d, 'trigger_file')"%lo_oid).encode('latin1'))
    except (OSError, RuntimeError) as ex:
        # ����ʧ�ܡ���Ҫ���ͱ�����
        logging.warning('do_switch exception: %s' % (str(ex), ))
        master_mon.close(is_down=False)
        # ������ʧ�ܽ�������������̡�
        put_msg_to_work_worker(poll, b'P', make_P_msg_data(False, str(ex)))
        return
    logging.info('promote done')
    # TODO:���ӿ��Ƿ��ѻָ����
    # �����ɹ�֮���޸����ò���
    g_conf['master'] = g_conf['promote']
    g_conf['promote'] = None
    if g_conf['slaver_list'] and g_conf['master'] in g_conf['slaver_list']:
        g_conf['slaver_list'].remove(g_conf['master'])
    # ���³�ʼ��master_mon
    # ��try_go���Ѿ���master_mon��poll��unregister�ˡ�
    master_mon.close(is_down=False)
    master_mon = pg_monitor(g_conf['master'], g_conf['conninfo'])
    master_mon.connect_first()
    # �������ɹ���������������̡�
    put_msg_to_work_worker(poll, b'P', make_P_msg_data(True, g_conf['master'], g_conf['slaver_list']))
    logging.info('do_switch done')
# �ɹ�put����True�����򷵻�False��
def put_msg_to_work_worker(poll, msg_type, msg_data, fdlist=[]):
    for pobj in work_worker_pobj_list:
        if pobj.is_connected():
            pobj.put_msg(msg_type, msg_data, fdlist)
            poll.register(pobj, poll.POLLOUT|poll.POLLIN)
            return True
    return False
def make_f_msg_data(addr, use_idle_cnn, startup_msg_raw):
    msg_data = '%s,%d,%d' % (addr[0], addr[1], use_idle_cnn)
    msg_data = msg_data.encode('latin1')
    msg_data = struct.pack('>i', len(msg_data)+4) + msg_data + cnn.startup_msg_raw
    return msg_data
# 
def match_conds(startup_msg, addr, disable_conds_list):
    msg = {}
    for kv in startup_msg[3]:
        msg[kv[0].rstrip(b'\x00').decode('latin1')] = kv[1].rstrip(b'\x00').decode('latin1')
    for disable_conds in disable_conds_list:
        match = True
        for cond in disable_conds:
            cond_name = cond[0]
            if cond_name not in msg:
                match = False
                break
            if not re.match(cond[1], msg[cond_name]):
                match = False
                break
        if match:
            return True
    return False
def sigterm_handler(signum, frame):
    logging.info('got SIGTERM')
    for pobj in work_worker_pobj_list:
        logging.info('kill work_worker %d', pobj.pid)
        os.kill(pobj.pid, signal.SIGTERM)
    for pobj in proxy_worker_pobj_list:
        logging.info('kill proxy_worker %d', pobj.pid)
        os.kill(pobj.pid, signal.SIGTERM)
    logging.info('unlink unix domain socket:%s', g_conf['ipc_uds_path'])
    os.unlink(g_conf['ipc_uds_path'])
    logging.info('unlink pid_file:%s', g_conf['pid_file'])
    os.unlink(g_conf['pid_file'])
    sys.exit(0)
# main
proxy_worker_pobj_list = []
work_worker_pobj_list = []
g_conf_file = None
g_conf = None
# TODO: �������ڼ�⵽work�ӽ����˳�������work�ӽ��̡�
# TODO: SIGUSR1�ź����´���־�ļ���
if __name__ == '__main__':
    if len(sys.argv) == 1:
        g_conf_file = os.path.join(os.path.dirname(__file__), 'pg_proxy.conf.py')
    elif len(sys.argv) == 2:
        g_conf_file = sys.argv[1]
    else:
        print('usage: %s [conf_file]' % (sys.argv[0], ))
        sys.exit(1)
    
    g_conf = read_conf_file(g_conf_file, 'pg_proxy_conf')
    w = get_max_len(g_conf['_print_order'])
    for k in g_conf['_print_order']: 
        print(k.ljust(w), ' = ', g_conf[k])
    fe_be_pair.recv_sz_per_poll = g_conf['recv_sz_per_poll']
    try:
        f = open(g_conf['pid_file'], 'x')
        f.write('%s' % (os.getpid(), ))
        f.close()
    except OSError as ex:
        print('%s' % (str(ex), ))
        sys.exit(1)
    
    master_mon = pg_monitor(g_conf['master'], g_conf['conninfo'])
    master_mon.connect_first()
    
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_s.bind(g_conf['listen'])
    listen_s.listen(100)
    listen_s.settimeout(0)
    
    ipc_s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ipc_s.bind(g_conf['ipc_uds_path'])
    ipc_s.listen(100)
    ipc_s.settimeout(0)
    # �����ؽ���
    for i in range(g_conf['proxy_worker_num']):
        pid = os.fork()
        if pid == 0:
            proxy_worker_pobj_list.clear()
            master_mon.close(is_down=False)
            listen_s.close()
            ipc_s.close()
            if g_conf['log']['filename']:
                g_conf['log']['filename'] += '.proxy%d' % (i+1, )
            logging.basicConfig(**g_conf['log'])
            set_process_title('pg_proxy.py: proxy worker')
            proxy_worker(g_conf['ipc_uds_path'])
        proxy_worker_pobj_list.append(proxy_worker_process(pid, i))
    # ������������
    pid = os.fork()
    if pid == 0:
        proxy_worker_pobj_list.clear()
        master_mon.close(is_down=False)
        listen_s.close()
        ipc_s.close()
        if g_conf['log']['filename']:
            g_conf['log']['filename'] += '.work'
        logging.basicConfig(**g_conf['log'])
        set_process_title('pg_proxy.py: work worker')
        work_worker(g_conf['ipc_uds_path'])
    work_worker_pobj_list.append(work_worker_process(pid, 0))
    
    if g_conf['log']['filename']:
        g_conf['log']['filename'] += '.main'
    logging.basicConfig(**g_conf['log'])
    
    signal.signal(signal.SIGTERM, sigterm_handler)
    
    pseudo_db_list = [] # α���ݿ�����
    pending_fe_conns = [] # ��û������startup_msg��fe����
    cancel_request_list = [] # �ȴ������������̵�CancelRequest
    send_fe_cnn_list = [] # �ȴ�����proxy���̵�fe����
    next_slaver_idx = 0
    master_mon_ret = None
    poll = spoller()
    poll.register(listen_s, poll.POLLIN)
    poll.register(ipc_s, poll.POLLIN)
    
    while True:
        master_mon_called = False
        to_v = 10000
        if master_mon_ret == None:
            to_v = 0.1
        
        down_proxy_worker_pobj_list = []
        x = poll.poll(to_v)
        for fobj, event in x:
            if fobj == listen_s:
                fe_conn = pending_fe_connection(listen_s.accept()[0])
                poll.register(fe_conn, poll.POLLIN)
                pending_fe_conns.append(fe_conn)
            elif fobj == ipc_s:
                conn = uds_ep(ipc_s.accept()[0])
                poll.register(conn, poll.POLLIN)
            elif type(fobj) == uds_ep: # ���յ�һ����Ϣ
                ret = fobj.recv()
                if ret[0] > 0:
                    continue
                poll.unregister(fobj)
                msg = ret[1]
                logging.debug('[main][uds_ep]recv: %s', msg)
                pid = struct.unpack('>i', msg[1])[0]
                for pobj in (proxy_worker_pobj_list + work_worker_pobj_list):
                    if pobj.pid == pid:
                        pobj.ep = fobj
                        poll.register(pobj, poll.POLLIN)
                        break
            elif type(fobj) == work_worker_process:
                fobj.handle_event(poll, event)
            elif type(fobj) == proxy_worker_process:
                try:
                    fobj.handle_event(poll, event)
                    # close�Ѿ����͵�pending_fe_connection
                    fobj.close_fe_cnn()
                except (OSError, RuntimeError) as ex:
                    logging.error('proxy worker process(%d) is down: %s', fobj.pid, str(ex))
                    poll.unregister(fobj)
                    proxy_worker_pobj_list.remove(fobj)
                    fobj.close()
                    logging.info('try to kill the proxy worker process:%d', fobj.pid)
                    try:
                        os.kill(fobj.pid, signal.SIGTERM)
                        logging.info('kill done')
                    except OSError as ex:
                        logging.info('kill fail:%s', str(ex))
                    down_proxy_worker_pobj_list.append(fobj)
            elif type(fobj) == pending_fe_connection: # pending_fe_connection
                try:
                    fobj.recv()
                except Exception as ex:
                    logging.info('pending_fe_connection.recv error: Exception: %s', str(ex))
                    poll.unregister(fobj)
                    fobj.close()
                    pending_fe_conns.remove(fobj)
            elif type(fobj) == pseudo_pg_pg_proxy:
                try:
                    ret = ''
                    if event & poll.POLLIN:
                        ret = fobj.recv()
                    if event & poll.POLLOUT:
                        ret += fobj.send()
                    logging.debug('pseudo_pg: %s', ret)
                    if 'w' in ret:
                        poll.register(fobj, poll.POLLIN|poll.POLLOUT)
                    else:
                        poll.register(fobj, poll.POLLIN)
                except Exception as ex:
                    logging.info('pseudo_pg error: Exception: %s', str(ex))
                    #traceback.print_exc()
                    poll.unregister(fobj)
                    pseudo_db_list.remove(fobj)
                    fobj.close()
            elif fobj == master_mon:
                master_mon_called = True
                master_mon_ret = master_mon.try_go(poll, True)                  
        # ����master_mon
        if not master_mon_called:
            master_mon_ret = master_mon.try_go(poll, False)
        if master_mon.check_down():
            do_switch(poll)
        # ����pending_fe_connection
        # ���pending_fe_connection�Ƿ��ѽ��յ�startup��Ϣ
        del_cnns = []
        for cnn in pending_fe_conns:
            if not cnn.check_startup():
                continue
            
            poll.unregister(cnn) # StartupMessage������֮��Ϳ��Դ�poll��ɾ���ˡ�
            if cnn.is_CancelRequest():
                cancel_request_list.append(cnn.startup_msg_raw)
                cnn.close()
                del_cnns.append(cnn)
                continue
            if cnn.is_SSLRequest() or cnn.is_StartupMessageV2() or cnn.get_param_val(b'replication') != None:
                cnn.close()
                del_cnns.append(cnn)
                continue
            # version 3 StartupMessage
            send_fe_cnn_list.append(cnn)
            del_cnns.append(cnn)
        # �Ƴ��Ѿ��������pending_fe_connection
        for cnn in del_cnns:
            pending_fe_conns.remove(cnn)
        del_cnns.clear()
        # ������һ��work���̷���CancelRequest
        for pobj in work_worker_pobj_list:
            if pobj.is_connected():
                for x in cancel_request_list:
                    pobj.put_msg(b'c', x)
                if cancel_request_list:
                    poll.register(pobj, poll.POLLOUT|poll.POLLIN)
                    cancel_request_list.clear()
                break
        # ��proxy���̷���fe����
        del_cnns.clear()
        pseudo_db_cnns = []
        pobj_set = set()
        for cnn in send_fe_cnn_list:
            slaver_selected = False
            user = cnn.get_param_val('user')
            dbname = cnn.get_param_val('database')
            if dbname == b'pg_proxy\x00':
                pseudo_db_cnns.append(cnn)
                continue
            if cnn.is_readonly() and g_conf['slaver_list']:
                slaver_selected = True
                be_addr = g_conf['slaver_list'][next_slaver_idx%len(g_conf['slaver_list'])]
            else:
                be_addr = g_conf['master']
            
            pobj = None
            min_active_cnn = 1024*1024
            has_matched = False
            for p in proxy_worker_pobj_list:
                if not p.is_connected():
                    continue
                if p.has_matched_idle_conn(cnn.startup_msg_raw, be_addr):
                    logging.info('[%d]found idle cnn to %s for %s' % (p.pid, be_addr, cnn.startup_msg))
                    p.put_msg(b'f', make_f_msg_data(be_addr, 1, cnn.startup_msg_raw), [cnn.fileno()])
                    p.add_closing_fe_cnn(cnn)
                    p.remove_idle_conn(cnn.startup_msg_raw)
                    pobj_set.add(p)
                    del_cnns.append(cnn)
                    has_matched = True
                    break
                if p.get_active_cnn_num() < min_active_cnn:
                    min_active_cnn = p.get_active_cnn_num()
                    pobj = p
            if has_matched:
                continue
            if not pobj: # ����pobj��δ���ӵ������̡�
                logging.warning('all pobj in proxy_worker_pobj_list are not connected')
                break
            # ������ǰ����������ٵ�proxy���̡�
            logging.info('[%d]no idle cnn to %s for %s' % (pobj.pid, be_addr, cnn.startup_msg))
            pobj.put_msg(b'f',  make_f_msg_data(be_addr, 0, cnn.startup_msg_raw), [cnn.fileno()])
            pobj.add_closing_fe_cnn(cnn)
            if pobj.pending_cnn_num < 0:
                logging.warning('pending_cnn_num < 0')
                pobj.pending_cnn_num = 1
            else:
                pobj.pending_cnn_num += 1
            pobj_set.add(pobj)
            del_cnns.append(cnn)
            if slaver_selected:
                next_slaver_idx += 1
        for pobj in pobj_set:
            poll.register(pobj, poll.POLLOUT|poll.POLLIN)
        pobj_set.clear()
        for cnn in del_cnns:
            send_fe_cnn_list.remove(cnn)
        del_cnns.clear()
        # ����α���ݿ�
        for cnn in pseudo_db_cnns:
            pseudo_db = pseudo_pg_pg_proxy(g_conf['pg_proxy_pw'].encode('latin1'), cnn.s, cnn.startup_msg)
            pseudo_db.proxy_pobj_list = proxy_worker_pobj_list
            poll.register(pseudo_db, poll.POLLIN|poll.POLLOUT)
            pseudo_db_list.append(pseudo_db)
            send_fe_cnn_list.remove(cnn)
        pseudo_db_cnns.clear()
        # ����Ƿ���Ҫ�����ӽ���
        for pobj in down_proxy_worker_pobj_list:
            logging.info('restart proxy worker:%d', pobj.idx)
            pid = os.fork()
            if pid == 0:
                master_mon.close(is_down=False)
                close_fobjs([listen_s, ipc_s, poll, pseudo_db_list, pending_fe_conns, send_fe_cnn_list, proxy_worker_pobj_list, work_worker_pobj_list])                
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                
                if g_conf['log']['filename']:
                    g_conf['log']['filename'] += '.proxy%d' % (pobj.idx+1, )
                logging.basicConfig(**g_conf['log'])
                set_process_title('pg_proxy.py: proxy worker')
                proxy_worker(g_conf['ipc_uds_path'])
            proxy_worker_pobj_list.append(proxy_worker_process(pid, pobj.idx))


