#!/bin/env python3
# -*- coding: GBK -*-
# 
# ����postgresql c/s version 3Э�飬������������ص�Э�顣
# postgresql��Ϣ��ʽ: type + len + data��type��һ���ֽڣ�len��4���ֽڱ�ʾ��С������len�����4���ֽڡ�
# FE�ĵ�һ����Ϣ������type���֡�
# ����Msg�������buf��������ͷ��5���ֽ�(����4���ֽ�)��
# 
# ���ڶ��ڲ���ʶ�����Ϣ����ֱ���׳��쳣�����������ܲ��Ǻܺ��ʣ���Ϊpg�°汾���������µ���Ϣ���͡�
# TODO: ��Щ��Ϣ���͵����ж�����ʵ������ͬ�ģ����Կ���Ԥ�ȴ�����Щ������bytes��������NoneType����ֻ��None��һ������
# 
import sys, os
import struct
import hashlib
import collections
import mputils
from structview import *

# �����������bytes����
def md5(bs):
    m = hashlib.md5()
    m.update(bs)
    return m.hexdigest().encode('ascii')

class FeMsgType(metaclass=mputils.V2SMapMeta, skip=(b'',), strip=3):
    # FE msg type
    MT_StartupMessage = b''        #
    MT_CancelRequest = b''         #
    MT_SSLRequest = b''            #

    MT_Msg = b''                   # 
    MT_Query = b'Q'                # Query
    MT_Parse = b'P'                # Parse (��дP)
    MT_Bind = b'B'                 # Bind
    MT_Execute = b'E'              # Execute
    MT_DescribeClose = b''         # placeholder for Describe/Close base class
    MT_Describe = b'D'             # Describe
    MT_Close = b'C'                # Close
    MT_Sync = b'S'                 # Sync
    MT_Flush = b'H'                # Flush
    MT_CopyData = b'd'             # CopyData (��be����)
    MT_CopyDone = b'c'             # CopyDone (��be����)
    MT_CopyFail = b'f'             # CopyFail
    MT_FunctionCall = b'F'         # FunctionCall
    MT_Terminate = b'X'            # Terminate
    # 'p'���͵���Ϣ�Ƕ�Authentication����Ӧ��������Authentication����������������ͣ�����ֻ�ܴ����������жϡ�
    MT_AuthResponse = b'p'         # (Сдp)�������Ͱ���: PasswordMessage,SASLInitialResponse,SASLResponse,GSSResponse��
class BeMsgType(metaclass=mputils.V2SMapMeta, skip=(b'',), strip=3):
    # BE msg type
    MT_Authentication = b'R'       # AuthenticationXXX
    MT_BackendKeyData = b'K'       # BackendKeyData
    MT_BindComplete = b'2'         # BindComplete
    MT_CloseComplete = b'3'        # CloseComplete
    MT_CommandComplete = b'C'      # CommandComplete
    MT_CopyData = b'd'             # CopyData
    MT_CopyDone = b'c'             # CopyDone
    MT_CopyResponse = b''          # placeholder for Copy[In|Out|Both]Response base class
    MT_CopyInResponse = b'G'       # CopyInResponse
    MT_CopyOutResponse = b'H'      # CopyOutResponse
    MT_CopyBothResponse = b'W'     # CopyBothResponse (only for Streaming Replication)
    MT_DataRow = b'D'              # DataRow
    MT_EmptyQueryResponse = b'I'   # EmptyQueryResponse
    MT_ErrorNoticeResponse = b''   # placeholder for ErrorResponse/NoticeResponse base class
    MT_ErrorResponse = b'E'        # ErrorResponse
    MT_NoticeResponse = b'N'       # NoticeResponse (async message)
    MT_FunctionCallResponse = b'V' # FunctionCallResponse (��дV)
    MT_NoData = b'n'               # NoData
    MT_NotificationResponse = b'A' # NotificationResponse (async message)
    MT_ParameterDescription = b't' # ParameterDescription
    MT_ParameterStatus = b'S'      # ParameterStatus (async message while reloading configure file)
    MT_ParseComplete = b'1'        # ParseComplete
    MT_PortalSuspended = b's'      # PortalSuspended
    MT_ReadyForQuery = b'Z'        # ReadyForQuery
    MT_RowDescription = b'T'       # RowDescription
    @classmethod
    def is_async_msg(cls, msgtype):
        return msgtype in (cls.MT_NoticeResponse, cls.MT_NotificationResponse, cls.MT_ParameterDescription)
