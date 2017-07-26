#!/bin/env python3
# -*- coding: GBK -*-
# 
# ����PostgreSQL version 3 protocol
# 
# process_XXX : ������Ϣ������������tuple����tuple�еĵ�һ��Ԫ������Ϣ�����ڶ���Ԫ������Ϣ�����ַ�������������Ϣ���Ͷ�Ӧ��ֵ��
# make_XXX1 : ��process_XXX�ķ��ؽ������һ����Ϣ���ú���һ�����make_XXX2��
# make_XXX2 : �Ӿ���Ĳ�������һ����Ϣ��
# make_Msg0 : ��ԭʼ����(msg_type, msg_data)����һ����Ϣ��
# make_Msg1 : ��process_XXX�ķ��ؽ������һ����Ϣ��
# ע: ����ͨ��make_Msg0/make_Msg1������������û����Ϣ���͵���Ϣ������ֱ��ͨ��make_XXX1/make_XXX2�����졣
#     make�����еĴ����͵Ĳ�����ֵ������bytes��
#
# 
# 
import sys, os, struct, socket, time, errno, hashlib
import traceback
import select
import signal
import sqlite3
import re, logging

if os.name == 'posix':
    NONBLOCK_SEND_RECV_OK = (errno.EAGAIN, errno.EWOULDBLOCK)
    NONBLOCK_CONNECT_EX_OK = (errno.EINPROGRESS, 0)
else:
    NONBLOCK_SEND_RECV_OK = (errno.EAGAIN, errno.EWOULDBLOCK, errno.WSAEWOULDBLOCK)
    NONBLOCK_CONNECT_EX_OK = (errno.WSAEWOULDBLOCK, 0)

# 
# utility functions
# 
# �����������bytes����
def md5(bs):
    m = hashlib.md5()
    m.update(bs)
    return m.hexdigest().encode('latin1')
# ���data�д�idx��ʼ��C����C����\x00��β��
def get_cstr(data, idx):
    end = idx
    while (data[end] != 0):
        end += 1
    return data[idx:end+1]
# makeһ��C����s�����ͱ�����bytes��
def make_cstr(s):
    s_len = len(s)
    if s_len == 0 or s[len(s)-1] != 0:
        s += b'\x00'
    return s
# 
# 
# 
def make_Msg0(msg_type, msg_data):
    return msg_type + struct.pack('>i', len(msg_data)+4) + msg_data
def make_Msg1(msg_res, is_from_be = True):
    if is_from_be:
        return be_msg_type_info[msg_res[1]][1](msg_res)
    else:
        return fe_msg_type_info[msg_res[1]][1](msg_res)
# msg_type : ��Ϣ����
# msg_data : ��Ϣ���ݣ���������ʾ���ȵ���4���ֽ�
def process_AuthenticationXXX(msg_type, msg_data):
    v = struct.unpack('>i', msg_data[:4])[0]
    if v == 0: 
        return ('AuthenticationOk', msg_type)
    elif v == 2:
        return ('AuthenticationKerberosV5', msg_type)
    elif v == 3:
        return ('AuthenticationCleartextPassword', msg_type)
    elif v == 5:
        return ('AuthenticationMD5Password', msg_type, msg_data[4:])
    elif v == 6:
        return ('AuthenticationSCMCredential', msg_type)
    elif v == 7:
        return ('AuthenticationGSS', msg_type)
    elif v == 9:
        return ('AuthenticationSSPI', msg_type)
    elif v == 8:
        return ('AuthenticationGSSContinue', msg_type, msg_data[4:])
    else:
        raise RuntimeError('Unknown Authentication message:(%s,%s,%s)' % (msg_type, v, msg_data))
def make_AuthenticationXXX1(msg_res):
    return make_AuthenticationXXX2(msg_res[0], *msg_res[2:])
def make_AuthenticationXXX2(auth_name, *auth_params):
    msg_data = b''
    if auth_name == 'AuthenticationOk' or auth_name == b'AuthenticationOk':
        msg_data = struct.pack('>i', 0)
    elif auth_name == 'AuthenticationCleartextPassword' or auth_name == b'AuthenticationCleartextPassword':
        msg_data = struct.pack('>i', 3)
    elif auth_name == 'AuthenticationMD5Password' or auth_name == b'AuthenticationMD5Password':
        msg_data = struct.pack('>i', 5) + auth_params[0] # auth_params[0]��md5 salt
    else:
        raise RuntimeError('do not support authentication type:%s' % auth_name)
    return make_Msg0(b'R', msg_data)

def process_BackendKeyData(msg_type, msg_data):
    pid, skey = struct.unpack('>ii', msg_data)
    return ('BackendKeyData', msg_type, pid, skey)
def make_BackendKeyData1(msg_res):
    return make_BackendKeyData2(msg_res[2], msg_res[3])
def make_BackendKeyData2(pid, skey):
    msg_data = struct.pack('>ii', pid, skey)
    return make_Msg0(b'K', msg_data)

def process_BindComplete(msg_type, msg_data):
    return ('BindComplete', msg_type)
def make_BindComplete1(msg_res):
    return make_BindComplete2()
def make_BindComplete2():
    return make_Msg0(b'2', b'')

def process_CloseComplete(msg_type, msg_data):
    return ('CloseComplete', msg_type)
def make_CloseComplete1(msg_res):
    return make_CloseComplete2()
def make_CloseComplete2():
    return make_Msg0(b'3', b'')

def process_CommandComplete(msg_type, msg_data):
    return ('CommandComplete', msg_type, msg_data)
def make_CommandComplete1(msg_res):
    return make_CommandComplete2(msg_res[2])
def make_CommandComplete2(cmd_tag):
    return make_Msg0(b'C', make_cstr(cmd_tag))

def process_CopyData(msg_type, msg_data):
    return ('CopyData', msg_type, msg_data)
def make_CopyData1(msg_res):
    return make_CopyData2(msg_res[2])
def make_CopyData2(data):
    return make_Msg0(b'd', data)

def process_CopyDone(msg_type, msg_data):
    return ('CopyDone', msg_type)
def make_CopyDone1(msg_res):
    return make_CopyDone2()
def make_CopyDone2():
    return make_Msg0(b'c', b'')

def process_CopyInResponse(msg_type, msg_data):
    overall_fmt, col_cnt = struct.unpack('>bh', msg_data[:3])
    col_fmts = struct.unpack('>%dh'%col_cnt, msg_data[3:])
    return ('CopyInResponse', msg_type, overall_fmt, col_cnt, col_fmts)
def make_CopyInResponse1(msg_res):
    return make_CopyInResponse2(msg_res[2], msg_res[4])
def make_CopyInResponse2(overall_fmt, col_fmts):
    '''
    overall_fmt : �ܵĸ�ʽ���롣0��text��ʽ��1��binary��ʽ��
    col_fmts : ָ��ÿ���еĸ�ʽ���롣���overall_fmtΪ0����ô����ȫΪ0��
    '''
    cnt = len(col_fmts)
    msg_data = struct.pack('>bh%dh'%cnt, overall_fmt, cnt, *col_fmts)
    return make_Msg0(b'G', msg_data)

