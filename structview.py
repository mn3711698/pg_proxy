#!/bin/env python3
# -*- coding: GBK -*-
# 
# structview : ���ڼ򻯶�дstruct�����ڶ�д�ܳ�һ���ֽڣ�������memoryview�����磺
#   mv = mvfrombuf(mm, 100, 100)
#   mv[:] = .....
# 
import sys, os, re
import struct
import itertools
import collections

__all__ = ['mvfrombuf', 'structview']

def mvfrombuf(buf, start, sz = -1):
    mv = memoryview(buf)
    if sz == -1:
        return mv[start:]
    else:
        return mv[start:start + sz]

class structview(object):
    flag_list = tuple('@=<>!')
    format_list = tuple('bBhHiIlLqQfd')
    # ����4�������ֱ��Ӧ "native order native size" "native order std size" "little order std size" "big order std size"
    @classmethod
    def nat_nat(cls, *args, **kwargs):
        return cls('@', *args, **kwargs)
    @classmethod
    def nat_std(cls, *args, **kwargs):
        return cls('=', *args, **kwargs)
    @classmethod
    def little_std(cls, *args, **kwargs):
        return cls('<', *args, **kwargs)
    @classmethod
    def big_std(cls, *args, **kwargs):
        return cls('>', *args, **kwargs)
    # buf������bytes,bytearray,mmap,�Լ�format='B'��memoryview��
    def __init__(self, flag, format, buf, start = 0, fields = None):
        if flag not in self.__class__.flag_list:
            raise ValueError("Wrong flag:%s" % flag)
        for f in format:
            if f not in self.__class__.format_list:
                raise ValueError("Wrong format:%s" % f)
        self.flag = flag
        self.format = format
        self.size = struct.calcsize(self.flag + self.format)
        self.buf = buf
        self.buf_start = start
        if self.buf_start + self.size > len(buf):
            raise ValueError("buf has not enouth space after idx %d. need %d" % (start, sz))
        # build index. list of (idx, sz)
        self.index = []
        sidx = self.buf_start
        for f in format:
            sz = struct.calcsize(self.flag + f)
            self.index.append((sidx, sz))
            sidx += sz
        self.index = tuple(self.index)
        # fields�������������Ϊ��Ҫ���fields���Ƿ���self�����е����ԡ�
        if not fields:
            fields = ()
        elif type(fields) == str:
            fields = fields.split()
        for fld in fields:
            if fld in self.__dict__:
                raise ValueError("fields can not contain %s" % fld)
        self.fields = tuple(fields)
    def nextpos(self):
        return self.buf_start + self.size
    def __len__(self):
        return len(self.format)
    def _get_ffii(self, idx):
        try:
            return self.format[idx], self.index[idx]
        except IndexError:
            raise IndexError("structview index out of range") from None
        except TypeError:
            raise TypeError("strutview indices must be integer or slice") from None
    def __getitem__(self, idx):
        ff, ii = self._get_ffii(idx)
        t = type(idx)
        if t == int:
            fmt = self.flag + ff
            i = ii
            return struct.unpack(fmt, self.buf[i[0]:i[0]+i[1]])[0]
        elif t == slice:
            res = []
            for f, i in zip(ff, ii):
                fmt = self.flag + f
                v = struct.unpack(fmt, self.buf[i[0]:i[0]+i[1]])[0]
                res.append(v)
            return res
        else:
            raise TypeError("strutview indices must be integer or slice")
    def __setitem__(self, idx, value):
        ff, ii = self._get_ffii(idx)
        t = type(idx)
        if t == int:
            fmt = self.flag + ff
            i = ii
            self.buf[i[0]:i[0]+i[1]] = struct.pack(fmt, value)
        elif t == slice:
            if len(ff) != len(value):
                raise ValueError("wrong len in value")
            for f, i, v in zip(ff, ii, value):
                fmt = self.flag + f
                self.buf[i[0]:i[0]+i[1]] = struct.pack(fmt, v)
        else:
            raise TypeError("strutview indices must be integer or slice")
    def _field2idx(self, field):
        # ��__init__��������ڳ�ʼ��self.fields֮ǰ�ͷ��ʲ����ڵ�����
        if 'fields' not in self.__dict__:
            return -1
        try:
            idx = self.fields.index(field)
        except ValueError:
            idx = -1
        return idx
    def __getattr__(self, name):
        idx = self._field2idx(name)
        if idx == -1:
            raise AttributeError("no attribute:%s" % name)
        return self[idx]
    def __setattr__(self, name, value):
        idx = self._field2idx(name)
        if idx == -1:
            return super().__setattr__(name, value)
        self[idx] = value

