#!/bin/env python3
# -*- coding: GBK -*-
#
# ����posix_ipcû���ṩ�����ź���������ͨ��cffiʵ�֡�
# 
import sys, os, errno, struct
import contextlib
import cffi

PROCESS_SHARED = 1
THREAD_SHARED = 0

ffi = cffi.FFI()
ffi.cdef('''
int semsize();
int seminit(char *sem, int pshared, unsigned int value);
int semdestroy(char *sem);
int semgetvalue(char *sem, int *sval);
int sempost(char *sem);
// timeoutָ����ʱֵ����λ���롣
//   <  0.0 : sem_wait
//   == 0.0 : sem_trywait
//   >  0.0 : sem_timedwait
// errno����ֵ: EINTR / EAGAIN / ETIMEOUT
int semwait(char *sem, double timeout);
''')
so = os.path.join(os.path.dirname(__file__), 'libmysem.so')
lib = ffi.dlopen(so)
# 
# python wrapper for lib.*
# 
# decorator to check errno and raise OSError
def check_errno(f):
    def wrapper(*args, **kwargs):
        retval = f(*args, **kwargs)
        if type(retval) == tuple:
            if retval[0] == 0:
                return retval
        elif retval == 0:
            return retval
        ex = OSError()
        ex.errno = ffi.errno
        ex.strerror = os.strerror(ex.errno)
        raise ex
    return wrapper
def semsize():
    return lib.semsize()
# ��ʼ��λ��mmap�е�semaphore
@check_errno
def init(mm, idx, value):
    buf = ffi.from_buffer(mm)
    sem = buf + idx
    return lib.seminit(sem, PROCESS_SHARED, value)
@check_errno
def destroy(mm, idx):
    buf = ffi.from_buffer(mm)
    sem = buf + idx
    return lib.semdestroy(sem)
@check_errno
def _getvalue(mm, idx):
    buf = ffi.from_buffer(mm)
    sem = buf + idx
    v = ffi.new('int *')
    ret = lib.semgetvalue(sem, v)
    return (ret, v[0])
def getvalue(mm, idx):
    return _getvalue(mm, idx)[1]
@check_errno
def post(mm, idx):
    buf = ffi.from_buffer(mm)
    sem = buf + idx
    return lib.sempost(sem)
@check_errno
def wait(mm, idx, timeout):
    buf = ffi.from_buffer(mm)
    sem = buf + idx
    return lib.semwait(sem, timeout)
# 
# sobj = sem(mm, 0)
# with sobj.wait():
#    ....
# 
class Sem(object):
    SIZE = semsize()
    def __len__(self):
        return self.SIZE
    # value=None ��ʾ����ʼ��sem
    def __init__(self, mm, idx, value=1):
        self.mm = mm
        self.idx = idx
        self.init_value = value
        if self.init_value != None:
            init(self.mm, self.idx, value)
    def destroy(self):
        if self.init_value != None:
            destroy(self.mm, self.idx)
    def getvalue(self):
        return getvalue(self.mm, self.idx)
    def post(self):
        post(self.mm, self.idx)
    def wait(self, timeout = -1):
        wait(self.mm, self.idx, timeout)
        return self
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.post()

# ����mmap���ٵ÷�����ٿռ�
def mmsize(itemnum, itemsz):
    return Sem.SIZE + 4 + itemnum * itemsz
#========================================================================================================
# ������һЩλ�����������ڴ��е����ݽṹ
# 
# ������� : �ڹ����ڴ��еĲ���: sem + <�������͵Ĺ�������> + <data>
# 
class ShmObject(object):
    def __init__(self, itemsz, mm, start=0, end=0, semvalue=1, fin=None, fout=None):
        self.itemsz = itemsz
        self.fin = fin
        self.fout = fout
        
        self.mm = mm
        self.mm_start = start
        self.mm_end = end
        if self.mm_end <= 0:
            self.mm_end = len(mm)
        
        self.sem = Sem(mm, start, value)
    def _misc_init(self):
        self.itemnum = (self.mm_end - self.data_idx) // self.itemsz
    def _value_i4(self, idx, *args):
        if args: # set value
            v = args[0]
            self.mm[idx:idx+4] = struct.pack('=i', v)
        else: # get value
            return struct.unpack('=i', self.mm[idx:idx+4])[0]
    def _apply_fin(self, item):
        if self.fin:
            item = self.fin(item)
        if type(item) != bytes or len(item) != self.itemsz:
            raise RuntimeError('wrong item: %s %s' % (item, type(item)))
        return item
    def _apply_fout(self, item):
        if self.fout and item != None: # None��ʾstack/queueΪ��
            item = self.fout(item)
        return item