def process_CopyOutResponse(msg_type, msg_data):
    overall_fmt, col_cnt = struct.unpack('>bh', msg_data[:3])
    cols_fmt = struct.unpack('>%dh'%col_cnt, msg_data[3:])
    return ('CopyOutResponse', msg_type, overall_fmt, col_cnt, cols_fmt)
def make_CopyOutResponse1(msg_res):
    return make_CopyOutResponse2(msg_res[2], msg_res[4])
def make_CopyOutResponse2(overall_fmt, col_fmts):
    '''
    overall_fmt : �ܵĸ�ʽ���롣0��text��ʽ��1��binary��ʽ��
    col_fmts : ָ��ÿ���еĸ�ʽ���롣���overall_fmtΪ0����ô����ȫΪ0��
    '''
    cnt = len(col_fmts)
    msg_data = struct.pack('>bh%dh'%cnt, overall_fmt, cnt, *col_fmts)
    return make_Msg0(b'H', msg_data)

def process_CopyBothResponse(msg_type, msg_data):
    overall_fmt, col_cnt = struct.unpack('>bh', msg_data[:3])
    cols_fmt = struct.unpack('>%dh'%col_cnt, msg_data[3:])
    return ('CopyBothResponse', msg_type, overall_fmt, col_cnt, cols_fmt)
def make_CopyBothResponse1(msg_res):
    return make_CopyBothResponse2(msg_res[2], msg_res[4])
def make_CopyBothResponse2(overall_fmt, col_fmts):
    '''
    overall_fmt : �ܵĸ�ʽ���롣0��text��ʽ��1��binary��ʽ��
    col_fmts : ָ��ÿ���еĸ�ʽ���롣���overall_fmtΪ0����ô����ȫΪ0��
    '''
    cnt = len(col_fmts)
    msg_data = struct.pack('>bh%dh'%cnt, overall_fmt, cnt, *col_fmts)
    return make_Msg0(b'W', msg_data)

def process_DataRow(msg_type, msg_data):
    col_cnt = struct.unpack('>h', msg_data[:2])[0]
    idx = 2
    res = ('DataRow', msg_type, col_cnt, [])
    col_list = res[3]
    for i in range(col_cnt):
        col_len = struct.unpack('>i', msg_data[idx:idx+4])[0]
        idx += 4
        col_val = b''
        if col_len > 0:
            col_val = msg_data[idx:idx+col_len]
        idx += (col_len if col_len > 0 else 0)
        col_list.append((col_len, col_val))
    return res
def make_DataRow1(msg_res):
    return make_DataRow2(msg_res[3])
def make_DataRow2(col_list):
    '''
    col_list : ��ֵ���б��б��е�Ԫ���Ǹ�tuple����tuple�еĵ�һ��Ԫ��ָ������ֵ�ĳ��ȣ�-1��ʾ�е�ֵΪNULL��
               tuple�еĵڶ���Ԫ������ֵ(�����һ��Ԫ�ص�ֵΪ0����-1����ô��ֵ����Ϊ���ֽڴ�)��
    '''
    cnt = len(col_list)
    msg_data = struct.pack('>h', cnt)
    for col in col_list:
        msg_data += struct.pack('>i', col[0]) + col[1]
    return make_Msg0(b'D', msg_data)

def process_EmptyQueryResponse(msg_type, msg_data):
    return ('EmptyQueryResponse', msg_type)
def make_EmptyQueryResponse1(msg_res):
    return make_EmptyQueryRespone2()
def make_EmptyQueryResponse2():
    return make_Msg0(b'I', b'')

def p_ErrorNoticeField(msg_data, idx, res):
    while True:
        field_type = msg_data[idx:idx+1]
        if field_type == b'\x00':
            break
        field_val = get_cstr(msg_data, idx + 1)
        idx += 1 + len(field_val)
        res.append((field_type, field_val))
def process_ErrorResponse(msg_type, msg_data):
    res = ('ErrorResponse', msg_type, [])
    p_ErrorNoticeField(msg_data, 0, res[2])
    return res
def make_ErrorResponse1(msg_res):
    return make_ErrorResponse2(msg_res[2])
def make_ErrorResponse2(err_field_list):
    '''
    err_field_list : ָ������field�б��б��е�Ԫ��������tuple��tuple�еĵ�һ��Ԫ����field���ͣ��ڶ���Ԫ������field���Ͷ�Ӧ�Ĵ�ֵ��֧�ֵ�field�����У�
                     .) b'S' : Severity: the field contents are ERROR, FATAL, or PANIC (in an error message), or WARNING, NOTICE, DEBUG, INFO, or LOG (in a notice message), 
                               or a localized translation of one of these. Always present.
                     .) b'C' : Code: the SQLSTATE code for the error (see Appendix A). Not localizable. Always present.
                     .) b'M' : Message: the primary human-readable error message. This should be accurate but terse (typically one line). Always present.
                     .) b'D' : Detail: an optional secondary error message carrying more detail about the problem. Might run to multiple lines.
                     .) b'H' : Hint: an optional suggestion what to do about the problem. This is intended to differ from Detail in that 
                               it offers advice (potentially inappropriate) rather than hard facts. Might run to multiple lines.
                     .) ... �������忴�ĵ�
    '''
    msg_data = b''
    for err_field in err_field_list:
        msg_data += err_field[0] + make_cstr(err_field[1])
    msg_data += b'\x00'
    return make_Msg0(b'E', msg_data)

def process_FunctionCallResponse(msg_type, msg_data):
    v_len = struct.unpack('>i', msg_data[:4])[0]
    val = b''
    if v_len > 0:
        val = msg_data[4:4+v_len]
    return ('FunctionCallResponse', msg_type, v_len, val)
def make_FunctionCallResponse1(msg_res):
    return make_FunctionCallResponse2(msg_res[2], msg_res[3])
def make_FunctionCallResponse2(res_len, res_val):
    '''
    res_len : �������ý��ֵ�ĳ��ȡ�Ϊ-1��ʾ��������ֵΪNULL��
    res_val : �������õĽ��ֵ�����res_lenΪ0����-1����ô��ֵ����Ϊb''��
    '''
    msg_data = struct.pack('>i', res_len) + res_val
    return make_Msg0(b'V', msg_data)

def process_NoData(msg_type, msg_data):
    return ('NoData', msg_type)
def make_NoData1(msg_res):
    return make_NoData2()
def make_NoData2():
    return make_Msg0(b'n', b'')

def process_NoticeResponse(msg_type, msg_data):
    res = ('NoticeResponse', msg_type, [])
    p_ErrorNoticeField(msg_data, 0, res[2])
    return res
def make_NoticeResponse1(msg_res):
    return make_NoticeResponse2(msg_res[2])
def make_NoticeResponse2(notice_field_list):
    '''
    notice_field_list : ��make_ErrorResponse2���ơ�
    '''
    msg_data = b''
    for notice_field in notice_field_list:
        msg_data += notice_field[0] + make_cstr(notice_field[1])
    msg_data += b'\x00'
    return make_Msg0(b'N', msg_data)