# struct_base etc.
__all__ += ['struct_meta', 'struct_base', 'xval', 'Xval', 'def_struct']
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
# xval��ʾ�����ֽڴ����ڴ���xval�����Ҫ�޸���������ֵ��
# c=0��ʾ�ֽڴ���\x00��β����ʱ�ֽڴ��в��ܰ���\x00��
# c>0��ʾ�ֽڴ�ǰ����c���ֽڱ�ʾ�ֽڴ��Ĵ�С����ʱ�ֽڴ����԰���\x00��
# c>0ʱ����Сǰ׺֧�ָ�����������ʾ����û���ֽڴ������������ֵ��ĳЩӦ�ÿ������ر�����塣
class xval(object):
    _c2fmt = [None, 'b', 'h', None, 'i']
    # c=0ʱ�����flags��sz����������
    # sz���ܴ���0��sz<0ʱ��ʾ�Ǹ���ֵ��
    # ���data��xval������ô���ᶪʧ��ֵ����Ϣ��������make����һ��xval�����µ�xval���������Ա�����ֵ����Ϣ��
    def __init__(self, data, c=1, flag='>', sz=0):
        self.data = bytes(data)
        self.c = c
        if self.c not in (0, 1, 2, 4):
            raise ValueError('c should be 0|1|2|4')
        if self.c == 0:
            if b'\x00' in self.data:
                raise ValueError(r'xval(format 0) can not contain \x00')
        self.flag = flag
        if self.flag not in struct_meta.flag_list:
            raise ValueError('unknown flag:%s' % self.flag)
        
        self.sz = sz
        if self.sz > 0:
            raise ValueError('sz can not be greater than 0')
        if self.c == 0 and self.sz < 0:
            raise ValueError('sz can not be less than 0 while c is 0')
        if self.c > 0 and self.sz < 0:
            self.data = b''
    def __repr__(self):
        if self.sz < 0:
            return "<xval data:-1>"
        else:
            return "<xval data:{}>".format(self.data,)
    def _info(self):
        return "<xval data:{} c:{} flag:'{}' sz:{}>".format(self.data, self.c, self.flag, self.sz)
    def __bytes__(self):
        return self.data
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        return self.data[idx]
    def make(self, c, flag):
        if c == self.c and flag == self.flag:
            return self
        if c == 0:
            return xval(self.data, c, flag)
        else:
            return xval(self.data, c, flag, self.sz)
    def tobuf(self):
        if self.c == 0:
            return self.data + b'\x00'
        else:
            fmt = self.flag + self._c2fmt[self.c]
            if self.sz < 0:
                return struct.pack(fmt, self.sz)
            else:
                return struct.pack(fmt, len(self.data)) + self.data
    @classmethod
    def frombuf(cls, c, flag, buf, sidx):
        if c == 0:
            data, sidx = get_cstr(buf, sidx)
            sz = 0
        else:
            fmt = flag + cls._c2fmt[c]
            sz = struct.unpack(fmt, buf[sidx:sidx+c])[0]
            sidx += c
            data = b''
            if sz > 0:
                data = buf[sidx:sidx+sz]
                sidx += sz
                sz = 0
        return cls(data, c, flag, sz), sidx
