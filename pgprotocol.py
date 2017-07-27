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
import sys, os
import struct, socket, hashlib

from netutils import NONBLOCK_SEND_RECV_OK

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

# main
if __name__ == '__main__':
    pass