class MsgType(FeMsgType, BeMsgType):
    pass

# �������ͣ�prepared statement, portal
class ObjType(metaclass=mputils.V2SMapMeta, strip=4):
    OBJ_PreparedStmt = b'S'
    OBJ_Portal = b'P'

# ����״̬
class TransStatus(metaclass=mputils.V2SMapMeta, strip=3):
    TS_Idle = b'I'
    TS_InBlock = b'T'
    TS_Fail = b'E'

# ErrorResponse/NoticeResponse�е�field type
class FieldType(metaclass=mputils.V2SMapMeta, strip=3):
    FT_Severity = b'S'
    FT_Severity2 = b'V'      # same to b'S', but never localized
    FT_Code = b'C'
    FT_Message = b'M'
    FT_Detail = b'D'
    FT_Hint = b'H'
    FT_Position = b'P'
    FT_InternalPos = b'p'
    FT_InternalQuery = b'q'
    FT_Where = b'W'
    FT_SchemaName = b's'
    FT_TableName = b't'
    FT_ColumnName = b'c'
    FT_DataType = b'd'
    FT_ConstraintName = b'n'
    FT_File = b'F'
    FT_Line = b'L'
    FT_Routine = b'R'
    # ��fieldtype�ֽڴ�ת���б�
    @classmethod
    def ftstr2list(cls, ftstr):
        return [ftstr[i:i+1] for i in range(len(ftstr))]

# auth type��Authentication��Ϣ����
class AuthType(metaclass=mputils.V2SMapMeta, strip=3):
    AT_Ok = 0
    AT_KerberosV5 = 2
    AT_CleartextPassword = 3
    AT_MD5Password = 5
    AT_SCMCredential = 6
    AT_GSS = 7
    AT_GSSContinue = 8
    AT_SSPI = 9
    AT_SASL = 10
    AT_SASLContinue = 11
    AT_SASLFinal = 12
    _HasData = (AT_MD5Password, AT_GSSContinue, AT_SASL, AT_SASLContinue, AT_SASLFinal)

class MsgMeta(struct_meta):
    fe_msg_map = mputils.NoRepeatAssignMap()
    be_msg_map = mputils.NoRepeatAssignMap()
    def __init__(self, name, bases, ns):
        if self.msg_type: # ����msg_type=b''
            mt_symbol = 'MT_' + name
            if hasattr(FeMsgType, mt_symbol):
                type(self).fe_msg_map[self.msg_type] = self
            if hasattr(BeMsgType, mt_symbol):
                type(self).be_msg_map[self.msg_type] = self
        super().__init__(name, bases, ns)
    def __new__(cls, name, bases, ns):
        if 'msg_type' in ns:
            raise ValueError('class %s should not define msg_type' % name)
        ns['msg_type'] = getattr(MsgType, 'MT_' + name)
        return super().__new__(cls, name, bases, ns)
    @classmethod
    def check_msg_type(cls, msg_type, *, fe):
        if fe:
            if msg_type not in cls.fe_msg_map:
                raise ValueError('unknown fe msg type:[%s]' % msg_type)
        else:
            if msg_type not in cls.be_msg_map:
                raise ValueError('unknown be msg type:[%s]' % msg_type)
# ��Ϣ���ࡣ
class Msg(struct_base, metaclass=MsgMeta):
    def tobytes(self):
        data = super().tobytes()
        header = self.msg_type + struct.pack('>i', len(data)+4)
        return header + data
    def __repr__(self):
        res = '<%s' % type(self).__name__
        for field in self._fields:
            fval = getattr(self, field)
            res += ' %s=%s' % (field, fval)
        res += '>'
        return res
