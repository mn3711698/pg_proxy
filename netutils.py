#!/bin/env python3
# -*- coding: GBK -*-
# 
# poller base class
# 
import sys, os, socket, struct
import select
import logging

if os.name == 'posix':
    NONBLOCK_SEND_RECV_OK = (errno.EAGAIN, errno.EWOULDBLOCK)
    NONBLOCK_CONNECT_EX_OK = (errno.EINPROGRESS, 0)
else:
    NONBLOCK_SEND_RECV_OK = (errno.EAGAIN, errno.EWOULDBLOCK, errno.WSAEWOULDBLOCK)
    NONBLOCK_CONNECT_EX_OK = (errno.WSAEWOULDBLOCK, 0)

class poller_base(object):
    def __init__(self):
        self.fd2objs = {}
    def _register(self, fobj, eventmask):
        fd = fobj
        if type(fobj) != int:
            fd = fobj.fileno()
        
        obj = self.fd2objs.get(fd, None)
        if obj and obj[0] != fobj:
            logging.warning('register with same fd(%d) but with two different obj(%s %s)', fd, obj, fobj)
        
        exist = fd in self.fd2objs
        self.fd2objs[fd] = (fobj, eventmask)
        return (fd, exist)
    def _modify(self, fobj, eventmask):
        fd = fobj
        if type(fobj) != int:
            fd = fobj.fileno()
        if fd not in self.fd2objs:
            ex = IOError()
            ex.errno = errno.ENOENT
            raise ex
        self.fd2objs[fd] = (fobj, eventmask)
        return (fd, )
    def _unregister(self, fobj):
        fd = fobj
        if type(fobj) != int:
            fd = fobj.fileno()
        self.fd2objs.pop(fd)
        return (fd, )
    def _poll(self, *args, **kwargs):
        raise SystemError('BUG: the derived class(%s) should implement _poll' % (type(self), ))
    def poll(self, timeout = None, *args, **kwargs):
        while True:
            try:
                ret = self._poll(timeout, *args, **kwargs)
            except OSError as ex:
                if ex.errno == errno.EINTR:
                    continue
                raise
            return ret
    def close(self):
        pass
# 
# ����select.select
# 
class spoller(poller_base):
    POLLIN =  0x01
    POLLOUT = 0x02
    POLLERR = 0x04
    def __init__(self):
        super().__init__()
    def register(self, fobj, eventmask):
        super()._register(fobj, eventmask)
    def modify(self, fobj, eventmask):
        super()._modify(fobj, eventmask)
    def unregister(self, fobj):
        super()._unregister(fobj)
    def _poll(self, timeout = None):
        if timeout != None and timeout < 0: # ��ֵ��ʾblock�����poll/epoll��ͬ��
            timeout = None
        r_list = []
        w_list = []
        e_list = []
        mask2list = [(self.POLLIN, r_list), (self.POLLOUT, w_list), (self.POLLERR, e_list)]
        for k in self.fd2objs:
            m = self.fd2objs[k][1]
            for i in mask2list:
                if m & i[0]:
                    i[1].append(k)
        #logging.debug('select: %s %s %s %s', r_list, w_list, e_list, timeout)
        x = select.select(r_list, w_list, e_list, timeout)
        
        res = {}
        masks = [self.POLLIN, self.POLLOUT, self.POLLERR]
        for idx in range(3):
            for fd in x[idx]:
                obj = self.fd2objs[fd][0]
                mask = res.get(obj, 0)
                res[obj] = mask | masks[idx]
        res_list = []
        for obj in res:
            res_list.append((obj, res[obj]))
        return res_list
# 
# ����select.poll
# 
class poller(poller_base):
    POLLIN  = select.POLLIN
    POLLOUT = select.POLLOUT
    POLLERR = select.POLLERR
    def __init__(self):
        super().__init__()
        self.p = select.poll()
    def register(self, fobj, eventmask):
        ret = super()._register(fobj, eventmask)
        self.p.register(ret[0], eventmask)
    def modify(self, fobj, eventmask):
        ret = super()._modify(fobj, eventmask)
        self.p.modify(ret[0], eventmask)
    def unregister(self, fobj):
        ret = super()._unregister(fobj)
        self.p.unregister(ret[0])
    def _poll(self, timeout = None):
        res = self.p.poll(timeout)
        res_list = []
        for fd, event in res:
            res_list.append((self.fd2objs[fd], event))
        return res_list
# 
# ����select.epoll
# 
class epoller(poller_base):
    POLLIN  = select.EPOLLIN
    POLLOUT = select.EPOLLOUT
    POLLERR = select.EPOLLERR
    def __init__(self):
        super().__init__()
        self.p = select.epoll()
    def register(self, fobj, eventmask):
        ret = super()._register(fobj, eventmask)
        if ret[1]:
            self.p.unregister(ret[0])
        self.p.register(ret[0], eventmask)
    def modify(self, fobj, eventmask):
        ret = super()._modify(fobj, eventmask)
        self.p.modify(ret[0], eventmask)
    def unregister(self, fobj):
        ret = super()._unregister(fobj)
        self.p.unregister(ret[0])
    def _poll(self, timeout = None, maxevents = -1):
        if timeout == None:
            timeout = -1
        res = self.p.poll(timeout = timeout, maxevents = maxevents)
        res_list = []
        for fd, event in res:
            res_list.append((self.fd2objs[fd], event))
        return res_list
    def close(self):
        self.p.close()
        super().close()