def process_NotificationResponse(msg_type, msg_data):
    pid = struct.unpack('>i', msg_data[:4])[0]
    channel = get_cstr(msg_data, 4)
    payload = get_cstr(msg_data, 4+len(channel))
    return ('NotificationResponse', msg_type, pid, channel, payload)
def make_NotificationResponse1(msg_res):
    return make_NotificationResponse2(msg_res[2], msg_res[3], msg_res[4])
def make_NotificationResponse2(pid, channel, payload):
    '''
    pid : ����notification�Ľ���ID��
    channel : channel���֡�
    payload : payload����
    '''
    msg_data = struct.pack('>i', pid) + make_cstr(channel) + make_cstr(payload)
    return make_Msg0(b'A', msg_data)

def process_ParameterDescription(msg_type, msg_data):
    param_cnt = struct.unpack('>h', msg_data[:2])[0]
    param_type_oids = struct.unpack('>%di'%param_cnt, msg_data[2:])
    return ('ParameterDescription', msg_type, param_cnt, param_type_oids)
def make_ParameterDescription1(msg_res):
    return make_ParameterDescription2(msg_res[3])
def make_ParameterDescription2(param_type_oids):
    '''
    param_type_oids : �������͵�oid�б�
    '''
    cnt = len(param_type_oids)
    msg_data = struct.pack('>h%di', cnt, *param_type_oids)
    return make_Msg0(b't', msg_data)

def process_ParameterStatus(msg_type, msg_data):
    param_name = get_cstr(msg_data, 0)
    param_val = get_cstr(msg_data, len(param_name))
    return ('ParameterStatus', msg_type, param_name, param_val)
def make_ParameterStatus1(msg_res):
    return make_ParameterStatus2(msg_res[2], msg_res[3])
def make_ParameterStatus2(param_name, param_val):
    msg_data = make_cstr(param_name) + make_cstr(param_val)
    return make_Msg0(b'S', msg_data)

def process_ParseComplete(msg_type, msg_data):
    return ('ParseComplete', msg_type)
def make_ParseComplete1(msg_res):
    return make_ParseComplete2()
def make_ParseComplete2():
    return make_Msg0(b'1', b'')

def process_PortalSuspended(msg_type, msg_data):
    return ('PortalSuspended', msg_type)
def make_PortalSuspended1(msg_res):
    return make_PortalSuspended2()
def make_PortalSuspended2():
    return make_Msg0(b's', b'')

def process_ReadyForQuery(msg_type, msg_data):
    return ('ReadyForQuery', msg_type, msg_data[:1])
def make_ReadyForQuery1(msg_res):
    return make_ReadyForQuery2(msg_res[2])
def make_ReadyForQuery2(trans_status):
    '''
    trans_status : ����״̬��b'I'��ʾ����(����������)��b'T'��ʾ��������ڣ�b'E'��ʾһ��ʧ�ܵ��������(��������佫�ܾ�ִ��)��
    '''
    return make_Msg0(b'Z', trans_status)

def process_RowDescription(msg_type, msg_data):
    field_cnt = struct.unpack('>h', msg_data[:2])[0]
    res = ('RowDescription', msg_type, field_cnt, [])
    field_list = res[3]
    idx = 2
    for i in range(field_cnt):
        f_name = get_cstr(msg_data, idx)
        idx += len(f_name)
        f_table_oid, f_attr_num, f_type_oid, f_typlen, f_typmod, f_fmtcode = struct.unpack('>ihihih', msg_data[idx:idx+18])
        idx += 18
        field_list.append((f_name, f_table_oid, f_attr_num, f_type_oid, f_typlen, f_typmod, f_fmtcode))
    return res
def make_RowDescription1(msg_res):
    return make_RowDescription2(msg_res[3])
def make_RowDescription2(field_list):
    '''
    field_list : ָ��field�����б��б��е�Ԫ��������tuple����tuple������
                 .) f_name : field���֡�
                 .) f_table_oid : �����field����ĳ������ô���Ǳ��oid������Ϊ0��
                 .) f_attr_num : �����field����ĳ������ô���Ǹ����ڱ��е����Ժţ�����Ϊ0��
                 .) f_type_oid : field���������͵�oid��
                 .) f_typlen : field���������͵ĳ��ȣ�����ǿɱ䳤�����ͣ���ôΪ-1��
                 .) f_typmod : field���������͵����η���
                 .) f_fmtcode : field��ֵ�ĸ�ʽ���롣0��ʾtext��1��ʾbinary��
    '''
    cnt = len(field_list)
    msg_data = struct.pack('>h', cnt)
    for f in field_list:
        msg_data += make_cstr(f[0]) + struct.pack('>ihihih', *f[1:])
    return make_Msg0(b'T', msg_data)

#
be_msg_type_info = {
    b'R' : (process_AuthenticationXXX, make_AuthenticationXXX1),       # AuthenticationXXX
    b'K' : (process_BackendKeyData, make_BackendKeyData1),             # BackendKeyData
    b'2' : (process_BindComplete, make_BindComplete1),                 # BindComplete
    b'3' : (process_CloseComplete, make_CloseComplete1),               # CloseComplete
    b'C' : (process_CommandComplete, make_CommandComplete1),           # CommandComplete
    b'd' : (process_CopyData, make_CopyData1),                         # CopyData
    b'c' : (process_CopyDone, make_CopyDone1),                         # CopyDone
    b'G' : (process_CopyInResponse, make_CopyInResponse1),             # CopyInResponse
    b'H' : (process_CopyOutResponse, make_CopyOutResponse1),           # CopyOutResponse
    b'W' : (process_CopyBothResponse, make_CopyBothResponse1),         # CopyBothResponse
    b'D' : (process_DataRow, make_DataRow1),                           # DataRow
    b'I' : (process_EmptyQueryResponse, make_EmptyQueryResponse1),     # EmptyQueryResponse
    b'E' : (process_ErrorResponse, make_ErrorResponse1),               # ErrorResponse
    b'V' : (process_FunctionCallResponse, make_FunctionCallResponse1), # FunctionCallResponse
    b'n' : (process_NoData, make_NoData1),                             # NoData
    b'N' : (process_NoticeResponse, make_NoticeResponse1),             # NoticeResponse
    b'A' : (process_NotificationResponse, make_NotificationResponse1), # NotificationResponse (async message)
    b't' : (process_ParameterDescription, make_ParameterDescription1), # ParameterDescription
    b'S' : (process_ParameterStatus, make_ParameterStatus1),           # ParameterStatus (async message while reloading configure file)
    b'1' : (process_ParseComplete, make_ParseComplete1),               # ParseComplete
    b's' : (process_PortalSuspended, make_PortalSuspended1),           # PortalSuspended
    b'Z' : (process_ReadyForQuery, make_ReadyForQuery1),               # ReadyForQuery
    b'T' : (process_RowDescription, make_RowDescription1),             # RowDescription
}
# 
# ��������frontend����Ϣ
# 
def process_Bind(msg_type, msg_data):
    idx = 0
    portal_name = get_cstr(msg_data, idx)
    idx += len(portal_name)
    stmt_name = get_cstr(msg_data, idx)
    idx += len(stmt_name)
    
    fmt_code_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    fmt_code_list = struct.unpack('>%dh'%fmt_code_cnt, msg_data[idx:idx+fmt_code_cnt*2])
    idx += fmt_code_cnt*2
    
    param_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    param_list = []
    for i in range(param_cnt):
        v_len = struct.unpack('>i', msg_data[idx:idx+4])[0]
        idx += 4
        val = b''
        if v_len > 0:
            val = msg_data[idx:idx+v_len]
        idx += (v_len if v_len > 0 else 0)
        param_list.append((v_len, val))
    
    res_fmt_code_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    res_fmt_code_list = struct.unpack('>%dh'%res_fmt_code_cnt, msg_data[idx:idx+res_fmt_code_cnt*2])
    
    return ('Bind', msg_type, portal_name, stmt_name, fmt_code_cnt, fmt_code_list, param_cnt, param_list, res_fmt_code_cnt, res_fmt_code_list)
