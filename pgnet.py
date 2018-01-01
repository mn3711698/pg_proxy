#!/bin/env python3
# -*- coding: GBK -*-
# 
# 
# 
import sys, os, socket, time
import traceback
import functools
import getpass
import netutils
import pgprotocol3 as p

# �����Ƿ������ģ�����connect��ʱ��
class connbase():
    def __init__(self, s):
        self.s = s
        self.s.settimeout(0)
        self.recv_buf = b''
        self.send_buf = b''
        self.readsz = -1 # _read����ÿ������ȡ�����ֽڣ�<=0��ʾ���ޡ�
    def fileno(self):
        return self.s.fileno()
    def close(self):
        self.s.close()
        self.status = 'disconnected'
    # ��ȡ����ֱ��û�����ݿɶ�
    def _read(self):
        while True:
            data = netutils.myrecv(self.s, 4096)
            if data is None:
                break
            elif not data:
                raise RuntimeError('the peer(%s) closed connection' % (self.s.getpeername(),))
            self.recv_buf += data
            if len(data) < 4096:
                break
            if self.readsz > 0 and len(self.recv_buf) >= self.readsz:
                break
    def _write(self):
        if self.send_buf:
            sz = self.s.send(self.send_buf)
            self.send_buf = self.send_buf[sz:]
    # ���ؽ��������Ϣ�б���max_msgָ����෵�ض��ٸ���Ϣ��
    def read_msgs(self, max_msg=0, *, fe):
        self._read()
        if not self.recv_buf:
            return []
        idx, msg_list = p.parse_pg_msg(self.recv_buf, max_msg, fe=fe)
        if msg_list:
            self.recv_buf = self.recv_buf[idx:]
        return msg_list
    # ���ػ�ʣ���ٸ��ֽ�û�з��͡�msg_listΪ����ᷢ���ϴ�ʣ�µ����ݡ�
    def write_msgs(self, msg_list=(), *, fe):
        prefix_str = 'BE' if fe else 'FE'
        for msg in msg_list:
            print('%s: %s' % (prefix_str, msg))
            self.send_buf += msg.tobytes()
        self._write()
        return len(self.send_buf)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
class feconn(connbase):
    def __init__(self, s):
        self.status = 'connected'
        super().__init__(s)
    # ��ȡ��һ����Ϣ�������û���յ��򷵻�None��
    def read_startup_msg(self):
        self._read()
        m = None
        if p.startup_msg_is_complete(self.recv_buf):
            m = p.parse_startup_msg(self.recv_buf[4:])
            self.recv_buf = b''
        return m
    def read_msgs(self, max_msg=0):
        return super().read_msgs(max_msg, fe=True)
    def write_msgs(self, msg_list=()):
        return super().write_msgs(msg_list, fe=True)
    def write_msg(self, msg):
        return self.write_msgs((msg,))
class beconn(connbase):
    def __init__(self, addr, async_conn=False):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = 'connecting'
        # connect_exҲ�����׳��쳣��֮����Ҫ�ȼ��POLLOUT|POLLERR��
        # POLLERR��ʾ����ʧ�ܣ���ʱ��ͨ��netutils.get_socket_error�������ʧ�ܵ�ԭ��
        # POLLOUT��ʾ���ӳɹ����Է������ݡ�
        if async_conn:
            s.settimeout(0)
            s.connect_ex(addr)
        else:
            s.connect(addr)
            self.status = 'connected'
        super().__init__(s)
    def read_msgs(self, max_msg=0):
        return super().read_msgs(max_msg, fe=False)
    def write_msgs(self, msg_list=()):
        return super().write_msgs(msg_list, fe=False)
    def write_msg(self, msg):
        return self.write_msgs((msg,))
