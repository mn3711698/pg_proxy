#!/bin/env python3
# -*- coding: GBK -*-
# 
# ���pg�Ƿ����
# 
import sys, os, time
import socket
import logging

from netutils import myrecv, NONBLOCK_CONNECT_EX_OK
from pgprotocol import *

# 
# ���pg�Ƿ���ã������ڼ������ʹӿ⡣
# ��Ҫ����������µ���try_go:
#   .) ��poller�м�⵽�ɶ�д����ʱ����None��ʾ�Ѽ��������ѶϿ����ӣ���Ҫ��һ��ʱ����ٿ�ʼ��һ�μ�⡣
#      ��ʱ��Ҫ��poller unregister pg_monitor��ͬʱ��poller����һ��pollʱ��Ҫ����һ��С��timeout��
#   .) ��poller֮����Ҫ���á�
# 
class pg_monitor(object):
    # addr : ����/�ӿ��ַ
    # conninfo : �û���/���ݿ�/����ȵ���Ϣ
    def __init__(self, addr, conninfo):
        self.addr = addr
        self.username = conninfo['user'].encode('latin1')
        self.dbname = conninfo.get('db', 'postgres').encode('latin1')
        self.password = conninfo.get('pw', '').encode('latin1')
        self.conn_retry_num = conninfo.get('conn_retry_num', 5)
        self.conn_retry_interval = conninfo.get('conn_retry_interval', 2)
        self.query_interval = conninfo.get('query_interval', 5)
        self.lo_oid = conninfo.get('lo_oid', 9999)
        self.query_sql = b'select 1'
        
        self.s = None
        self.param_dict = None
        self.key_data = None
        self.status = 'disconnected' # disconnected -> connect_sending -> connect_recving -> connected -> query_sending -> query_recving
        
        self.last_query_time = time.time() # ��¼���һ�γɹ�query��ʱ�䡣
        self.query_sending_data = b''
        self.query_recving_data = b''
        self.ready_for_query_recved = False
        self.error_response_recved = False
        
        self.disconnected_list = [] # ��¼����ʧ�ܵ�ʱ�䣬����ļ�¼�����������ʧ�ܼ�¼�����ӳɹ���ʱ�����ո��б�
        self.connect_sending_data = b''
        self.connect_recving_data = b''
    # ���ӳɹ�����øú���
    def connection_done(self):
        self.status = 'connected'
        
        self.last_query_time = time.time()
        self.query_sending_data = b''
        self.query_recving_data = b''
        self.ready_for_query_recved = False
        self.error_response_recved = False
        
        self.disconnected_list.clear()
        self.connect_sending_data = b''
        self.connect_recving_data = b''
    # ����ʧ�ܵ�ʱ����øú�����is_down��ʾ���ݿ��Ƿ��Ѿ�down����
    def close(self, is_down):
        if self.s:
            self.s.close()
            self.s = None
            self.param_dict = None
            self.key_data = None
        self.status = 'disconnected'
        
        self.last_query_time = time.time()
        self.query_sending_data = b''
        self.query_recving_data = b''
        self.ready_for_query_recved = False
        self.error_response_recved = False
        
        if not is_down:
            self.disconnected_list.clear()
        self.disconnected_list.append(time.time())
        self.connect_sending_data = b''
        self.connect_recving_data = b''
    def fileno(self):
        return self.s.fileno()
    # �ڳ�������ʱ������ͬ���������ӣ���ȷ�����ݿ���á�
    def connect_first(self):
        self.s, self.param_dict, self.key_data = make_pg_login(self.addr[0], self.addr[1], password=self.password, 
                                                               user=self.username, database=self.dbname, application_name=b'pg_proxy monitor')
        # ��������Ƿ����
        sql = ("select oid from pg_largeobject_metadata where oid=%d"%self.lo_oid).encode('latin1')
        try:
            res = execute(self.s, sql)
        except (OSError, RuntimeError) as ex:
            raise RuntimeError('execute(%s) fail:%s' % (sql, str(ex)))
        if len(res[2]) != 1:
            raise RuntimeError('large object(%d) does not exist' % (self.lo_oid, ))
        
        self.last_query_time = time.time()
        self.status = 'connected'
        self.s.settimeout(0)
    # ������ݿ��Ƿ��Ѿ�down����
    def check_down(self):
        if len(self.disconnected_list) >= self.conn_retry_num:
            return True
        return False
    # ����go��������ص��쳣��
    # called��ʾ�Ƿ���pollѭ��������õģ�Ҳ����˵�Ƿ���poll���档
    def try_go(self, poll, called):
        try:
            return self.go(poll, called)
        except (OSError, RuntimeError) as ex:
            logging.warning('[pg_monitor %s %s %s] Exception: %s', self.addr, self.dbname, self.username, str(ex))
            if called:
                poll.unregister(self)
            self.close(is_down=True)
            return None
    # ע�⣺���go�����׳��쳣���Ǿ�˵�����ݿ��Ѿ�down�ˣ������ڸú����ڱ��벶�񲻱�ʾ���ݿ��Ѿ�down�����쳣��
    # ����None��ʾ����Ҫ����Ƿ�ɶ�д����ʱpoller��Ҫ����һ����ʱ��
    def go(self, poll, called):
        if self.status == 'disconnected':
            # �ڱ�״̬��ʱ��disconnected_list����϶�������һ����¼��
            if not self.disconnected_list:
                raise SystemError('BUG: disconnected_list should not be empty')
            t = time.time()
            prev_t = self.disconnected_list[len(self.disconnected_list)-1]
            if t - prev_t < self.conn_retry_interval:
                return None
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(0)
            ret = self.s.connect_ex(self.addr)
            if ret not in NONBLOCK_CONNECT_EX_OK:
                raise RuntimeError('connect_ex fail:%s' % (os.strerror(ret), ))
            self.connect_sending_data = make_StartupMessage2(user=self.username, database=self.dbname, application_name=b'pg_proxy monitor')
            self.connect_recving_data = b''
            self.status = 'connect_sending'
            poll.register(self, poll.POLLOUT)
            return 'w'
        elif self.status == 'connect_sending':
            # ����޷����ӣ���ô�����send�����׳�OSError�쳣������һ��������ݿ�û��down������������ʧ�ܡ��������������ԭ���ǣ���������
            # �ļ��������Ѿ��ù⵼��acceptʧ�ܡ���δ�OSError�ж����������
            n = self.s.send(self.connect_sending_data)
            self.connect_sending_data = self.connect_sending_data[n:]
            if not self.connect_sending_data:
                self.status = 'connect_recving'
                poll.register(self, poll.POLLIN)
                return 'r'
            poll.register(self, poll.POLLOUT)
            return 'w'
        elif self.status == 'connect_recving':
            data = myrecv(self.s, 1024*4)
            if data == None:
                return 'r'
            if not data:
                raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
            self.connect_recving_data += data
            # ���������ص���Ϣ��
            ret = parse_be_msg(self.connect_recving_data)
            self.connect_recving_data = self.connect_recving_data[ret[0]:]
            for msg in ret[1]:
                logging.debug('[pg_monitor %s %s %s] %s', self.addr, self.dbname, self.username, msg)
                if msg[1] == b'R': # AuthenticationXXX��Ϣ
                    if msg[0] == 'AuthenticationOk':
                        None
                    elif msg[0] == 'AuthenticationCleartextPassword' or msg[0] == 'AuthenticationMD5Password':
                        if msg[0] == 'AuthenticationCleartextPassword':
                            self.connect_sending_data = make_PasswordMessage2(self.password)
                        else:
                            self.connect_sending_data = make_PasswordMessage2(self.password, self.username, msg[2])
                        self.connect_recving_data = b''
                        self.status = 'connect_sending'
                        poll.register(self, poll.POLLOUT)
                        return 'w'
                    else:
                        # ���ڲ�֧�ֵ�authentication��ֻ���ͱ��������ǲ�����Ϊ���ݿ��Ѿ�down����
                        if called: # ������close֮ǰunregister
                            poll.unregister(self)
                        self.report_error(b'unsupported authentication:%s' % (msg, ))
                        self.close(is_down=False)
                        return None
                elif msg[0] == 'ErrorResponse':
                    if called:
                        poll.unregister(self)
                    self.error_response_recved = True
                    self.report_error(msg)
                    self.close(is_down=False)
                    return None
                elif msg[0] == 'ReadyForQuery':
                    self.ready_for_query_recved = True
            if self.ready_for_query_recved:
                if called:
                    poll.unregister(self)
                self.connection_done()
                return None
            poll.register(self, poll.POLLIN)
            return 'r'
        elif self.status == 'connected':
            t = time.time()
            if t - self.last_query_time < self.query_interval:
                return None
            self.query_sending_data = make_Query2(self.query_sql)
            self.query_recving_data = b''
            self.status = 'query_sending'
            logging.debug('[pg_monitor %s %s %s] sending query: %s', self.addr, self.dbname, self.username, self.query_sending_data.decode('latin1'))
            poll.register(self, poll.POLLOUT)
            return 'w'
        elif self.status == 'query_sending':
            n = self.s.send(self.query_sending_data)
            self.query_sending_data = self.query_sending_data[n:]
            if not self.query_sending_data:
                poll.register(self, poll.POLLIN)
                self.status = 'query_recving'
                return 'r'
            poll.register(self, poll.POLLOUT)
            return 'w'
        elif self.status == 'query_recving':
            data = myrecv(self.s, 1024*4)
            if data == None:
                return 'r'
            if not data:
                raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
            self.query_recving_data += data
            # �����Ϣ����ֱ�����յ�ReadyForQuery���м���ܻ���յ�ErrorResponse��Ϣ��
            ret = parse_be_msg(self.query_recving_data)
            self.query_recving_data = self.query_recving_data[ret[0]:]
            for msg in ret[1]:
                logging.debug('[pg_monitor %s %s %s] %s', self.addr, self.dbname, self.username, msg)
                if msg[0] == 'ErrorResponse': # ����ErrorResponse����ʾ���ݿ��Ѿ�down����������Ҫ���ͱ����ʼ�֮��ģ�֪ͨ����Ա��
                    self.error_response_recved = True
                    self.report_error(msg)
                elif msg[0] == 'ReadyForQuery':
                    self.ready_for_query_recved = True
            if self.ready_for_query_recved and not self.query_recving_data: # �Է�ReadyForQuery֮���������첽��Ϣ������ParameterStatus��NotificationResponse��
                if called:
                    poll.unregister(self)
                self.status = 'connected'
                self.last_query_time = time.time()
                self.query_sending_data = b''
                self.query_recving_data = b''
                self.error_response_recved = False
                self.ready_for_query_recved = False
                return None
            poll.register(self, poll.POLLIN)
            return 'r'
        else:
            raise SystemError('BUG: unknown status:%s' % (self.status, ))
    # �����ӻ���ִ��������ʱ������øú�����
    def report_error(self, msg):
        logging.error('[pg_monitor %s %s %s] report error:%s', self.addr, self.dbname, self.username, msg)

# main
if __name__ == '__main__':
    pass