def make_Bind1(msg_res):
    return make_Bind2(msg_res[2], msg_res[3], msg_res[5], msg_res[7], msg_res[9])
def make_Bind2(portal_name, stmt_name, param_fmt_codes, param_list, res_fmt_codes):
    '''
    portal_name : portal���֡�
    stmt_name : prepared�������֡�
    param_fmt_codes : ָ������ֵ�ĸ�ʽ���롣
                      .) ���Ϊ���б��Ǿͱ�ʾû�в����������в���ֵ�ĸ�ʽ����Ϊ0��
                      .) ���ֻ��һ��Ԫ�أ���ô��Ԫ��ֵָ�������в����ĸ�ʽ���룻
                      .) ����Ԫ�ظ������ڲ���������ÿ��Ԫ��ָ���˶�Ӧ����ֵ�ĸ�ʽ���롣
    param_list : ����ֵ���б��б��е�Ԫ���Ǹ�tuple����tuple�еĵ�һ��Ԫ��ָ���˲���ֵ�ĳ��ȣ�-1��ʾ������ֵΪNULL��
                 tuple�еĵڶ���Ԫ���ǲ���ֵ(�����һ��Ԫ�ص�ֵΪ0����-1����ô����ֵ����Ϊ���ֽڴ�)��
    res_fmt_codes : ָ������еĸ�ʽ���롣��param_fmt_codes��ʶ��ͬ��
    '''
    msg_data = make_cstr(portal_name) + make_cstr(stmt_name)
    
    cnt = len(param_fmt_codes)
    msg_data += struct.pack('>h%dh'%cnt, cnt, *param_fmt_codes)
    
    cnt = len(param_list)
    msg_data += struct.pack('>h', cnt)
    for param in param_list:
        msg_data += struct.pack('>i', param[0]) + param[1]
    
    cnt = len(res_fmt_codes)
    msg_data += struct.pack('>h%dh'%cnt, cnt, *res_fmt_codes)
    return make_Msg0(b'B', msg_data)

def process_Close(msg_type, msg_data):
    obj_type = msg_data[:1]
    obj_name = get_cstr(msg_data, 1)
    return ('Close', msg_type, obj_type, obj_name)
def make_Close1(msg_res):
    return make_Close2(msg_res[2], msg_res[3])
def make_Close2(obj_type, obj_name):
    '''
    obj_type : �������͡�Ϊb'S'��ʾ��prepared��䣻Ϊb'P'��ʾ��portal��
    obj_name : prepared������portal�����֡�
    '''
    msg_data = obj_type + make_cstr(obj_name)
    return make_Msg0(b'C', msg_data)

def process_CopyFail(msg_type, msg_data):
    return ('CopyFail', msg_type, msg_data)
def make_CopyFail1(msg_res):
    return make_Fail2(msg_res[2])
def make_CopyFail2(errmsg):
    '''
    errmsg : ������Ϣ��
    '''
    msg_data = make_cstr(errmsg)
    return make_Msg0(b'f', msg_data)

def process_Describe(msg_type, msg_data):
    obj_type = msg_data[:1]
    obj_name = get_cstr(msg_data, 1)
    return ('Close', msg_type, obj_type, obj_name)
def make_Describe1(msg_res):
    return make_Describe2(msg_res[2], msg_res[3])
def make_Describe2(obj_type, obj_name):
    '''
    obj_type : �������͡�Ϊb'S'��ʾ��prepared��䣻Ϊb'P'��ʾ��portal��
    obj_name : prepared������portal�����֡�
    '''
    msg_data = obj_type + make_cstr(obj_name)
    return make_Msg0(b'D', msg_data)

def process_Execute(msg_type, msg_data):
    idx = 0
    portal_name = get_cstr(msg_data, idx)
    idx += len(portal_name)
    return_row_cnt = struct.unpack('>i', msg_data[idx:idx+4])[0]
    return ('Execute', msg_type, portal_name, return_row_cnt)
def make_Execute1(msg_res):
    return make_Execute2(msg_res[2], msg_res[3])
def make_Execute2(portal_name, return_row_cnt = 0):
    '''
    portal_name : portal����
    return_row_cnt : ��෵�ض�������0��ʾ�������С�
    '''
    msg_data = make_cstr(portal_name) + struct.pack('>i', return_row_cnt)
    return make_Msg0(b'E', msg_data)

def process_Flush(msg_type, msg_data):
    return ('Flush', msg_type)
def make_Flush1(msg_res):
    return make_Flush2()
def make_Flush2():
    return make_Msg0(b'H', b'')

def process_FunctionCall(msg_type, msg_data):
    idx = 0
    func_oid = struct.unpack('>i', msg_data[idx:idx+4])[0]
    idx += 4
    
    arg_fmt_code_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    arg_fmt_code_list = struct.unpack('>%dh'%arg_fmt_code_cnt, msg_data[idx:idx+arg_fmt_code_cnt*2])
    idx += arg_fmt_code_cnt*2
    
    arg_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    arg_list = []
    for i in range(arg_cnt):
        v_len = struct.unpack('>i', msg_data[idx:idx+2])[0]
        idx += 4
        val = b''
        if v_len > 0:
            val = msg[idx:idx+v_len]
        idx += (v_len if v_len > 0 else 0)
        arg_list.append((v_len, val))
    
    res_fmt_code = struct.unpack('>h', msg_data[idx:idx+2])[0]
    
    return ('FunctionCall', msg_type, func_oid, arg_fmt_code_cnt, arg_fmt_code_list, arg_cnt, arg_list, res_fmt_code)
def make_FunctionCall1(msg_res):
    return make_FunctionCall2(msg_res[2], msg_res[4], msg_res[6], msg_res[7])