# ��Ч�Ĺؼ��ֲ�������: host, port, database, user, password, �Լ�����GUC����������client_encoding, application_name��
class pgconn(beconn):
    def __init__(self, **kwargs):
        self.async_msgs = { 
            p.MsgType.MT_NoticeResponse :       [], 
            p.MsgType.MT_NotificationResponse : [], 
            p.MsgType.MT_ParameterDescription : [], 
        }
        self.processer = None
        host = kwargs.pop('host', '127.0.0.1')
        port = kwargs.pop('port', 5432)
        super().__init__((host, port))
        if 'database' not in kwargs:
            kwargs['database'] = 'postgres'
        if 'user' not in kwargs:
            kwargs['user'] = getpass.getuser()
        password = kwargs.pop('password', '')
        m = p.StartupMessage.make(**kwargs)
        self.write_msg(m)
        self._process_auth(password.encode('utf8'), kwargs['user'].encode('utf8'))
    def _process_auth(self, password, user):
        m = self.processer.process()
        if m.authtype == p.AuthType.AT_Ok:
            return
        elif m.authtype == p.AuthType.AT_CleartextPassword:
            self.write_msg(m.make_ar(password=password))
        elif m.authtype == p.AuthType.AT_MD5Password:
            self.write_msg(m.make_ar(password=password, user=user))
        else:
            raise RuntimeError('unsupported authentication type:%s' % m)
        self._process_auth(password, user)
    def write_msg(self, msg):
        if self.processer:
            raise RuntimeError('you should not call write_msg while processer(%s) is not None' % self.processer)
        ret = super().write_msg(msg)
        self.processer = get_processer_for_msg(msg)(self)
        return self.processer
    # read_msgs_until_avail/write_msgs_until_done ������ѭ����д������æ�ȴ�����cpuռ�ã�������poller������Ƿ�ɶ�д��
    # һֱ��ֱ������ϢΪֹ
    def read_msgs_until_avail(self, max_msg=0):
        msg_list = None
        while not msg_list:
            msg_list = self.read_msgs(max_msg)
        return msg_list
    # һֱдֱ��д��Ϊֹ
    def write_msgs_until_done(self):
        while self.write_msgs():
            pass
    def flush(self):
        return self.write_msgs((p.Flush(),))
    def sync(self):
        return self.write_msgs((p.Sync(),))
    def got_async_msg(self, m):
        self.async_msgs[m.msg_type].append(m)
        if m.msg_type == p.MsgType.MT_ParameterStatus:
            self.params[bytes(m.name).decode('ascii')] = bytes(m.val).decode('ascii')
    # str <-> bytes
    def encode(self, data):
        if type(data) is str:
            data = data.encode(self.params['client_encoding'])
        return data
    def decode(self, data):
        if type(data) is not str:
            data = bytes(data).decode(self.params['client_encoding'])
        return data
    # ִ�в�ѯ���������ֵ��CopyResponse����Ҫ����process��������copy������
    def query(self, sql):
        sql = self.encode(sql)
        return self.write_msg(p.Query(query=sql)).process()
# ��ʾErrorResponse��Ϣ���쳣�����������׳�����RuntimeError�쳣��
class pgerror(Exception):
    def __init__(self, errmsg):
        super().__init__(errmsg)
        self.errmsg = errmsg
# transaction context manager
class pgtrans():
    def __init__(self, cnn):
        self.cnn = cnn
        sele.cnn.query('begin')
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.cnn.query('commit')
        else:
            self.cnn.query('abort')
# ���rowdesc!=None����������з��ؽ�����Ĳ�ѯ(����select)���������û�н������(����insert/delete)��
class QueryResult():
    class rowtype():
        # r : row data
        # qres : QueryResult which contains the row data
        def __init__(self, r, qres):
            self.r = r
            self.qres = qres
        def __iter__(self):
            yield from self.r
        def __len__(self):
            return len(self.r)
        def __getitem__(self, idx):
            if type(idx) is str:
                idx = self.qres.field_map[idx]
            return self.r[idx]
        def __getattr__(self, name):
            if name not in self.qres.field_map:
                raise AttributeError('no attribute %s' % name)
            return self[name]
        def __repr__(self):
            ret = '('
            for field in self.qres.rowdesc:
                ret += '%s=%s, ' % (field.name, self[field.name])
            ret = ret[:-2] + ')'
            return ret
    
    def __init__(self, cmdtag, rowdesc, rows):
        self.cmdtag = cmdtag
        self.rowdesc = rowdesc
        self.rows = rows
        self._parse_cmdtag()
        self._make_field_map()
    def _parse_cmdtag(self):
        s1, s2 = self.cmdtag.split(maxsplit=1)
        if s1 in ('UPDATE', 'DELETE', 'SELECT', 'MOVE', 'FETCH', 'COPY'):
            self.cmdtag = (s1, int(s2))
        elif s1 in ('INSERT',):
            oid, rownum = s2.split(maxsplit=1)
            self.cmdtag = (s1, int(rownum), int(oid))
        else:
            self.cmdtag = (self.cmdtag, )
    def _make_field_map(self):
        if self.rowdesc is None:
            return
        self.field_map = {field.name : idx for idx, field in enumerate(self.rowdesc)}
    def __iter__(self):
        for r in self.rows:
            yield type(self).rowtype(r, self)
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, idx):
        return type(self).rowtype(self.rows[idx], self)
    def rowcount(self):
        if self.rowdesc is None:
            if len(self.cmdtag) >= 2:
                return self.cmdtag[1]
            else:
                return -1
        return len(self)
    def field_info(self, fname):
        return self.rowdesc[self.field_map[fname]]
# 
# processer for response msg after sending message
# 
def get_processer_for_msg(msg):
    msgname = type(msg).__name__
    pname = msgname + 'Processer'
    return globals()[pname]