# Xval��ʾ����ֽڴ���
# c1=0ʱ�������ֽڴ���\x00��β������XvalҲ��\x00��β�����Ե����ֽڴ��������ǿմ���
# c1>0ʱ����ͷ��c1���ֽڱ�ʾ�ж��ٸ�����c2��ʾ�������ĸ�ʽ����ʹc2=0Ҳ֧�ֿմ���
# **��Ҫ�ر�ע�����**��
#   ���data_list������c2>0��xval����ô��c2=0����Xval��ʱ��ᵼ�¸�ֵ����Ϣ��ʧ����ֵ�����ɿմ���
#   ������������Զ�Ӧ��c1/c2����ʼ��Xval(���Ե���struct_base.fmt���������c1/c2)��
#   ���߳�ʼ��Xval��ʱ����c2=0�����԰�c1/c2��ȱʡֵ��Ϊ��0��
class Xval(object):
    _c2fmt = [None, 'b', 'h', None, 'i']
    def __init__(self, data_list, c1=1, c2=1, flag='>'):
        if c1 not in (0, 1, 2, 4):
            raise ValueError('wrong c1 for Xval')
        if c1 == 0 and c2 != 0:
            raise ValueError('c2 should be 0 while c1 is 0')
        self.c = c1
        
        self.xval_list = []
        for d in data_list:
            if isinstance(d, xval):
                d = d.make(c2, flag)
            else:
                d = xval(d, c2, flag)
            self.xval_list.append(d)
        self.flag = flag
        if c1 == 0 and any(len(xv)==0 for xv in self.xval_list):
            raise ValueError('Xval does not support empty byte string while c1=0')
    def __repr__(self):
        return "<Xval xval_list:{}>".format(self.xval_list)
    def _info(self):
        return "<Xval xval_list:{} c:{} flag:'{}'>".format(len(self.xval_list), self.c, self.flag)
    def __len__(self):
        return len(self.xval_list)
    def __getitem__(self, idx):
        return self.xval_list[idx]
    def __iter__(self):
        yield from self.xval_list
    def tobuf(self):
        res = b''
        if self.c > 0:
            fmt = self.flag + self._c2fmt[self.c]
            res += struct.pack(fmt, len(self.xval_list))
        for v in self.xval_list:
            res += v.tobuf()
        if self.c == 0:
            res += b'\x00'
        return res
    @classmethod
    def frombuf(cls, c1, c2, flag, buf, sidx):
        data_list = []
        if c1 == 0:
            while buf[sidx] != 0:
                d, sidx = xval.frombuf(c2, flag, buf, sidx)
                data_list.append(d)
            sidx += 1
        else:
            fmt = flag + cls._c2fmt[c1]
            cnt = struct.unpack(fmt, buf[sidx:sidx+c1])[0]
            sidx += c1
            for i in range(cnt):
                d, sidx = xval.frombuf(c2, flag, buf, sidx)
                data_list.append(d)
        return cls(data_list, c1, c2, flag), sidx
# struct attribute descriptor
# ����ʵ��__get__������ͨ������ʻ᷵��������������ͨ��instance���ʵĻ��᷵��instance�ֵ����ͬ�����ԡ�
class struct_attr_descriptor(object):
    def __init__(self, name, fmt_spec):
        self.name = name
        self.fmt_spec = fmt_spec
    # Ŀǰֻ����Ƿ��������Լ����еĳ��ȣ�
    # �����ֵ�Ƿ���Ч�����ֵ��Ч��ôtobytes�������׳��쳣��
    def __set__(self, instance, val):
        if getattr(instance, '_check_assign', True):
            n, flag, fmt_list, fmt_str, fmt_info = self.fmt_spec
            sz = len(fmt_str)
            if n == 0:
                if sz > 1:
                    self._check_sequence(val, sz)
            else:
                if n < 0:
                    n = instance._field_ref(n)
                self._check_sequence(val, n)
                if sz > 1:
                    for item in val:
                        self._check_sequence(item, sz)
            self._apply_instance_check(instance, val)
        instance.__dict__[self.name] = val
    # sz <  0 ֻ����Ƿ�������
    # sz >= 0 ����Ƿ������У����Ҵ�С�Ƿ���sz
    def _check_sequence(self, v, sz = -1):
        if not isinstance(v, collections.Sequence):
            raise ValueError('val(%s) is not sequence' % v)
        if sz >= 0 and len(v) != sz:
            raise ValueError('len of val(%s) is not equal %s' % (v, sz))
    # ���instance�Ƿ��ṩ����صļ�麯��������о͵�������
    def _apply_instance_check(self, instance, val):
        m = getattr(instance, '_check_'+self.name, None)
        if m:
            m(val)