# ������Щ���Ǵ�Msg��������Ϣ�࣬������������decorator�����Ǽӽ�����
def FE(cls):
    MsgMeta.fe_msg_map[cls.msg_type] = cls
    return cls
def BE(cls):
    MsgMeta.be_msg_map[cls.msg_type] = cls
    return cls

# 
# FE msg
# 
# simple query
class Query(Msg):
    _formats = '>x'
    _fields = 'query'
# extended query��
# һ��˳��Ϊ: Parse->Bind->Describe->Execute->Close->Sync��
# ����������յ���Ϣ�Ľ���Ļ�����Ҫ���淢��Flush(Sync���治��ҪFlush)������д�����������˻����̷���ErrorResponse(����ҪFlush)��
# ����д���������˻���Ժ����������Ϣֱ��Sync������ÿ����Ϣ��������ȼ���Ƿ��յ�ErrorResponse�����û�յ��ٷ��ͺ�������Ϣ��
# Sync��ر�����(�ύ��ع�)��Ȼ�󷵻�ReadyForQuery��ÿ��Sync������һ��ReadyForQuery��Ӧ��
# 
# param_cnt/param_oidsָ���������������͵�oid�����oid=0��ϵͳ���Լ��Ƶ������͡�
# ����ָ���Ĳ�����������С�ڲ�ѯ�����ʵ�ʵĲ���������û��ָ���Ĳ�����ϵͳ�Լ��Ƶ������͡�
class Parse(Msg):
    _formats = '>x >x >h -0>i'
    _fields = 'stmt query param_cnt param_oids'
    # query/stmt�����Ǹ�ʽΪclient_encoding���ֽڴ��������ط�Ҳһ����
    # query��sql��䣬���в�����$n��ʾ��stmt��prepared statement���֡�
    @classmethod
    def make(cls, query, stmt=b'', param_oids=()):
        return cls(stmt=stmt, query=query, param_cnt=len(param_oids), param_oids=param_oids)
@mputils.SeqAccess(attname='params', f=lambda x:(None if x.sz < 0 else x.data))
class Bind(Msg):
    _formats = '>x >x >h -0>h >24X >h -0>h'
    _fields = 'portal stmt fc_cnt fc_list params res_fc_cnt res_fc_list'
    # fc_listָ��params�в���ֵ�ĸ�ʽ����(fc)��0���ı���ʽ1�Ƕ����Ƹ�ʽ�����Ϊ�����ʾ�����ı���ʽ��
    # ���ֻ��һ��fc��ָ�����в����ĸ�ʽΪfc������fc_list�Ĵ�С��params�Ĵ�Сһ����ָ��ÿ��������fc��
    # res_fc_listָ�����ؽ���и��еĸ�ʽ���룬�����fc_listһ����
    @classmethod
    def make(cls, params, portal=b'', stmt=b'', fc_list=(), res_fc_list=()):
        params = List2Xval(params)
        return cls(portal=portal, stmt=stmt, fc_cnt=len(fc_list), fc_list=fc_list, 
                   params=params, res_fc_cnt=len(res_fc_list), res_fc_list=res_fc_list)
class Execute(Msg):
    _formats = '>x >i'
    _fields = 'portal max_num'
    @classmethod
    def make(cls, portal=b'', max_num=0):
        return cls(portal=portal, max_num=max_num)
@mputils.Check(attname='obj_type', attvals=ObjType.v2smap)
class DescribeClose(Msg):
    _formats = '>s >x'
    _fields = 'obj_type obj_name'
    # ע��:����ͨ��DescribeClose����������2��������Ӧ��ͨ��Describe��Close���á�
    @classmethod
    def stmt(cls, name=b''):
        return cls(obj_type=ObjType.OBJ_PreparedStmt, obj_name=name)
    @classmethod
    def portal(cls, name=b''):
        return cls(obj_type=ObjType.OBJ_Portal, obj_name=name)
class Describe(DescribeClose):
    pass