class MsgProcesser():
    def __init__(self, cnn, prev_processer=None):
        self.cnn = cnn
        self.prev_processer = prev_processer
    def process(self, *args, **kwargs):
        self.cnn.write_msgs_until_done()
        try:
            return self._process(*args, **kwargs)
        finally:
            self.reset_processer()
    # ��cnn��processer����Ϊprev_processer
    def reset_processer(self):
        if self.cnn.processer is self:
            self.cnn.processer = self.prev_processer
class StartupMessageProcesser(MsgProcesser):
    UnknownMsgErr = 'unknown response msg for startup message'
    def __init__(self, cnn):
        super().__init__(cnn)
        self.params = {}
        self.be_keydata = None
    # ����authtype��Ok/CleartextPasword/MD5Password��Authentication�������׳��쳣��
    # ���ú�Ӧ�ü��cnn.async_msgs[MsgType.MT_NoticeResponse]�Ƿ�Ϊ�ա�
    def _process(self):
        msg_list = self.cnn.read_msgs_until_avail()
        m1 = msg_list[0]
        if m1.msg_type == p.MsgType.MT_Authentication:
            if m1.authtype == p.AuthType.AT_Ok:
                self._process_msg_list(msg_list[1:])
                self.cnn.params = self.params
                self.cnn.be_keydata = self.be_keydata
                return m1
            elif m1.authtype == p.AuthType.AT_CleartextPassword or m1.authtype == p.AuthType.AT_MD5Password:
                return m1
            else:
                raise RuntimeError('unsupported authentication type', m1)
        elif m1.msg_type == p.MsgType.MT_ErrorResponse:
            raise pgerror(m1)
        else:
            raise RuntimeError(cls.UnknownMsgErr, m1)
    def _process_msg_list(self, msg_list):
        got_ready = False
        for m in msg_list:
            if m.msg_type == p.MsgType.MT_ParameterStatus:
                self.params[bytes(m.name).decode('ascii')] = bytes(m.val).decode('ascii')
            elif m.msg_type == p.MsgType.MT_BackendKeyData:
                self.be_keydata = (m.pid, m.skey)
            elif m.msg_type == p.MsgType.MT_ReadyForQuery:
                got_ready = True
                break
            elif m.msg_type == p.MsgType.MT_NoticeResponse:
                self.cnn.got_async_msg(m)
            elif m.msg_type == p.MsgType.MT_ErrorResponse:
                raise pgerror(m)
            else:
                raise RuntimeError(self.UnknownMsgErr, m)
        if got_ready:
            return
        msg_list = self.cnn.read_msgs_until_avail()
        self._process_msg_list(msg_list)
class AuthResponseProcesser(StartupMessageProcesser):
    UnknownMsgErr = 'unknown response msg for AuthResponse message'
class QueryProcesser(MsgProcesser):
    UnknownMsgErr = 'unknown response msg for Query message'
    def __init__(self, cnn):
        super().__init__(cnn)
        self.msgs_from_copy = []
        self.ex = None
        self.cmdtag = None
        self.rowdesc = None
        self.rows = None
    # ����(cmdtag, rowdesc, rows)������CopyResponse��Ϣ�������׳��쳣��
    def _process(self):
        if self.msgs_from_copy:
            msg_list = self.msgs_from_copy
            self.msgs_from_copy = []
        else:
            msg_list = self.cnn.read_msgs_until_avail()
        ret = self._process_msg_list(msg_list)
        if isinstance(ret, p.CopyResponse):
            return ret
        if self.ex:
            raise self.ex
        return QueryResult(self.cmdtag, self.rowdesc, self.rows)
    def _process_msg_list(self, msg_list):
        got_ready = False
        for idx, m in enumerate(msg_list):
            if m.msg_type == p.MsgType.MT_EmptyQueryResponse:
                self.ex = RuntimeError('empty query', m)
            elif m.msg_type == p.MsgType.MT_ErrorResponse:
                self.ex = pgerror(m)
            elif m.msg_type == p.MsgType.MT_RowDescription:
                self.rowdesc = list(c._replace(name=self.cnn.decode(c.name)) for c in m)
                self.rows = []
            elif m.msg_type == p.MsgType.MT_DataRow:
                self.rows.append(list(c if c is None else self.cnn.decode(c) for c in m))
            elif m.msg_type == p.MsgType.MT_CommandComplete:
                self.cmdtag = self.cnn.decode(m.tag)
            elif m.msg_type == p.MsgType.MT_ReadyForQuery:
                got_ready = True
                break
            elif m.msg_type in self.cnn.async_msgs: # async msg
                self.cnn.got_async_msg(m)
            elif m.msg_type == p.MsgType.MT_CopyInResponse:
                self.cnn.processer = CopyInResponseProcesser(self.cnn, msg_list[idx:])
                return m
            elif m.msg_type == p.MsgType.MT_CopyOutResponse:
                self.cnn.processer = CopyOutResponseProcesser(self.cnn, msg_list[idx:])
                return m
            else:
                # ���ﲻֱ���׳��쳣����Ҫ������ReadyForQuery֮����ܰ����׳���
                self.ex = RuntimeError(self.UnknownMsgErr, m)
        if got_ready:
            return
        msg_list = self.cnn.read_msgs_until_avail()
        return self._process_msg_list(msg_list)