# meta class for struct_base
# _formats��_fields����ͬʱָ�������߶���ָ�����������ָ������ô�̳л��ࡣ
class struct_meta(type):
    flag_list = structview.flag_list
    format_list = structview.format_list + tuple('sxXa')
    def __repr__(self):
        return "<class '%s.%s' _formats='%s' _fields='%s'>" % (self.__module__, self.__name__, self._formats_original, self._fields_original)
    def __new__(cls, name, bases, ns):
        if '_formats' not in ns and '_fields' not in ns:
            return super().__new__(cls, name, bases, ns)
        if '_formats' not in ns or '_fields' not in ns:
            raise ValueError('class %s should has _formats and _fields' % name)
        if '_field2idx' in ns:
            raise ValueError('class %s should not define _field2idx' % name)
        ns['_formats_original'] = ns['_formats']
        ns['_fields_original'] = ns['_fields']
        
        _fields = ns['_fields']
        if type(_fields) == str:
            _fields = _fields.split()
        if set(_fields) & set(ns):
            raise ValueError('_fields can not contain class attribute')
        for fn in _fields:
            if fn[0] == '_':
                raise ValueError('fieldname in _fields can not starts with undercore')
        ns['_fields'] = tuple(_fields)
        field2idx = {}
        for idx, fn in enumerate(ns['_fields']):
            field2idx[fn] = idx
        ns['_field2idx'] = field2idx
        
        _formats = ns['_formats']
        if type(_formats) == str:
            _formats = _formats.split()
        _formats_res = []
        for idx, fmt in enumerate(_formats):
            # check 'a' format
            if 'a' in fmt:
                if len(fmt) != 2 or (idx + 1) != len(_formats):
                    raise ValueError("wrong fmt '%s'. format 'a' should be last and '<flag>a'." % fmt)
            _formats_res.append(cls._parse_format(fmt, idx))
        ns['_formats'] = tuple(_formats_res)
        
        if len(ns['_formats']) != len(ns['_fields']):
            raise ValueError('_formats should be equal with _fields')
        # add descriptor
        for fn, fmt_spec in zip(ns['_fields'], ns['_formats']):
            ns[fn] = struct_attr_descriptor(fn, fmt_spec)
        return super().__new__(cls, name, bases, ns)
    # �������ִ�n; idx��ǰ������fmt�ǵڼ���; emptyval��nΪ�մ�ʱ��Ӧ��ֵ
    @classmethod
    def _process_n(cls, n, fmt, idx, emptyval):
        if n == '-0':
            if idx == 0:
                raise ValueError('first fmt(%s) can not contain -0' % fmt)
            else:
                n = -idx
        else:
            n = int(n) if n else emptyval
            if n < 0 and -n > idx:
                raise ValueError('fmt(%s) reference attribute behind it' % fmt)
        return n
    @classmethod
    def _parse_format(cls, fmt, idx):
        p_split = '([%s])' % ''.join(cls.flag_list)
        split_res = re.split(p_split, fmt)
        if len(split_res) != 3:
            raise ValueError('wrong format:%s' % fmt)
        n, flag, fmt = split_res
        n = cls._process_n(n, ''.join(split_res), idx, 0)
                
        pitem = '%s[%s]' % (r'-?\d*', ''.join(cls.format_list))
        p = r'^(%s)+$' % pitem
        if not re.match(p, fmt):
            raise ValueError('wrong format:%s' % fmt)
        fmt_list = re.findall(pitem, fmt)
        fmt_list_new = []
        fmt_str = ''
        fmt_info = []
        for fi in fmt_list:
            c, f = fi[:-1], fi[-1:]
            if f == 's':
                c = cls._process_n(c, fmt, idx, 1)
                fmt_str += f
                fmt_info.append(c)
                if c < 0: # ԭʼc������-0��������Ҫ�޸�fi
                    fi = '%s%s' % (c, f)
            elif f == 'x':
                c = int(c) if c else 0
                if c not in (0, 1, 2, 4):
                    raise ValueError('the prefix n of x in %s should be 0|1|2|4' % fmt)
                fmt_str += f
                fmt_info.append(c)
                fi = '%s%s' % (c, f)
            elif f == 'X':
                if not c:
                    c = '00'
                elif len(c) == 1:
                    c = c*2
                elif len(c) > 2:
                    raise ValueError('wrong prefix n(%s) for X in %s' % (c, fmt))
                c1, c2 = int(c[0]), int(c[1])
                if c1 not in (0, 1, 2, 4) or c2 not in (0, 1, 2, 4):
                    raise ValueError('the prefix n of X in %s should be 0|1|2|4' % fmt)
                if c1 == 0 and c2 != 0:
                    raise ValueError('the prefix n can not be 0(1|2|4) in %s' % fmt)
                fmt_str += f
                fmt_info.append(c)
                fi = '%s%s%s' % (c1, c2, f)
            else:
                c = int(c) if c else 1
                if c <= 0:
                    raise ValueError('the prefix n of %s in %s should not be less than 0' % (f,fmt))
                fmt_str += f*c
                fmt_info.extend([c]*c)
            fmt_list_new.append(fi)
        return (n, flag, tuple(fmt_list_new), fmt_str, tuple(fmt_info))
    