def make_FunctionCall2(func_oid, arg_fmt_codes, arg_list, res_fmt_code):
    '''
    func_oid : Ҫ���õĺ�����oid��
    arg_fmt_codes : ָ����������ֵ�ĸ�ʽ���롣
                    .) ���Ϊ���б��Ǿͱ�ʾ����û�в����������в���ֵ�ĸ�ʽ����Ϊ0��
                    .) ���ֻ��һ��Ԫ�أ���ô��Ԫ��ֵָ�������в����ĸ�ʽ���룻
                    .) ����Ԫ�ظ������ں�������������ÿ��Ԫ��ָ���˶�Ӧ����ֵ�ĸ�ʽ���롣
    arg_list : ��������ֵ�б��б��е�Ԫ���Ǹ�tuple����tuple�еĵ�һ��Ԫ��ָ���˺�������ֵ�ĳ��ȣ�-1��ʾ����������ֵΪNULL��
               tuple�еĵڶ���Ԫ���Ǻ�������ֵ(�����һ��Ԫ�ص�ֵΪ0����-1����ô��������ֵ����Ϊ���ֽڴ�)��
    res_fmt_code : ��������ֵ�ĸ�ʽ���롣
    '''
    msg_data = struct.pack('>i', func_oid)
    
    cnt = len(arg_fmt_codes)
    msg_data += struct.pack('>h%dh'%cnt, cnt, *arg_fmt_codes)
    
    cnt = len(arg_list)
    msg_data += struct.pack('>h', cnt)
    for arg in arg_list:
        msg_data += struct.pack('>i', arg[0]) + arg[1]
    
    msg_data += struct.pack('>h', res_fmt_code)
    return make_Msg0(b'F', msg_data)

def process_Parse(msg_type, msg_data):
    idx = 0
    stmt_name = get_cstr(msg_data, idx)
    idx += len(stmt_name)
    query = get_cstr(msg_data, idx)
    idx += len(query)
    
    param_type_cnt = struct.unpack('>h', msg_data[idx:idx+2])[0]
    idx += 2
    param_type_oid_list = struct.unpack('>%di'%param_type_cnt, msg_data[idx:idx+param_type_cnt*4])
    
    return ('Parse', msg_type, stmt_name, query, param_type_cnt, param_type_oid_list)
def make_Parse1(msg_res):
    return make_Parse2(msg_res[2], msg_res[3], msg_res[5])
def make_Parse2(stmt_name, query, param_type_oids):
    '''
    stmt_name : prepared�������֡�
    query : ��ѯ��䡣
    param_type_oids : �������͵�oid�б����oid��ֵΪ0����ôϵͳ���Լ��Ƶ������ͣ�
                      ����ָ���ĸ�������С�ڲ�ѯ�����ʵ�ʵĲ���������û��ָ���Ĳ�����ϵͳ�Լ��Ƶ������͡�
    '''
    param_cnt = len(param_type_oids)
    msg_data = make_cstr(stmt_name) + make_cstr(query) + struct.pack('>h', param_cnt)
    msg_data += struct.pack('>%di'%param_cnt, *param_type_oids)
    return make_Msg0(b'P', msg_data)

def process_PasswordMessage(msg_type, msg_data):
    return ('PasswordMessage', msg_type, msg_data)
def make_PasswordMessage1(msg_res):
    return make_Msg0(msg_res[1], msg_res[2])
def make_PasswordMessage2(password, user_name = None, md5_salt = None):
    if md5_salt:
        if not user_name:
            raise SystemError('BUG: should provide user_name for md5 authentication')
        password = b'md5' + md5(md5(password + user_name) + md5_salt)
    return make_Msg0(b'p', make_cstr(password)) # ��Ϣ������Сд��p

def process_Query(msg_type, msg_data):
    return ('Query', msg_type, msg_data)
def make_Query1(msg_res):
    return make_Query2(msg_res[2])
def make_Query2(sql):
    return make_Msg0(b'Q', make_cstr(sql))

def process_Sync(msg_type, msg_data):
    return ('Sync', msg_type)
def make_Sync1(msg_res):
    return make_Sync2()
def make_Sync2():
    return make_Msg0(b'S', b'')

def process_Terminate(msg_type, msg_data):
    return ('Terminate', msg_type)
def make_Terminate1(msg_res):
    return make_Terminate2()
def make_Terminate2():
    return make_Msg0(b'X', b'')

fe_msg_type_info = {
    b'B' : (process_Bind, make_Bind1),                       # Bind
    b'C' : (process_Close, make_Close1),                     # Close
    b'd' : (process_CopyData, make_CopyData1),               # CopyData (��be����)
    b'c' : (process_CopyDone, make_CopyDone1),               # CopyDone (��be����)
    b'f' : (process_CopyFail, make_CopyFail1),               # CopyFail
    b'D' : (process_Describe, make_Describe1),               # Describe
    b'E' : (process_Execute, make_Execute1),                 # Execute
    b'H' : (process_Flush, make_Flush1),                     # Flush
    b'F' : (process_FunctionCall, make_FunctionCall1),       # FunctionCall
    b'P' : (process_Parse, make_Parse1),                     # Parse  (��д��P)
    b'p' : (process_PasswordMessage, make_PasswordMessage1), # PasswordMessage  (Сд��p)
    b'Q' : (process_Query, make_Query1),                     # Query
    b'S' : (process_Sync, make_Sync1),                       # Sync
    b'X' : (process_Terminate, make_Terminate1),             # Terminate
    # ������3����Ϣû����Ϣ�����ַ��������������Ӻ��FE���͸�BE�ĵ�һ����Ϣ��
    # CancelRequest
    # SSLRequest
    # StartupMessage
}
PG_PROTO_VERSION2_NUM = 131072
PG_PROTO_VERSION3_NUM = 196608
PG_CANCELREQUEST_CODE = 80877102
PG_SSLREQUEST_CODE    = 80877103
# 
# ������FE->BE�ĵ�һ����Ϣ����������Ϣû����Ϣ���͡�
# ����û�ж�Ӧ����Ϣ���ͣ����ؽ������b'\x00'��������Ϣ���͡�
# msg_data��������ʾ��Ϣ���ȵ���4���ֽڡ�
# 
# V3 StartupMsg������μ�postmaster.c�е�ProcessStartupPacket������
# ���԰���������Щ��
#   database
#   user
#   options       ������ѡ��
#   replication   ��Чֵtrue/false/1/0/database��database��ʾ���ӵ�databaseѡ��ָ�������ݿ⣬һ�������߼����ơ�
#   <guc option>  ����gucѡ�����: client_encoding/application_name
# 
def process_Startup(msg_data):
    idx = 0
    code = struct.unpack('>i', msg_data[idx:idx+4])[0]
    idx += 4
    if code == PG_PROTO_VERSION3_NUM: # StartupMessage for version 3
        res = ('StartupMessage', b'\x00', code, [])
        param_list = res[3]
        while msg_data[idx] != 0:
            param_name = get_cstr(msg_data, idx)
            idx += len(param_name)
            param_val = get_cstr(msg_data, idx)
            idx += len(param_val)
            param_list.append((param_name, param_val))
        return res
    elif code == PG_PROTO_VERSION2_NUM: # StartupMessage for version 2
        return ('StartupMessage', b'\x00', code, msg_data[idx:])
    elif code == PG_CANCELREQUEST_CODE: # CancelRequest
        pid, skey = struct.unpack('>ii', msg_data[idx:idx+8])
        return ('CancelRequest', b'\x00', pid, skey)
    elif code == PG_SSLREQUEST_CODE: # SSLRequest
        return ('SSLRequest', b'\x00')
    else:
        raise RuntimeError('unknown startup message:(%d, %s)' % (code, msg_data))