class Close(DescribeClose):
    pass
class Sync(Msg):
    pass
class Flush(Msg):
    pass
# CopyData/CopyDone��BE���ã������涨�塣
class CopyFail(Msg):
    _formats = '>x'
    _fields = 'err_msg'
@mputils.SeqAccess(attname='args', f=lambda x:(None if x.sz < 0 else x.data))
class FunctionCall(Msg):
    _formats = '>i >h -0>h >24X >h'
    _fields = 'foid fc_cnt fc_list args res_fc'
    # fc_list����˼��Bind.makeһ����
    @classmethod
    def make(cls, foid, args, fc_list=(), res_fc=0):
        args = List2Xval(args)
        return cls(foid=foid, fc_cnt=len(fc_list), fc_list=fc_list, args=args, res_fc=res_fc)
class Terminate(Msg):
    pass
# 'p'��Ϣ�����Ƕ�Authentication�Ļ�Ӧ�����������������ͣ���Ҫ�����������ж���Ҫ�Ǹ��������͡�
# AuthResponse����data����data�ɾ�������ͽ������������������͵�tobytes���Ҫ��ֵ��AuthResponse��data��
# ���磺
#     r = SASLInitialResponse(name=b'xxxx', response=xval(b'yyyy'))
#     ar = AuthResponse(data=bytes(r))  or  ar = AuthResponse(r)
#     r2 = SASLInitialResponse(ar.data)   ������ar.tobytes()����bytes(ar)
class AuthResponse(Msg):
    _formats = '>a'
    _fields = 'data'
class PasswordMessage(struct_base):
    _formats = '>x'
    _fields = 'password'
    # �����������ֽڴ�
    @classmethod
    def make(cls, password, username=None, md5salt = None):
        if md5salt:
            if not username:
                raise SystemError('BUG: should provide username for md5 authentication')
            password = b'md5' + md5(md5(password + username) + md5salt)
        return cls(password=password)
class SASLInitialResponse(struct_base):
    _formats = '>x >4x'
    _fields = 'name response'
class SASLResponse(struct_base):
    _formats = '>a'
    _fields = 'msgdata'
class GSSResponse(struct_base):
    _formats = '>a'
    _fields = 'msgdata'

# 
# BE msg
# 
# ĳЩauthtype��ʹ��û��dataֵ�ģ�ҲҪ��b''��ֵ��data��
@mputils.Check(attname='authtype', attvals=AuthType.v2smap)
class Authentication(Msg):
    _formats = '>i >a'
    _fields = 'authtype data'
    # ���val�Ƿ�����Ч��data���ڸ�data��ֵǰ�����ȸ�authtype��ֵ��
    def _check_data(self, val):
        if not self.field_assigned('authtype'):
            raise ValueError('authtype should be assigned before data')
        if self.authtype not in AuthType._HasData and val:
            raise ValueError('authtype(%s) should has empty data(%s)' % (AuthType.v2smap[self.authtype], val))
        if self.authtype in AuthType._HasData and not val:
            raise ValueError('authtype(%s) should has data which is not empty' % (AuthType.v2smap[self.authtype],))
        # ������auth���͵�data����Ч��
        if self.authtype == AuthType.AT_MD5Password and len(val) != 4:
            raise ValueError('the data size for authtype(MD5Password) should be 4:%s' % val)
    def __repr__(self):
        return '<%s authtype=%s data=%s>' % (type(self).__name__, AuthType.v2smap[self.authtype], self.data)
    # ���ݱ���Ϣ�����ʹ�����Ӧ��AuthResponse��Ϣ
    def make_ar(self, **kwargs):
        if self.authtype in (AuthType.AT_CleartextPassword, AuthType.AT_MD5Password):
            return AuthResponse(PasswordMessage.make(md5salt=self.data, **kwargs))
        else:
            raise ValueError('do not support authentication:%s' % AuthType.v2smap[self.authtype])
        
class BackendKeyData(Msg):
    _formats = '>i >i'
    _fields = 'pid skey'
