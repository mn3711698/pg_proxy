#!/bin/env python3
# -*- coding: GBK -*-
# 
# ����pgЭ���õ���һЩ��������
# 
import sys, os
import struct
try:
    import cutils
except ImportError:
    cutils = None

# ���\x00��β���ֽڴ��������ֽڴ�����һ��sidx��
# nullbyte��ʾ����ֵ�Ƿ�����β��\x00�ֽڡ�
def get_cstr(buf, sidx, nullbyte=False):
    idx = sidx
    while buf[sidx] != 0:
        sidx += 1
    sidx += 1
    if nullbyte:
        d = buf[idx:sidx]
    else:
        d = buf[idx:sidx-1]
    return d, sidx

if cutils:
    get_byte = cutils.lib.get_byte
    get_short = cutils.lib.get_short
    get_int = cutils.lib.get_int
else:
    def get_byte(buf, sidx):
        return struct.unpack('>b', buf[sidx:sidx+1])[0]
    def get_short(buf, sidx):
        return struct.unpack('>h', buf[sidx:sidx+2])[0]
    def get_int(buf, sidx):
        return struct.unpack('>i', buf[sidx:sidx+4])[0]
def get_nshort(buf, sidx, cnt):
    return struct.unpack('>%dh'%cnt, buf[sidx:sidx+2*cnt])
def get_nint(buf, sidx, cnt):
    return struct.unpack('>%di'%cnt, buf[sidx:sidx+4*cnt])

def put_byte(n):
    return struct.pack('>b', n)
def put_short(n):
    return struct.pack('>h', n)
def put_int(n):
    return struct.pack('>i', n)
def put_nshort(n_list):
    return struct.pack('>%dh'%len(n_list), *n_list)
def put_nint(n_list):
    return struct.pack('>%di'%len(n_list), *n_list)

def get_24X(buf, sidx):
    old_sidx = sidx
    res = []
    cnt = get_short(buf, sidx)
    sidx += 2
    # ��cnt��Сʱ(����<=5)��while�����forҪ�졣
    for i in range(cnt):
        n = get_int(buf, sidx)
        sidx += 4
        if n < 0:
            res.append(None)
        else:
            res.append(buf[sidx:sidx+n])
            sidx += n
    return tuple(res), sidx-old_sidx
def put_24X(v_list):
    data = struct.pack('>h', len(v_list))
    for v in v_list:
        if v is None:
            data += struct.pack('>i', -1)
        else:
            data += struct.pack('>i', len(v)) + v
    return data

def get_X(buf, sidx):
    res = []
    while buf[sidx] != 0:
        s, sidx = get_cstr(buf, sidx)
        res.append(s)
    return res
def put_X(v_list):
    res = b''
    for v in v_list:
        res += v + b'\x00'
    res += b'\x00'
    return res