# ������Ӧ���ȼ�鷵��ֵ�Ƿ���None������None��ʾselect���ؼٵĿɶ��źŻ��߿ɶ�������checksumʧ�ܣ���Ҫ�Է��ش���
def myrecv(s, bufsize):
    try:
        data = s.recv(bufsize)
    except OSError as ex:
        if ex.errno in NONBLOCK_SEND_RECV_OK:
            return None
        raise
    return data
# 
# ͨ��unix domain socket����ͨ�ţ����Դ��ݾ������Ϣ�Լ��ļ���������
# ��Ϣ��ʽ��һ�ֽڵ���Ϣ���� + �ĸ��ֽڵ���Ϣ����(�������ĸ��ֽ�) + ��Ϣ���ݡ�
# 'f'���͵���Ϣ��������ļ���������
# 
class uds_ep(object):
    FDSIZE = 4
    MAXFD = 100
    def __init__(self, x):
        if type(x) == socket.socket:
            self.s = x
        else:
            self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.s.connect(x)
        self.s.settimeout(0)
        
        self.recv_msg_header = b''
        self.recv_msg_data = b''
        self.recv_msg_fdlist = []
        
        self.send_msg_list = [] # ��������Ϣ�б�list of (idx, data, fdlist)
    def fileno(self):
        return self.s.fileno()
    def close(self):
        self.s.close()
    # 
    # �ڵ��øú���ǰ����ȷ��socket�ɶ���
    # ����ֵ (len, msg)���׳��쳣��ʾ�������ˣ�����close���ˡ�
    # .) len=-1��ʾ������Ϣ�Ѿ������꣬��ʱmsgΪ(msg_type, msg_data, fdlist)��
    # .) len>0��ʾ���ν����˶������ݣ���������Ϣ��û�н����ꡣ
    # .) len=0��ʾ��Ȼpoll���ؿɶ��¼������ǻ���û�����ݿɶ���
    # 
    def recv(self):
        n = 5 - len(self.recv_msg_header)
        if n > 0:
            data = myrecv(self.s, n)
            if data == None:
                return (0, None)
            if not data:
                raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
            self.recv_msg_header += data
            return (len(data), None)
        
        msg_type = self.recv_msg_header[:1]
        msg_len = struct.unpack('>i', self.recv_msg_header[1:])[0]
        n = msg_len - 4 - len(self.recv_msg_data)
        if n > 0:
            data = myrecv(self.s, n)
            if data == None:
                return (0, None)
            if not data:
                raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
            self.recv_msg_data += data
            if len(data) == n and msg_type != b'f':
                ret = (-1, (msg_type, self.recv_msg_data, self.recv_msg_fdlist))
                self.recv_msg_header = b''
                self.recv_msg_data = b''
                self.recv_msg_fdlist = []
                return ret
            else:
                return (len(data), None)
        
        if msg_type == b'f':
            data, ancdata, flags, addr = self.s.recvmsg(1, socket.CMSG_LEN(self.MAXFD*self.FDSIZE))
            for cmsg in ancdata:
                fddata = cmsg[2]
                tail_len = len(fddata) % self.FDSIZE
                if tail_len:
                    logging.warning('found truncated fd:%s %d', fddata, tail_len)
                fdcnt = len(fddata) // self.FDSIZE
                fds = struct.unpack('%di'%fdcnt, fddata[:len(fddata)-tail_len])
                self.recv_msg_fdlist.extend(fds)
        
        ret = (-1, (msg_type, self.recv_msg_data, self.recv_msg_fdlist))
        self.recv_msg_header = b''
        self.recv_msg_data = b''
        self.recv_msg_fdlist = []
        return ret
    # 
    # ����Ҫ������Ϣ��ʱ���ȵ���put_msg����Ϣ�ŵ������Ͷ��У�Ȼ����select/poll/epoll����Ƿ��д������д��ʱ���ٵ���send������
    # ע�⣺�����������������ô��Ҫ�ڵ���put_msg֮������close�������������ڵ���send����֮�����Ƿ��ѷ��ͣ�����֮��ſ���close��
    # 
    def put_msg(self, msg_type, msg_data, fdlist = None):
        if (msg_type != b'f' and fdlist) or (msg_type == b'f' and not fdlist):
            raise SystemError("BUG: fdlist should be empty while msg_type is not b'f', and fdlist should not be empty while msg_type is b'f'. (%s %s %s)" % (msg_type, msg_data, fdlist))
        data = msg_type + struct.pack('>i', len(msg_data)+4) + msg_data
        self.send_msg_list.append([0, data, fdlist])
    # 
    # ����None��ʾ����Ҫ�ټ���Ƿ��д��Ҳ���Ƕ��������ˡ�
    # ����׳�OSError���Ǿ�˵���������ˣ�����close���ˡ�
    # 
    def send(self):
        if not self.send_msg_list:
            return None
        msg = self.send_msg_list[0]
        if msg[0] < len(msg[1]):
            n = self.s.send(msg[1][msg[0]:])
            msg[0] += n
            if msg[0] < len(msg[1]) or msg[2]:
                return 'w'
            # msg�ѷ����겢������fdlistΪ��
            self.send_msg_list.remove(msg)
            if self.send_msg_list:
                return 'w'
            else:
                return None
        # ����fdlist
        fdlist = msg[2]
        fddata = struct.pack('%di'%len(fdlist), *fdlist)
        self.s.sendmsg([b'z'], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fddata)])
        self.send_msg_list.remove(msg)
        if self.send_msg_list:
            return 'w'
        else:
            return None
    # 
    # ����ļ��������Ƿ��Ѿ����͡�ֻ�з���֮��ſ���close�ļ���������
    # 
    def fd_is_sent(self, fd):
        for msg in self.send_msg_list:
            if fd in msg[2]:
                return False
        return True
# main
if __name__ == '__main__':
    pass