class BindComplete(Msg):
    pass
class CloseComplete(Msg):
    pass
class CommandComplete(Msg):
    _formats = '>x'
    _fields = 'tag'
class CopyData(Msg):
    _formats = '>a'
    _fields = 'data'
class CopyDone(Msg):
    pass
# just base class for Copy In/Out/Both Response
class CopyResponse(Msg):
    _formats = '>b >h -0>h'
    _fields = 'overall_fmt col_cnt col_fc_list'
    @classmethod
    def make(cls, overall_fmt, col_fc_list):
        return cls(overall_fmt=overall_fmt, col_cnt=len(col_fc_list), col_fc_list=col_fc_list)
class CopyInResponse(CopyResponse):
    pass
class CopyOutResponse(CopyResponse):
    pass
class CopyBothResponse(CopyResponse):
    pass
@mputils.SeqAccess(attname='col_vals', f=lambda x:(None if x.sz < 0 else x.data))
class DataRow(Msg):
    _formats = '>24X'
    _fields = 'col_vals'
class EmptyQueryResponse(Msg):
    pass
# field_list���ֽڴ��б��ֽڴ��е�һ���ֽ���fieldtype, ʣ�µ���fieldval
@mputils.SeqAccess(attname='field_list', restype='Field', resfields='t v', f=lambda x:(x[:1],x[1:]))
class ErrorNoticeResponse(Msg):
    _formats = '>X'
    _fields = 'field_list'
    def get(self, fields):
        res = []
        if type(fields) == bytes:
            fields = FieldType.ftstr2list(fields)
        if not (set(fields) <= FieldType.v2smap.keys()):
            raise ValueError('fields(%s) have unknown field type' % (fields,))
        for t, v in self:
            if t not in fields:
                continue
            res.append((FieldType.v2smap[t], v))
        return res
class ErrorResponse(ErrorNoticeResponse):
    pass
class NoticeResponse(ErrorNoticeResponse):
    pass
class FunctionCallResponse(Msg):
    _formats = '>4x'
    _fields = 'res_val'
    def value(self):
        return (None if self.res_val.sz < 0 else bytes(self.res_val))
class NoData(Msg):
    pass
class NotificationResponse(Msg):
    _formats = '>i >x >x'
    _fields = 'pid channel payload'
class ParameterDescription(Msg):
    _formats = '>h -0>i'
    _fields = 'count oid_list'
class ParameterStatus(Msg):
    _formats = '>x >x'
    _fields = 'name val'
class ParseComplete(Msg):
    pass
class PortalSuspended(Msg):
    pass
@mputils.Check(attname='trans_status', attvals=TransStatus.v2smap)
class ReadyForQuery(Msg):
    _formats = '>s'
    _fields = 'trans_status'
# field_list����(name, tableoid, attnum, typoid, typlen, typmod, fmtcode)
@mputils.SeqAccess(attname='field_list', restype='Field', resfields='name tableoid attnum typoid typlen typmod fmtcode')
class RowDescription(Msg):
    _formats = '>h -0>xihihih'
    _fields = 'field_cnt field_list'

# 
# FE->BE�ĵ�һ����Ϣ
# 
PG_PROTO_VERSION2_NUM = 131072
PG_PROTO_VERSION3_NUM = 196608
PG_CANCELREQUEST_CODE = 80877102
PG_SSLREQUEST_CODE    = 80877103

# 
# V3 StartupMessage������μ�postmaster.c�е�ProcessStartupPacket������
# ���԰���������Щ��
#   database
#   user
#   options       ������ѡ��
#   replication   ��Чֵtrue/false/1/0/database��database��ʾ���ӵ�databaseѡ��ָ�������ݿ⣬һ�������߼����ơ�
#   <guc option>  ����gucѡ�����: client_encoding/application_name
# 
class StartupMessage(Msg):
    _formats = '>i >X'
    _fields = 'code params'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = PG_PROTO_VERSION3_NUM
        self._params_dict = None
    def get_params(self):
        # ��paramsת��dict��dict��keyת��str��value���ֽڴ�
        if not self._params_dict:
            it = iter(self.params)
            f = lambda x: (bytes(x[0]).decode('ascii'), bytes(x[1]))
            self._params_dict = dict(map(f, zip(it, it)))
        return self._params_dict
    @classmethod
    def make(cls, **kwargs):
        params = []
        for k, v in kwargs.items():
            params.append(k.encode('ascii'))
            if type(v) is str:
                v = v.encode('ascii')
            params.append(v)
        return cls(params = Xval(params))