# 
# _formats : ָ����ʽ
#     [n]<flag>ff...  : nָ�������ģʽ�ظ���ȡ���Σ�0/1����ʾ��ȡһ�Σ�����1�Ƿ��س���Ϊ1���б���
#                       ���n<0�����ʾ�ӵ�-n-1�����Զ�ȡnֵ�����n=-0�����ʾ��ǰһ�����Զ�ȡnֵ��
# flag����ָ������Чֵ��struct_meta.flag_list�����ֵ��
# f�ǵ����ַ���������struct_meta.format_list������ַ���fǰ�����������ǰ׺n������s��n<0�ĺ���ͬǰ��һ��
# fҲ������������Щ�Զ�����ַ�: 
#     [n]x : ��������0��ʾ�ֽڴ���\x00��β��(1|2|4)��ʾ��ͷn���ֽ�Ϊ�ֽڴ��Ĵ�С��
#     [n]X : �������n(c1c2)����2�����֣������һ������c1Ϊ0��ڶ�������c2Ҳ����Ϊ0��
#                    00��ʾ����ֽڴ���\x00��β�������ֽڴ�Ҳ��\x00��β��Ҳ����������2��\x00����֧�ֿմ���
#                    c1>0���ʾ��ͷc1���ֽڱ�ʾ�ֽڴ�����Ŀ��c2=0��ʾ�ֽڴ���\x00��β��c2>0��ʾ�ֽڴ���ǰ��c2���ֽڱ�ʾ�ֽڴ��Ĵ�С��
#                    ����00��������ʽ��ʵ������x�����棬����'>11X'��'>b -0>1x'���Դﵽͬ����Ч����
#     a    : ��ʾ����ʣ�µ��������ݣ�ֻ�ܷ���_formats�����
# struct_meta���_formatsת����fmt_spec���б���fmt_spec����5���֣�
#     n, flag, fmt_list : fmt_list�ǵ���fmt������
#     fmt_str : ����������ǰ׺�ĸ�ʽ�ַ���ɵĴ������ڷ�s/x/X��ʽ�ַ��������ǰ׺������չ������3i -> iii
#     fmt_info : ��¼fmt_str�ж�Ӧ��ʽ�ַ�ǰ�������
# ����:
#   '>i' : ���ص�������
#   '1>i' : ���ذ���һ���������б�
#   '>ii' : ���ذ��������������б�
#   '2>i' : ͬ��
#   '2>ii' : �����б����б����б��а�����������Ϊ2�������б�������[[1,2],[3,4]]
# 
# _fields : _formats�ж�Ӧ��������������ܰ���buf�Լ������е����ԡ�
# 
# ����__init__��buf����󲿷ֱ����Ǹ������Ľṹ,�����Խ����ʡ����_formats�������'a'����ôbuf����ֻ����һ���ṹ��
# 
class struct_base(metaclass=struct_meta):
    _check_assign = True # ���ΪTrue���߲����壬��ô���������ｫ�������ֵ
    _formats = ''
    _fields = ''
    # ���field��Ӧ��format spec�еĵ�idx����format
    @classmethod
    def fmt(cls, field, idx=0):
        i = cls._field2idx[field]
        fmt_list = cls._formats[i][2]
        fi = fmt_list[idx]
        n, f = fi[:-1], fi[-1:]
        if f == 'X':
            return int(n[0]), int(n[1]), f
        elif f == 'x':
            return int(n), f
        n = int(n) if n else 1
        return n, f
    # 
    def __init__(self, buf=None, **kwargs):
        if buf is not None and kwargs:
            raise ValueError('buf and kwargs can not be given meanwhile')
        # ����buf��kwargs����ָ�����ڴ���һ���ն���֮������������ֵ�����Ǳ��밴��_fields�����˳��ֵ��
        #if buf is None and not kwargs:
        #    raise ValueError('buf or kwargs should be given')
        if buf:
            self._init_from_buf(bytes(buf))
        else:
            self._init_from_kwargs(kwargs)
    def _init_from_buf(self, buf):
        sidx = 0
        for fmt_spec, field in zip(self._formats, self._fields):
            sidx = self._read(fmt_spec, field, buf, sidx)
        self._sidx = sidx
    def _init_from_kwargs(self, kwargs):
        if set(kwargs) - set(self._fields):
            raise ValueError('kwargs contains keys which are not in %s' % self._fields)
        # ��_fields�����˳��ֵ
        for k in self._fields:
            if k in kwargs:
                setattr(self, k, kwargs[k])
    def _field_ref(self, n):
        fn = self._fields[(-n)-1]
        n = getattr(self, fn, None)
        if not isinstance(n, int):
            raise ValueError('field(%s) value should be int' % fe)
        return n
    def _read(self, fmt_spec, field, buf, sidx):
        n, flag, fmt_list, fmt_str, fmt_info = fmt_spec
        if n == 0:
            v, sidx = self._read_one(flag, fmt_list, buf, sidx)
        else:
            if n < 0: # ������ܷ���n==0ǰ�棬��Ϊ_field_ref���ܷ���0
                n = self._field_ref(n)
            v = []
            for i in range(n):
                x, sidx =self._read_one(flag, fmt_list, buf, sidx) 
                v.append(x)
        setattr(self, field, v)
        return sidx
    # ����(val, next_sidx)
    def _read_one(self, flag, fmt_list, buf, sidx):
        res = []
        for fmt in fmt_list:
            f = fmt[-1]
            v, sidx = self._read_map[f](self, flag, fmt, buf, sidx)
            res.extend(v)
        if len(res) == 1:
            return res[0], sidx
        return res, sidx
    def __bytes__(self):
        return self.tobytes()
    def tobytes(self):
        res = b''
        for fmt_spec, field in zip(self._formats, self._fields):
            res += self._write(fmt_spec, field)
        return res
    def field_assigned(self, field):
        fval = getattr(self, field)
        return not isinstance(fval, struct_attr_descriptor)
    def _write(self, fmt_spec, field):
        n, flag, fmt_list, fmt_str, fmt_info = fmt_spec
        fval = getattr(self, field)
        if isinstance(fval, struct_attr_descriptor):
            raise ValueError('attribute(%s) is not assigned' % field)
        leftval = []
        if n == 0: # fval�����ǵ�ֵ�������С�
            res, leftval = self._write_one(flag, fmt_list, fval)
        else: # fval���������У�fval�е�Ԫ�ؿ����ǵ�ֵ�������С�
            if n < 0:
                n = self._field_ref(n)
            res = b''
            for i in range(n):
                d, leftval = self._write_one(flag, fmt_list, fval[i])
                if leftval:
                    break
                res += d
        if leftval:
            raise ValueError('attribute(%s) has too many values:%s' % (field, leftval))
        return res
    def _write_one(self, flag, fmt_list, val):
        if type(val) in (str, bytes, bytearray, xval, Xval) or not isinstance(val, collections.Sequence):
            val = [val]
        res = b''
        for fmt in fmt_list:
            f = fmt[-1]
            d, val = self._write_map[f](self, flag, fmt, val)
            res += d
        return res, val
    # 
    # read map & write map
    # ��Ϊ��ͨ���ֵ�_read_map��������Щ���������Բ���ͨ��������Э�顣
    # ����ڵ��õ�ʱ����Ҫ�ṩself������
    # 
    # �������ִ�n�����nΪ�����ȡ��Ӧ���Ե�ֵ�����Ϊ�մ��򷵻�emptyval
    def _process_n(self, n, emptyval):
        n = int(n) if n else emptyval
        if n < 0:
            n = self._field_ref(n)
        return n
    # _read_xxx��������ֵ�б�����һ��sidx
    def _read_s(self, flag, fmt, buf, sidx):
        n = self._process_n(fmt[:-1], 1)
        fmt = '%s%s%s' % (flag, n, fmt[-1])
        sz = struct.calcsize(fmt)
        res = struct.unpack(fmt, buf[sidx:sidx+sz])
        return res, sidx+sz
    def _read_std(self, flag, fmt, buf, sidx):
        fmt = flag + fmt
        sz = struct.calcsize(fmt)
        res = struct.unpack(fmt, buf[sidx:sidx+sz])
        return res, sidx+sz
    def _read_x(self, flag, fmt, buf, sidx):
        c = int(fmt[0])
        v, sidx = xval.frombuf(c, flag, buf, sidx)
        return [v], sidx
    def _read_X(self, flag, fmt, buf, sidx):
        c1, c2 = int(fmt[0]), int(fmt[1])
        v, sidx = Xval.frombuf(c1, c2, flag, buf, sidx)
        return [v], sidx
    def _read_a(self, flag, fmt, buf, sidx):
        v = buf[sidx:]
        return [v], len(buf)
    _read_map = dict(zip(structview.format_list, itertools.repeat(_read_std)))
    _read_map['s'] = _read_s
    _read_map['x'] = _read_x
    _read_map['X'] = _read_X
    _read_map['a'] = _read_a
    del _read_s, _read_std, _read_x, _read_X, _read_a
    # _write_xxx�������ؽ���ֽڴ���ʣ���ֵ�б�������fmt��valȡ��Ҫ�������������val�Ǹ����С�
    # ����s��ʽ��strut.pack��ʱ������������ֽڴ�̫�����ضϣ����̫�������\x00���
    # ��struct.unpack��ʱ�򣬱��������ͬ���ȵ��ֽڴ���
    def _write_s(self, flag, fmt, val):
        n = self._process_n(fmt[:-1], 1)
        fmt = '%s%s%s' % (flag, n, fmt[-1])
        d = bytes(val[0])
        res = struct.pack(fmt, d)
        return res, val[1:]
    def _write_std(self, flag, fmt, val):
        n = self._process_n(fmt[:-1], 1)
        res = struct.pack(flag+fmt, *val[:n])
        return res, val[n:]
    def _write_x(self, flag, fmt, val):
        c = int(fmt[0])
        d = val[0]
        if isinstance(d, xval):
            d = d.make(c, flag)
        else:
            d = xval(d, c, flag)
        res = d.tobuf()
        return res, val[1:]
    def _write_X(self, flag, fmt, val):
        c1, c2 = int(fmt[0]), int(fmt[1])
        # val[0]�����Ǹ�iterable��Xval֧��iterableЭ��
        res = Xval(val[0], c1, c2, flag).tobuf()
        return res, val[1:]
    def _write_a(self, flag, fmt, val):
        res = bytes(val[0])
        return res, val[1:]
    _write_map = dict(zip(structview.format_list, itertools.repeat(_write_std)))
    _write_map['s'] = _write_s
    _write_map['x'] = _write_x
    _write_map['X'] = _write_X
    _write_map['a'] = _write_a
    del _write_s, _write_std, _write_x, _write_X, _write_a
# utility func to define struct_base derived class
def def_struct(name, formats, fields):
    return struct_meta(name, (struct_base,), {'_formats':formats, '_fields':fields})
# examples for testing
__all__ += ['S1', 'S2']
class S1(struct_base):
    _formats = '>i -0>xi'
    _fields = 'num name_age_list'
class S2(struct_base):
    _formats = '>i 1>i >ii 2>ii'
    _fields = 'v1 v2 v3 v4'
# main
if __name__ == '__main__':
    sv = structview('=', 'iii', bytearray(12), fields = 'a b c')
    sv.a = 1; sv.b = 2; sv.c = 3
    print(list(sv))
    x, y, z = sv
    sv[0] += 1
    sv[1] += 1
    sv[2] += 1
    print(list(sv))