class CopyResponseProcesser(MsgProcesser):
    # msg_list[0] is CopyInResponse or CopyOutResponse msg
    def __init__(self, cnn, msg_list):
        super().__init__(cnn, cnn.processer)
        self.cr_msg = msg_list[0]
        self.msg_list = msg_list[1:]
    def _get_msg_list(self):
        if self.msg_list:
            msg_list = self.msg_list
            self.msg_list = None
        else:
            msg_list = self.cnn.read_msgs()
        return msg_list
class CopyInResponseProcesser(CopyResponseProcesser):
    # ���CopyIn�ɹ��򷵻�True�����򷵻�False��
    def _process(self, data_list):
        for data in data_list:
            data = self.cnn.encode(data)
            m = p.CopyData(data=data)
            self.cnn.write_msgs((m,))
            msg_list = self._get_msg_list()
            for m in msg_list:
                if m.msg_type in self.cnn.async_msgs:
                    self.cnn.got_async_msg(m)
                else: # �쳣��Ϣ(����ErrorResponse)���˳�CopyInģʽ��
                    self.prev_processer.msgs_from_copy.append(m)
            if self.prev_processer.msgs_from_copy:
                return False
        self.cnn.write_msgs((p.CopyDone(),))
        return True
class CopyOutResponseProcesser(CopyResponseProcesser):
    # �������˿����ڷ��ز��ֽ�����ٷ���ErrorResponse�����Ա���鿴QueryProcesser�Ľ�����Ƿ��д���
    def _process(self):
        return list(self.process_iter())
    # һ��һ�����أ����Ƿ�����������������øú������������ݺ���Ҫ�ٵ���reset_processer��
    def process_iter(self):
        self.cnn.write_msgs_until_done()
        while True:
            msg_list = self._get_msg_list()
            for idx, m in enumerate(msg_list):
                if m.msg_type == p.MsgType.MT_CopyData:
                    yield self.cnn.decode(m.data)
                elif m.msg_type == p.MsgType.MT_CopyDone:
                    self.prev_processer.msgs_from_copy.extend(msg_list[idx+1:])
                    return
                elif m.msg_type in self.cnn.async_msgs:
                    self.cnn.got_async_msg(m)
                else: # �쳣��Ϣ(����ErrorResponse)���˳�CopyOutģʽ��
                    self.prev_processer.msgs_from_copy.extend(msg_list[idx:])
                    return
# main
if __name__ == '__main__':
    if len(sys.argv) > 3:
        print('usage: %s [be_addr [listen_addr]]' % sys.argv[0])
        sys.exit(1)
    be_addr = ('127.0.0.1', 5432)
    listen_addr = ('0.0.0.0', 9999)
    if len(sys.argv) >= 2:
        host, port = sys.argv[1].split(':')
        be_addr = (host, int(port))
    if len(sys.argv) >= 3:
        host, port = sys.argv[2].split(':')
        listen_addr = (host, int(port))
    print(be_addr, listen_addr)
        
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.bind(listen_addr)
    listen_s.listen()
    poll = netutils.spoller()
    while True:
        s, peer = listen_s.accept()
        print('accept connection from %s' % (peer,))
        poll.clear()
        try:
            with feconn(s) as fe_c, beconn(be_addr) as be_c:
                while True:
                    m = fe_c.read_startup_msg()
                    if m:
                        be_c.write_msgs([m])
                        break
                    time.sleep(0.01)
                poll.register(fe_c, poll.POLLIN)
                poll.register(be_c, poll.POLLIN)
                while True:
                    poll.poll()
                    if be_c.write_msgs(fe_c.read_msgs()):
                        poll.register(be_c, poll.POLLIN|poll.POLLOUT)
                    else:
                        poll.register(be_c, poll.POLLIN)
                    if fe_c.write_msgs(be_c.read_msgs()):
                        poll.register(fe_c, poll.POLLIN|poll.POLLOUT)
                    else:
                        poll.register(fe_c, poll.POLLIN)
        except Exception as ex:
            print('%s: %s' % (ex.__class__.__name__, ex))
            #traceback.print_tb(sys.exc_info()[2])