class CancelRequest(Msg):
    _formats = '>i >i >i'
    _fields = 'code pid skey'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = PG_CANCELREQUEST_CODE
class SSLRequest(Msg):
    _formats = '>i'
    _fields = 'code'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = PG_SSLREQUEST_CODE
# ���ڴ���nnX(��00X/X)����ֵ����None�໥ת����
def Xval2List(v):
    return [None if x.sz < 0 else x.data for x in v]
def List2Xval(vlist):
    xlist = (xval(b'', sz=-1) if v is None else v for v in vlist)
    return Xval(xlist)

#============================================================================================
# ��Э�������ֱ����ص�
# 
# ���startup��Ϣ�Ƿ������������data̫�����׳��쳣��data������ͷ��ʾ���ȵ�4���ֽڡ�
def startup_msg_is_complete(data):
    data_len = len(data)
    if data_len <= 4:
        return False
    msg_len = struct.unpack('>i', data[:4])[0]
    if data_len > msg_len:
        raise RuntimeError('startup msg is invalid. msg_len:%s data_len:%s' % (msg_len, data_len))
    return data_len == msg_len
# ����FE�ĵ�һ����Ϣ��������Ӧ����Ϣ��Ķ�������׳��쳣��data��������ͷ��ʾ��С��4���ֽڡ�
def parse_startup_msg(data):
    code = struct.unpack('>i', data[:4])[0]
    if code == PG_PROTO_VERSION2_NUM:
        raise RuntimeError('do not support version 2 protocol')
    elif code == PG_PROTO_VERSION3_NUM:
        return StartupMessage(data)
    elif code == PG_CANCELREQUEST_CODE:
        return CancelRequest(data)
    elif code == PG_SSLREQUEST_CODE:
        return SSLRequest(data)
    else:
        raise RuntimeError('unknown code(%s) in startup msg' % code)
# �ж�data�д�idx��ʼ�Ƿ�����������Ϣ��������Ϣ���ĳ���(������ͷ5���ֽ�)�����û��������Ϣ�򷵻�0��
def has_msg(data, idx, *, fe=True):
    data_len = len(data)
    if data_len - idx < 5:
        return 0
    msg_type = data[idx:idx+1]
    MsgMeta.check_msg_type(msg_type, fe=fe)
    msg_len = struct.unpack('>i', data[idx+1:idx+5])[0]
    if data_len -idx < msg_len + 1:
        return 0
    return msg_len + 1
# 
# ��data����ȡ�����Ϣ����������һ��idx����Ϣ�����б��ú�����������parse��FE����BE�ĵ�һ����Ϣ��
#   data : ԭʼ���ݡ�
#   max_msg : �����ȡ���ٸ���Ϣ�������Ϊ0��ʾ��ȡ���С�
#   fe : �Ƿ�������FE����Ϣ��
# 
def parse_pg_msg(data, max_msg = 0, *, fe=True):
    msg_list = []
    idx, cnt = 0, 0
    msg_map = MsgMeta.fe_msg_map if fe else MsgMeta.be_msg_map
    while True:
        msg_len = has_msg(data, idx, fe=fe)
        if msg_len <= 0:
            break
        msg_type = data[idx:idx+1]
        msg_data = data[idx+5:idx+msg_len]
        idx += msg_len
        
        msg_list.append(msg_map[msg_type](msg_data))
        cnt += 1
        if max_msg > 0 and cnt >= max_msg:
            break
    return (idx, msg_list)

# main
if __name__ == '__main__':
    pass