def make_Startup1(msg_res):
    if msg_res[0] == 'StartupMessage':
        return make_StartupMessage1(msg_res)
    elif msg_res[0] == 'CancelRequest':
        return make_CancelRequest1(msg_res)
    elif msg_res[0] == 'SSLRequest':
        return make_SSLRequest1(msg_res)
    else:
        raise RuntimeError('unknown startup message: %s' % (msg_res, ))

def make_StartupMessage1(msg_res):
    version = msg_res[2]
    if version == PG_PROTO_VERSION3_NUM:
        param_list = msg_res[3]
        param_dict = {kv[0].decode('latin1'):kv[1] for kv in param_list}
        return make_StartupMessage2(**param_dict)
    elif version == PG_PROTO_VERSION2_NUM:
        msg_data = struct.pack('>i', version) + msg_res[3]
        return struct.pack('>i', len(msg_data)+4) + msg_data
# ��param name˳������װ����Ϊ����������dict��key��
def make_StartupMessage2(**param_dict):
    res = b''
    res += struct.pack('>i', PG_PROTO_VERSION3_NUM)
    param_name_list = list(param_dict.keys())
    param_name_list.sort()
    for k in param_name_list:
        res += make_cstr(k.encode('latin1')) + make_cstr(param_dict[k])
    res += b'\0'
    res = struct.pack('>i', len(res)+4) + res
    return res

def make_CancelRequest1(msg_res):
    return make_CancelRequest2(msg_res[2], msg_res[3])
def make_CancelRequest2(pid, skey):
    res = struct.pack('>i', 16)
    res += struct.pack('>i', PG_CANCELREQUEST_CODE)
    res += struct.pack('>i', pid)
    res += struct.pack('>i', skey)
    return res

def make_SSLRequest1(msg_res):
    return make_SSLRequest2()
def make_SSLRequest2():
    res = struct.pack('>i', 8)
    res += struct.pack('>i', PG_SSLREQUEST_CODE)
    return res
# 
# ������Ϣ����
# 
def recv_size(s, sz):
    ret = b'';
    while sz > 0:
        tmp = s.recv(sz)
        if not tmp:
            raise RuntimeError('the peer(%s) closed the connection. last recved:[%s]' % (s.getpeername(), ret));
        ret += tmp
        sz -= len(tmp)
    return ret
# ����FE->BE�ĵ�һ����Ϣ��
def recv_fe_startup_msg(s):
    msg_len = recv_size(s, 4)
    msg_len = struct.unpack('>i', msg_len)[0]
    msg_len -= 4
    msg_data = b''
    if msg_len > 0:
        msg_data = recv_size(s, msg_len)
    return msg_data
# ���startup��Ϣ�Ƿ���������data������ͷ��ʾ���ȵ�4���ֽڡ�
def startup_msg_is_complete(data):
    data_len = len(data)
    if data_len <= 4:
        return False
    msg_len = struct.unpack('>i', data[:4])[0]
    return data_len == msg_len
# ������һ����Ϣ��
# ע�⣺�����������ܲ��õ�ʹ�÷��㡣���Ҫ�������ܣ���ô�������������ݣ�Ȼ����parse_pg_msg�Ⱥ�����
def recv_pg_msg(s, process, msg_type_info = None, timeout = 0):
    s.settimeout(timeout)
    try:
        msg_type = recv_size(s, 1)
    except socket.timeout:
        return None
    except OSError as err:
        if err.errno in NONBLOCK_SEND_RECV_OK:
            return None
        else:
            raise
    finally:
        s.settimeout(None)
    msg_len = recv_size(s, 4)
    msg_len = struct.unpack('>i', msg_len)[0]
    msg_len -= 4
    msg_data = b''
    if msg_len:
        msg_data = recv_size(s, msg_len)
    if process:
        return msg_type_info[msg_type][0](msg_type, msg_data)
    else:
        return (msg_type, msg_data)
def recv_be_msg(s, process = True, timeout = 0):
    return recv_pg_msg(s, process, be_msg_type_info, timeout)
def recv_fe_msg(s, process = True, timeout = 0):
    return recv_pg_msg(s, process, fe_msg_type_info, timeout)
# 
# ��data����ȡ�����Ϣ�����ú�����������parse��FE����BE�ĵ�һ����Ϣ��
# data : ԭʼ���ݡ�
# max_msg : �����ȡ���ٸ���Ϣ�������Ϊ0��ʾ��ȡ���С�
# process : �Ƿ񷵻ش��������Ϣ��
# msg_type_info : �ֵ���󣬰�������Ϣ���Ͷ�Ӧ�Ĵ�������
# 
def parse_pg_msg(data, max_msg = 0, process = False, msg_type_info = None):
    idx = 0
    data_len = len(data)
    msg_list = []
    cnt = 0
    while True:
        if data_len - idx < 5:
            break
        msg_type = data[idx:idx+1]
        msg_len = struct.unpack('>i', data[idx+1:idx+1+4])[0]
        if data_len - idx < msg_len + 1:
            break
        msg_data = data[idx+5:idx+msg_len+1]
        idx += msg_len + 1
        
        if process:
            msg_list.append(msg_type_info[msg_type][0](msg_type, msg_data))
        else:
            msg_list.append((msg_type, msg_data))
        cnt += 1
        if max_msg > 0 and cnt >= max_msg:
            break
    return (idx, msg_list)
def parse_fe_msg(data, max_msg = 0, process = True):
    return parse_pg_msg(data, max_msg, process, fe_msg_type_info)
def parse_be_msg(data, max_msg = 0, process = True):
    return parse_pg_msg(data, max_msg, process, be_msg_type_info)
