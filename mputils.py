#!/bin/env python3
# -*- coding: GBK -*-
# 
# meta programming��ص�һЩ�Ƚ�ͨ�õĴ���
# 
import functools
import collections

# �����ظ���ֵ��dict
class NoRepeatAssignMap(dict):
    def __setitem__(self, key, val):
        if key in self:
            raise ValueError('key(%s) already in dict. val is %s' % (key, val))
        super().__setitem__(key, val)

def assert_no_attr(obj, *attnames):
    for an in attnames:
        if hasattr(obj, an):
            raise ValueError('%s already has attribute %s' % (obj, an))
# ���iterfn/getfnΪNone����ô����__iter__/__getitem__�����getfn��None����ô��Ҫ����__len__������
# ���iterfn/getfnΪ�մ���������Ϊget_<restype>s��get_<restype>�����restype=None�򱨴�
# ���restypeΪNone����ôiterfn/getfn����Ϊ�մ�����ʱ���ᴴ��namedtuple���͡�
# f�������е�ÿ��������������һ���ٴ���restype����ֱ�ӷ��ء�
def SeqAccess(cls=None, *, attname, iterfn=None, getfn=None, restype=None, resfields='', f=lambda x:x):
    if cls is None:
        return functools.partial(SeqAccess, attname=attname, iterfn=iterfn, getfn=getfn, restype=restype, resfields=resfields, f=f)
    
    t = None
    if restype:
        assert_no_attr(cls, restype)
        t = collections.namedtuple(restype, resfields)
        setattr(cls, restype, t)
    
    if iterfn is None:
        iterfn = '__iter__'
    elif iterfn == '':
        if restype:
            iterfn = 'get_%ss' % restype
        else:
            raise ValueError('iterfn can not be empty while restype is None')
    if getfn is None:
        getfn = '__getitem__'
    elif getfn == '':
        if restype:
            getfn = 'get_%s' % restype
        else:
            raise ValueError('getfn can not be empty while restype is None')
    assert_no_attr(cls, iterfn, getfn)
    
    def MyIter(self):
        for x in getattr(self, attname):
            v = f(x)
            yield t(*v) if restype else v
    MyIter.__name__ = iterfn
    MyIter.__qualname__ = '%s.%s' % (cls.__name__, iterfn)
    setattr(cls, iterfn, MyIter)
    
    def MyGet(self, idx):
        v = getattr(self, attname)
        v = f(v[idx])
        return t(*v) if restype else v
    MyGet.__name__ = getfn
    MyGet.__qualname__ = '%s.%s' % (cls.__name__, getfn)
    setattr(cls, getfn, MyGet)
    
    def MyLen(self):
        v = getattr(self, attname)
        return len(v)
    MyLen.__name__ = '__len__'
    MyLen.__qualname__ = '%s.%s' % (cls.__name__, '__len__')
    if getfn == '__getitem__':
        assert_no_attr(cls, '__len__')
        setattr(cls, '__len__', MyLen)
    return cls

# ����cls�����check����
def Check(cls=None, *, attname, attvals, fnfmt='_check_%s'):
    if cls is None:
        return functools.partial(Check, attname=attname, attvals=attvals)
    def MyCheck(self, v):
        if v not in attvals:
            raise ValueError('val(%s) not in %s' % (v, attvals))
    fn = fnfmt % attname
    MyCheck.__name__ = fn
    MyCheck.__qualname__ = '%s.%s' % (cls.__name__, fn)
    assert_no_attr(cls, fn)
    setattr(cls, fn, MyCheck)
    return cls
# ��ʱ��Ҫ����һЩ����ֵ������ϣ���ӳ���ֵ��ö�Ӧ�ķ������������Ҫ������ӳ���ֵ����������ӳ���
# ��Ԫ������þ��Ǵ������ӳ���
class V2SMapMeta(type):
    def __init__(self, name, bases, ns, **kwargs):
        super().__init__(name, bases, ns)
    # v2s_attnameָ��Ҫ���������Ե����֣�skipָ����Щ����ֵ�����棻stripָ���ӷ�������ͷȥ�������ַ���
    def __new__(cls, name, bases, ns, v2s_attname='v2smap', skip=(), strip=0):
        if v2s_attname in ns:
            raise ValueError('class %s should not define attribute %s' % v2s_attname)
        v2smap = NoRepeatAssignMap()
        for s, v in ns.items():
            if s[0] == '_' or callable(v):
                continue
            if v not in skip:
                s = s[strip:]
                v2smap[v] = s
        ns[v2s_attname] = v2smap
        return super().__new__(cls, name, bases, ns)