# 
# Stack : �����ڴ��а���: sem + top +        <data>
#                               |->top_idx   |->data_idx
# 
class Stack(ShmObject):
    # semvalue=None ��ʾ����ʼ��sem��top
    def __init__(self, itemsz, mm, start=0, end=0, semvalue=1, fin=None, fout=None):
        super().__init__(itemsz, mm, start, end, semvalue, fin, fout)
        self.top_idx = self.mm_start + Sem.SIZE
        self.data_idx = self.top_idx + 4
        if semvalue != None:
            self._topvalue(0)
        self._misc_init()
    def _topvalue(self, *args):
        return self._value_i4(self.top_idx, *args)
    def count(self, timeout=-1):
        with self.sem.wait(timeout):
            return self._topvalue()
    def push(self, item, timeout=-1):
        item = self._apply_fin(item)
        with self.sem.wait(timeout):
            topv = self._topvalue()
            if topv >= self.itemnum: # stack is full
                return None
            item_idx = self.data_idx + topv * self.itemsz
            self.mm[item_idx:item_idx+self.itemsz] = item
            self._topvalue(topv + 1)
            return item
    def pop(self, timeout=-1):
        with self.sem.wait(timeout):
            topv, item = self._top()
            if topv > 0:
                self._topvalue(topv - 1)
            return item
    def top(self, timeout=-1):
        with self.sem.wait(timeout):
            return self._top()[1]
    def _top(self):
        topv = self._topvalue()
        if topv <= 0: # stack is empty
            return (topv, None)
        item_idx = self.data_idx + (topv - 1) * self.itemsz
        item = self.mm[item_idx:item_idx+self.itemsz]
        item = self._apply_fout(item)
        return (topv, item)
# 
# Queue : �����ڴ��а���: sem + head + tail + <data>
# ��head/tail�����β��ʱ�����ͷ��ʼ�����tail��headǰ�棬��ôtail��head֮��������һ��item�ռ䣬
# �������item�ռ����ڱ�ʾ�����������������Ҫ�������n��item����ô��Ҫ����n+1��item�Ŀռ䡣
# 
class Queue(ShmObject):
    # semvalue=None ��ʾ����ʼ��sem��head/tail
    def __init__(self, itemsz, mm, start=0, end=0, semvalue=1, fin=None, fout=None):
        super().__init__(itemsz, mm, start, end, semvalue, fin, fout)
        self.head_idx = self.mm_start + Sem.SIZE
        self.tail_idx = self.head_idx + 4
        self.data_idx = self.tail_idx + 4
        if semvalue != None:
            self._headvalue(0)
            self._tailvalue(0)
        self._misc_init()
    def _headvalue(self, *args):
        return self._value_i4(self.head_idx, *args)
    def _tailvalue(self, *args):
        return self._value_i4(self.tail_idx, *args)
    def count(self, timeout=-1):
        with self.sem.wait(timeout):
            headv = self._headvalue()
            tailv = self._tailvalue()
            v = tailv - headv
            v = (v + self.itemnum) % self.itemnum
            return v
    def _isempty(self):
        headv = self._headvalue()
        tailv = self._tailvalue()
        if headv == tailv:
            return (True, headv, tailv)
        else:
            return (False, headv, tailv)
    def _isfull(self):
        headv = self._headvalue()
        tailv = self._tailvalue()
        if (tailv + 1) % self.itemnum == headv:
            return (True, headv, tailv)
        else:
            return (False, headv, tailv)
    def push(self, item, timeout=-1):
        item = self._apply_fin(item)
        with self.sem.wait(timeout):
            isfull, headv, tailv = self._isfull()
            if isfull:
                return None
            item_idx = self.data_idx + tailv * self.itemsz
            self.mm[item_idx:item_idx+self.itemsz] = item
            tailv = (tailv + 1) % self.itemnum
            self._tailvalue(tailv)
            return item
    def _itemat(self, head=True):
        isempty, headv, tailv = self._isempty()
        if isempty:
            return (None, headv, tailv)
        if head:
            item_idx = self.data_idx + headv * self.itemsz
        else:
            item_idx = self.data_idx + ((tailv - 1 + self.itemnum) % self.itemnum) * self.itemsz
        item = self.mm[item_idx:item_idx+self.itemsz]
        item = self._apply_fout(item)
        return (item, headv, tailv)
    def pop(self, timeout=-1):
        with self.sem.wait(timeout):
            item, headv, tailv = self._itemat()
            if headv != tailv:
                headv = (headv + 1) % self.itemnum
                self._headvalue(headv)
            return item
    def head(self, timeout=-1):
        with self.sem.wait(timeout):
            return self._itemat()[0]
    def tail(self, timeout=-1):
        with self.sem.wait(timeout):
            return self._itemat(False)[0]
# main
if __name__ == '__main__':
    pass