# startup_msg�еĲ���ֵ�����ͱ�����bytes��startup_msg�б�����user
def make_pg_connection(host, port, **startup_msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(make_StartupMessage2(**startup_msg))
    return s
# ������pg�����ӣ���ɵ�½���̣�ֱ�����յ�ReadyForQuery����ErrorResponse��������յ�ErrorResponse�Ǿ��׳��쳣��
# �����½�ɹ�����ô����(socket, parameter_dict, (pid, cancelkey))
def make_pg_login(host, port, password = b'', **startup_msg):
    param_dict = {}
    key_data = None
    s = make_pg_connection(host, port, **startup_msg)
    msg_res = recv_be_msg(s, timeout=None)
    if msg_res[0] == 'AuthenticationOk':
        None
    elif msg_res[0] == 'AuthenticationCleartextPassword' or msg_res[0] == 'AuthenticationMD5Password':
        # ����PasswordMessage
        if msg_res[0] == 'AuthenticationCleartextPassword':
            s.sendall(make_PasswordMessage2(password))
        else:
            s.sendall(make_PasswordMessage2(password, startup_msg['user'], msg_res[2]))
        # ����AuthentictionOk����ErrorResponse
        msg_res = recv_be_msg(s, timeout=None)
        if msg_res[0] == 'ErrorResponse':
            raise RuntimeError('authentication fail:%s' % (msg_res, ))
    elif msg_res[0] == 'ErrorResponse':
        raise RuntimeError('got ErrorResponse from be while authentication:%s' % (msg_res, ))
    else:
        raise RuntimeError('do not support this authentication type:%s' % (msg_res, ))
    # ������Ϣֱ��ReadyForQuery����ErrorResponse
    while True:
        msg_res = recv_be_msg(s, timeout=None)
        if msg_res[0] == 'ErrorResponse':
            raise RuntimeError('got ErrorResponse from be after authentication:%s' % (msg_res, ))
        elif msg_res[0] == 'ParameterStatus':
            k = msg_res[2].rstrip(b'\x00').decode('latin1')
            v = msg_res[3].rstrip(b'\x00')
            param_dict[k] = v
        elif msg_res[0] == 'BackendKeyData':
            key_data = (msg_res[2], msg_res[3])
        elif msg_res[0] == 'ReadyForQuery':
            break
    # ����client_encoding���ֽڴ�decode��unicode��
    enc = param_dict['client_encoding'].decode('latin1')
    for k in param_dict:
        param_dict[k] = param_dict[k].decode(enc)
    return (s, param_dict, key_data)
# ִ��һ����䣬���ʧ�����׳��쳣OSError/RuntimeError��
# ����ɹ����򷵻�(cmd_status, row_desc, row_list)
def execute(s, sql):
    cmd_status = None
    row_desc = None
    row_list = []
    ex = None
    s.sendall(make_Query2(sql))
    while True:
        msg_res = recv_be_msg(s, timeout=None)
        if msg_res[0] == 'EmptyQueryResponse':
            ex = RuntimeError('got EmptyQueryResponse')
        elif msg_res[0] == 'ErrorResponse':
            # ĳ������·��������ڷ���ErrorResponse֮����˳��ˣ������ٷ���ReadyForQuery���������������һ�ε���recv_be_msg��ʱ����׳��쳣��
            # ���⵱���ִ�й�����Ҳ���ܷ���ErrorResponse��Ҳ����˵�ڷ���DataRow֮��Ҳ�п��ܷ���ErrorResponse��
            ex = RuntimeError('got ErrorResponse:%s' % (msg_res, ))
        elif msg_res[0] == 'RowDescription':
            row_desc = msg_res[3]
        elif msg_res[0] == 'DataRow':
            row = []
            for col in msg_res[3]:
                if col[0] == -1:
                    row.append(None)
                else:
                    row.append(col[1])
            row_list.append(row)
        elif msg_res[0] == 'CommandComplete':
            cmd_status = msg_res[2].rstrip(b'\x00').decode('latin1')
            cmd_status = cmd_status.split()
        elif msg_res[0] == 'ReadyForQuery':
            break
    if ex:
        raise ex
    return (cmd_status, row_desc, row_list)
#************************************************************************************************************************************************
#!/bin/env python3
# -*- coding: GBK -*-
# 
# poller base class
# 
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

#************************************************************************************************************************************************
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
# 
# utility functions
try:
    import setproctitle
except ImportError:
    setproctitle = None
def set_process_title(title):
    if not setproctitle:
        return
    setproctitle.setproctitle(title)

import datetime
def get_now_time():
    d = datetime.datetime.now()
    return '%.4d-%.2d-%.2d %.2d:%.2d:%.2d' % (d.year, d.month, d.day, d.hour, d.minute, d.second)
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
# 
# αpg���ݿ⡣��������Ҫ�ṩselect_table�������ڸú����ڸ��ݱ���������ص����ݡ�������Ϣ��RowDescription / DataRow / CommandComplete
#
# recving_StartupMessage -> sending_AuthenticationMD5Password -> recving_PasswordMessage -> sending_AuthenticationOk -> recving_Query -> sending_QueryResult
#                                                                         |                                                      |<---------------|
#                                                                         |-> sending_ErrorResponse
# 
class pseudo_pg(object):
    def __init__(self, password, s, startup_msg = None):
        self.password = password
        self.s = s
        self.send_data = b''
        self.recv_data = b''
        self.startup_msg = None
        self.client_encoding = None
        self.status = 'recving_StartupMessage'
        if startup_msg:
            self.startup_msg = self.startup_msg_to_dict(startup_msg)
            self.send_data = make_AuthenticationXXX2('AuthenticationMD5Password', b'1234')
            self.status = 'sending_AuthenticationMD5Password'
    def fileno(self):
        return self.s.fileno()
    def close(self):
        self.s.close()
    def send(self):
        n = self.s.send(self.send_data)
        self.send_data = self.send_data[n:]
        if self.send_data:
            return 'w'
        
        if self.status == 'sending_AuthenticationMD5Password':
            self.status = 'recving_PasswordMessage'
            return 'r'
        if self.status == 'sending_ErrorResponse':
            raise RuntimeError('close because ErrorResponse sent')
        if self.status == 'sending_AuthenticationOk':
            self.status = 'recving_Query'
            return 'r'
        if self.status == 'sending_QueryResult':
            self.status = 'recving_Query'
            return 'r'
    def recv(self):
        data = myrecv(self.s, 4*1024)
        if data == None:
            return 'r'
        if not data:
            raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
        self.recv_data += data
        
        if self.status == 'recving_StartupMessage':
            if not startup_msg_is_complete(self.recv_data):
                return 'r'
            msg = process_Startup(self.recv_data[4:])
            self.recv_data = b''
            logging.debug('recv: %s', msg)
            if not (msg[0] == 'StartupMessage' and msg[2] == PG_PROTO_VERSION3_NUM):
                raise RuntimeError('do not support this startup msg:%s' % (msg, ))
            self.startup_msg = self.startup_msg_to_dict(msg)
            self.send_data = make_AuthenticationXXX2('AuthenticationMD5Password', b'1234')
            self.status = 'sending_AuthenticationMD5Password'
            return 'w'
        if self.status == 'recving_PasswordMessage':
            res = parse_fe_msg(self.recv_data)
            if not res[1]:
                return 'r'
            msg = res[1][0]
            self.recv_data = self.recv_data[res[0]:]
            logging.debug('recv: %s  recv_data:%s', msg, self.recv_data)
            if msg[0] != 'PasswordMessage':
                raise RuntimeError('this msg should be PasswordMessage:%s' % (msg, ))
            msg1 = make_PasswordMessage1(msg)
            msg2 = make_PasswordMessage2(self.password, self.startup_msg[b'user\x00'].rstrip(b'\x00'), b'1234')
            logging.debug('msg2: %s  msg1: %s', msg2, msg1)
            if msg2 != msg1:
                self.send_data = make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'28P01'), (b'M', b'invalid password')])
                self.status = 'sending_ErrorResponse'
                return 'w'
            else:
                self.send_data = self.gen_auth_ok()
                self.status = 'sending_AuthenticationOk'
                return 'w'
        if self.status == 'recving_Query':
            res = parse_fe_msg(self.recv_data)
            if not res[1]:
                return 'r'
            msg = res[1][0]
            self.recv_data = self.recv_data[res[0]:]
            logging.debug('recv: %s  recv_data:%s', msg, self.recv_data)
            if msg[0] == 'Terminate':
                raise RuntimeError('close because Terminate msg recved')
            elif msg[0] != 'Query':
                self.send_data = make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'0A000'), (b'M', b'only suport simple Query message')])
                self.send_data += make_ReadyForQuery2(b'I')
                self.status = 'sending_QueryResult'
                return 'w'
            else:
                sql = msg[2].rstrip(b'\x00').decode(self.client_encoding).strip().rstrip(';').lower()
                sql_elem_list = sql.split() # ֻ֧��select ... from tablename [...]
                tablename = None
                for i in range(len(sql_elem_list)):
                    if sql_elem_list[i] == 'from':
                        tablename = sql_elem_list[i+1]
                        break
                if sql_elem_list[0] != 'select' or not tablename:
                    self.send_data = make_ErrorResponse2([(b'S', b'ERROR'), (b'C', b'0A000'), (b'M', b'only suport sql such as "select ... from tablename ..."')])
                    self.send_data += make_ReadyForQuery2(b'I')
                    self.status = 'sending_QueryResult'
                    return 'w'
                self.send_data = self.select_table(tablename, sql)
                self.send_data += make_ReadyForQuery2(b'I')
                self.status = 'sending_QueryResult'
                return 'w'
        raise RuntimeError('BUG: unknown status: %s %s' % (self.status, self.recv_data))
    def select_table(self, tablename, sql):
        # ��Ҫ���� RowDescription / DataRow / CommandComplete
        data  = make_RowDescription2([(b'colume1', 0, 0, 25, -1, -1, 0)])
        data += make_DataRow2([(4, b'aaaa')])
        data += make_DataRow2([(5, b'bbbbb')])
        data += make_CommandComplete2(b'SELECT 2')
        return data
    def gen_auth_ok(self):
        data  = make_AuthenticationXXX2('AuthenticationOk')
        data += make_ParameterStatus2(b'application_name', self.startup_msg.get(b'application_name\x00', b''))
        self.client_encoding = self.startup_msg.get(b'client_encoding\x00', b'utf8')
        data += make_ParameterStatus2(b'client_encoding', self.client_encoding)
        self.client_encoding = self.client_encoding.rstrip(b'\x00').decode('latin1')
        data += make_ParameterStatus2(b'DateStyle', b'ISO, MDY')
        data += make_ParameterStatus2(b'integer_datetimes', b'on')
        data += make_ParameterStatus2(b'IntervalStyle', b'postgres')
        data += make_ParameterStatus2(b'is_superuser', b'on')
        data += make_ParameterStatus2(b'server_encoding', b'UTF8')
        data += make_ParameterStatus2(b'server_version', b'9.5devel')
        data += make_ParameterStatus2(b'session_authorization', self.startup_msg.get(b'user\x00'))
        data += make_ParameterStatus2(b'standard_conforming_strings', b'on')
        data += make_ParameterStatus2(b'TimeZone', b'Asia/Chongqing')
        data += make_BackendKeyData2(1, 123456)
        data += make_ReadyForQuery2(b'I')
        return data
    def startup_msg_to_dict(self, startup_msg):
        res = {}
        for param in startup_msg[3]:
            res[param[0]] = param[1]
        return res
    def make_row_desc(self, col_name_list):
        common_desc = (0, 0, 25, -1, -1, 0)
        col_desc_list = []
        for colname in col_name_list:
            col_desc_list.append((colname,) + common_desc)
        data  = make_RowDescription2(col_desc_list)
        return data
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

