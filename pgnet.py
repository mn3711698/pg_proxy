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

# 连接是非阻塞的，除了connect的时候。
class connbase():
    def __init__(self, s):
        self.s = s
        self.s.settimeout(0)
        self.recv_buf = b''
        self.send_buf = b''
        self.readsz = -1 # _read函数每次最多读取多少字节，<=0表示不限。
    def fileno(self):
        return self.s.fileno()
    def close(self):
        self.s.close()
        self.status = 'disconnected'
    # 读取数据直到没有数据可读
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
    # 返回解析后的消息列表。max_msg指定最多返回多少个消息。
    def read_msgs(self, max_msg=0, *, fe):
        self._read()
        if not self.recv_buf:
            return []
        idx, msg_list = p.parse_pg_msg(self.recv_buf, fe=fe)
        if msg_list:
            self.recv_buf = self.recv_buf[idx:]
        return msg_list
    # 返回还剩多少个字节没有发送。msg_list为空则会发送上次剩下的数据。
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
    # 读取第一个消息，如果还没有收到则返回None。
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
        # connect_ex也可能抛出异常，之后需要先检测POLLOUT|POLLERR，
        # POLLERR表示连接失败，此时可通过netutils.get_socket_error获得连接失败的原因。
        # POLLOUT表示连接成功可以发送数据。
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
# 
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
    # read_msgs_until_avail/write_msgs_until_done 现在是循环读写，可能忙等待导致cpu占用，可以用poller来检查是否可读写。
    # 一直读直到有消息为止
    def read_msgs_until_avail(self, max_msg=0):
        msg_list = None
        while not msg_list:
            msg_list = self.read_msgs(max_msg)
        return msg_list
    # 一直写直到写完为止
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
    # 执行查询，如果返回值是CopyResponse则需要调用process继续进行copy操作。
    def query(self, sql):
        sql = self.encode(sql)
        return self.write_msg(p.Query(query=sql)).process()
# 表示ErrorResponse消息的异常，其他错误抛出的是RuntimeError异常。
class pgerror(Exception):
    def __init__(self, errmsg):
        super().__init__(errmsg)
        self.errmsg = errmsg
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
    # 把cnn的processer重置为prev_processer
    def reset_processer(self):
        if self.cnn.processer is self:
            self.cnn.processer = self.prev_processer
class StartupMessageProcesser(MsgProcesser):
    UnknownMsgErr = 'unknown response msg for startup message'
    def __init__(self, cnn):
        super().__init__(cnn)
        self.params = {}
        self.be_keydata = None
    # 返回authtype是Ok/CleartextPasword/MD5Password的Authentication，或者抛出异常。
    # 调用后应该检查cnn.async_msgs[MsgType.MT_NoticeResponse]是否为空。
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
    # 返回(cmdtag, rowdesc, rows)，或者CopyResponse消息，或者抛出异常。
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
        return (self.cmdtag, self.rowdesc, self.rows)
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
                # 这里不直接抛出异常，需要处理到ReadyForQuery之后才能把它抛出。
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
    # 如果CopyIn成功则返回True，否则返回False。
    def _process(self, data_list):
        for data in data_list:
            data = self.cnn.encode(data)
            m = p.CopyData(data=data)
            self.cnn.write_msgs((m,))
            msg_list = self._get_msg_list()
            for m in msg_list:
                if m.msg_type in self.cnn.async_msgs:
                    self.cnn.got_async_msg(m)
                else: # 异常消息(包括ErrorResponse)则退出CopyIn模式。
                    self.prev_processer.msgs_from_copy.append(m)
            if self.prev_processer.msgs_from_copy:
                return False
        self.cnn.write_msgs((p.CopyDone(),))
        return True
class CopyOutResponseProcesser(CopyResponseProcesser):
    # 服务器端可能在返回部分结果后再发送ErrorResponse，所以必须查看QueryProcesser的结果看是否有错误。
    def _process(self):
        return list(self.process_iter())
    # 一条一条返回，不是返回整个结果集。调用该函数处理完数据后需要再调用reset_processer。
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
                else: # 异常消息(包括ErrorResponse)则退出CopyOut模式。
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