class pending_fe_connection(object):
    def __init__(self, s):
        self.s = s
        self.s.settimeout(0)
        self.startup_msg_raw = b''
        self.startup_msg = None
        self._is_readonly = False
    def is_readonly(self):
        return self._is_readonly
    def fileno(self):
        return self.s.fileno()
    def close(self):
        self.s.close()
    def recv(self):
        data = myrecv(self.s, 1024*4)
        if data == None:
            return
        if not data:
            raise RuntimeError('the peer(%s) closed the connection' % (self.s.getpeername(), ))
        self.startup_msg_raw += data
    def check_startup(self):
        if startup_msg_is_complete(self.startup_msg_raw):
            self.startup_msg = process_Startup(self.startup_msg_raw[4:])
            self._process_readonly()
            # ����������Ϣ��raw���ݣ���Ϊmake_StartupMessage2�Բ������������������Ϳ���ͨ��raw�������Ƚ�startup msg�ˡ�
            self.startup_msg_raw = make_Startup1(self.startup_msg) 
            return True
        return False
    def _process_readonly(self):
        if not self.is_StartupMessageV3():
            return
        param_list = self.startup_msg[3]
        for i in range(len(param_list)):
            if param_list[i][0] == b'database\x00':
                v = param_list[i][1]
                if v.endswith(b'@\x00'):
                    param_list[i] = (b'database\x00', v[:-2] + b'\x00')
                    self._is_readonly = True
                    break
    def is_SSLRequest(self):
        return self.startup_msg[0] == 'SSLRequest'
    def is_CancelRequest(self):
        return self.startup_msg[0] == 'CancelRequest'
    def is_StartupMessageV2(self):
        return self.startup_msg[0] == 'StartupMessage' and self.startup_msg[2] == PG_PROTO_VERSION2_NUM
    def is_StartupMessageV3(self):
        return self.startup_msg[0] == 'StartupMessage' and self.startup_msg[2] == PG_PROTO_VERSION3_NUM
    def get_param_val(self, param_name):
        return get_param_val_from_startupmsg(self.startup_msg, param_name)

def get_param_val_from_startupmsg(startup_msg, param_name):
    if not (startup_msg[0] == 'StartupMessage' and startup_msg[2] == PG_PROTO_VERSION3_NUM):
        raise SystemError('BUG: only can call get_param_val_from_startupmsg on StartupMessage of version 3' % (startup_msg, ))
    if type(param_name) == str:
        param_name = param_name.encode('latin1')
    param_name = make_cstr(param_name)
    for n, v in startup_msg[3]:
        if param_name == n:
            return v
    return None
# ���pg�Ƿ���ã������ڼ������ʹӿ⡣
class pg_monitor(object):
    # addr : ����ĵ�ַ��
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
def read_conf_file(conf_file):
    f = open(conf_file, encoding='gbk')
    data = f.read()
    f.close()
    this_path = os.path.dirname(conf_file)
    local_dict = {'this_path' : this_path}
    exec(data, None, local_dict)
    return local_dict.pop('pg_proxy_conf')
def close_fobjs(x_list):
    for x in x_list:
        if type(x) == list:
            for fobj in x:
                fobj.close()
            x.clear()
        else:
            x.close()
def get_max_len(s_list):
    max_len = 0
    for s in s_list:
        if len(s) > max_len:
            max_len = len(s)
    return max_len
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
    
    g_conf = read_conf_file(g_conf_file)
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


