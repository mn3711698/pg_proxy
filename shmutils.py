#!/bin/env python3
# -*- coding: GBK -*-
# 
# �����ڴ��д
# 
import sys, os
import struct, socket
import datetime

# 
# ������������д��ÿ��startup_msg_raw+be_addr����һ����Ӧ�Ŀ�����������key����md5ֵ��
# 
class idle_cnn_hash_table(object):
    KEY_SZ = 16
    VAL_SZ = 2
    ITEM_SZ = KEY_SZ + VAL_SZ
    EMPTY_KEY = b'\x00'*16
    # sidx��part�е���ʼλ��
    def __init__(self, shm, part_idx, sidx):
        self.shm = shm
        self.part_idx = part_idx
        self.sidx = sidx 
        x = shm.get_part_bound(part_idx)
        self.ht_sz = (x[1] - x[0] - sidx) // self.ITEM_SZ # ��ϣ���С
    def _hash(self, key):
        x = struct.unpack('4I', key)
        s = sum(x)
        return s % self.ht_sz
    # ����Ƿ������key��Ӧ������أ�
    #   .) (None, 0/1) : ��������key��Ӧ���0��ʾ��ϣ���л��пռ䣻1��ʾû�пռ��ˡ�
    #   .) (0, v)      : ������key��Ӧ�������ֵv<=0��
    #   .) (1, v)      : ������key��Ӧ�����ֵ>0��v����ֵ��1�����ֵ��
    # ���ָ����timeout����ָ����ʱ����û�л��semphore����ô�׳��쳣��
    # key��md5ֵ�������ƴ���
    def get(self, key, timeout=None):
        self.key = key
        self.hv = self._hash(key)
        return self.shm.get(self.sidx, -1, self.part_idx, self._get_pf, timeout)
    def _get_pf(self, mm, sidx, sz, part_bound):
        sidx += part_bound[0]
        if sz < 0:
            eidx = part_bound[1]
        else:
            eidx = part_bound[0] + sidx + sz
        
        idx = sidx + self.hv * self.ITEM_SZ
        ret = self._check_item(mm, idx)
        # ���ڹ�ϣ���keyֻ������������ret==(None, 0)��ʾkey��û�н����ϣ��
        if ret[0] != None or ret[1] == 0:
            return ret
        # ��self.hvλ��û���ҵ�ƥ���key������ǰ�����顣
        idx2 = idx + self.ITEM_SZ
        while idx2 + self.ITEM_SZ <= eidx:
            ret = self._check_item(mm, idx2)
            if ret[0] != None or ret[1] == 0:
                return ret
            idx2 += self.ITEM_SZ
        # ��ͷ��ʼ����
        idx2 = sidx
        while idx2 + self.ITEM_SZ <= idx:
            ret = self._check_item(mm, idx2)
            if ret[0] != None or ret[1] == 0:
                return ret
            idx2 += self.ITEM_SZ
        return (None, 1)
    def _check_item(self, mm, idx):
        k = mm[idx:idx+self.KEY_SZ]
        if k == self.key:
            v = struct.unpack('h', mm[idx+self.KEY_SZ:idx+self.ITEM_SZ])[0]
            if v <= 0:
                return (0, v)
            else:
                v = v - 1
                mm[idx+self.KEY_SZ:idx+self.ITEM_SZ] = struct.pack('h', v)
                return (1, v)
        elif k == self.EMPTY_KEY:
            return (None, 0)
        else:
            return (None, 1)
    # �޸�key��Ӧ��ֵ����val�ӵ���ϣ�����Ѿ��е�ֵ��
    # �����µ�ֵ�������ϣ��û�пռ��ˣ��򷵻�None��
    def put(self, key, val, timeout=None):
        self.key = key
        self.val = val
        self.hv = self._hash(key)
        return self.shm.put(val, self.sidx, self.part_idx, self._put_pf, timeout)
    def _put_pf(self, mm, data, sidx, part_bound):
        sidx += part_bound[0]
        eidx = part_bound[1]
        
        idx = sidx + self.hv * self.ITEM_SZ
        ret = self._put_item(mm, idx)
        if ret != None:
            return ret
        # ��self.hvλ�ñ�����keyռ���ˣ�����ǰ�����顣
        idx2 = idx + self.ITEM_SZ
        while idx2 + self.ITEM_SZ <= eidx:
            ret = self._put_item(mm, idx2)
            if ret != None:
                return ret
            idx2 += self.ITEM_SZ
        # ��ͷ��ʼ����
        idx2 = sidx
        while idx2 + self.ITEM_SZ <= idx:
            ret = self._put_item(mm, idx2)
            if ret != None:
                return ret
            idx2 += self.ITEM_SZ
        return None
    def _put_item(self, mm, idx):
        k = mm[idx:idx+self.KEY_SZ]
        if k == self.key:
            v = struct.unpack('h', mm[idx+self.KEY_SZ:idx+self.ITEM_SZ])[0]
            v += self.val
            mm[idx+self.KEY_SZ:idx+self.ITEM_SZ] = struct.pack('h', v)
            return v
        elif k == self.EMPTY_KEY:
            mm[idx:idx+self.ITEM_SZ] = self.key + struct.pack('h', self.val)
            return self.val
        else:
            return None
# 
# �����ڴ�Ŀ�ͷ8���ֽڷֱ���Ϊidle_list/use_list��ͷ��
# ÿ��item����Ч��С��ITEM_SZ(���ڱ���ʵ�ʵ�����)��itemͷ��5���ֽڣ���һ���ֽڱ�ʾ�ǿ���(I)�����ѱ���(U)��������4���ֽ�ָ����һ��item��
# �ڲ�itemָ��ָ��item��ͷ�������ظ��ⲿ����ָ�򱣴�ʵ�����ݵĿ�ͷλ�á�
# ָ��ֵ���������part_idx����ʼλ�õģ�������������������ڴ����ʼλ�á�ָ��ֵ-1��ʾ������
# 
# idle_idx / use_idx����������������ڴ����ʼλ�á�
# 
class item_table(object):
    ITEM_SZ = 10 # ��������Ҫ�����ֵ
    # sidx��part_idx�е���ʼλ�ã�part��sidx֮ǰ�Ŀռ䲻�á�
    def __init__(self, shm, part_idx, sidx=0):
        self.shm = shm
        self.part_idx = part_idx
        self.sidx = sidx
        self.part_sidx, self.part_eidx = shm.get_part_bound(part_idx)
        self.idle_idx = self.part_sidx + self.sidx
        self.use_idx = self.idle_idx + 4
    # ��ʼ��idle/use�б�����idle item��Ŀ��
    # �����ڴ�Ĵ����ߵ��ø÷�����
    @staticmethod
    def init_idle_use_list(shm, part_idx, item_sz, sidx=0):
        cnt = 0
        part_sidx, part_eidx = shm.get_part_bound(part_idx)
        mm = shm.mm
        mm[part_sidx+sidx+4:part_sidx+sidx+8] = struct.pack('i', -1) # use list
        off = sidx + 8
        mm[part_sidx+sidx:part_sidx+sidx+4] = struct.pack('i', off) # idle list
        idx = part_sidx + off
        while idx + 5 + item_sz <= part_eidx:
            mm[idx:idx+1] = b'I'
            mm[idx+1:idx+5] = struct.pack('i', off + 5 + item_sz)
            off += 5 + item_sz
            idx = part_sidx + off
            cnt += 1
        mm[idx-item_sz-4:idx-item_sz] = struct.pack('i', -1)
        return cnt
    # ���Ҳ����ؿ��е�item������ֵָ��item�б���ʵ�����ݵ�λ�á����û�п���item���򷵻�-1��
    def find_idle_item(self, timeout=None):
        def pf(mm, sidx, sz, part_bound):
            x = mm[self.idle_idx:self.idle_idx+4]
            item_idx = struct.unpack('i', x)[0]
            if item_idx == -1:
                return item_idx
            
            item_pos = self.part_sidx + item_idx
            mm[self.idle_idx:self.idle_idx+4] = mm[item_pos+1:item_pos+5]
            mm[item_pos:item_pos+1] = b'U'
            mm[item_pos+1:item_pos+5] = mm[self.use_idx:self.use_idx+4]
            mm[self.use_idx:self.use_idx+4] = struct.pack('i', item_idx)
            return item_idx + 5
        return self.shm.get(part_idx=self.part_idx, pf=pf, timeout=timeout)
    # ��item_ptr�Żص�����������
    def put_to_idle_list(self, item_ptr, timeout=None):
        def pf(mm, sidx, sz, part_bound):
            item_pos = self.part_sidx + item_ptr
            # ��use_listɾ��item_ptr
            prev_idx = self.use_idx
            next_item = struct.unpack('i', mm[prev_idx:prev_idx+4])[0]
            while next_item + 5 != item_ptr:
                prev_idx = self.part_sidx + next_item + 1
                next_item = struct.unpack('i', mm[prev_idx:prev_idx+4])[0]
            mm[prev_idx:prev_idx+4] = mm[item_pos-4:item_pos]
            # ��item_ptr��ӵ�idle_list
            mm[item_pos-5:item_pos+self.ITEM_SZ] = b'\x00' * (self.ITEM_SZ + 5)
            mm[item_pos-5:item_pos-4] = b'I'
            mm[item_pos-4:item_pos] = mm[self.idle_idx:self.idle_idx+4]
            mm[self.idle_idx:self.idle_idx+4] = struct.pack('i', item_ptr-5)
            return None
        return self.shm.get(part_idx=self.part_idx, pf=pf, timeout=timeout)
    # ��ȡitem��ֵ��item_ptrָ��item�б���ʵ�����ݵĿ�ͷ��
    def get(self, item_ptr, pf=None, timeout=None):
        return self.shm.get(item_ptr, self.ITEM_SZ, self.part_idx, pf, timeout)
    # ��item_dataд��item_ptrָ���λ�á�
    def put(self, item_ptr, item_data, pf=None, timeout=None):
        # pf�����������item_data
        if pf == None and len(item_data) != self.ITEM_SZ:
            raise RuntimeError('len of item_data(%s) != %d' % (item_data, self.ITEM_SZ))
        return self.shm.put(item_data, item_ptr, self.part_idx, pf, timeout)
    # ��ȡ����item
    def getall(self, timeout=None):
        def pf(mm, sidx, sz, part_bound):
            res = []
            x = mm[self.use_idx:self.use_idx+4]
            item_idx = struct.unpack('i', x)[0]
            while item_idx != -1:
                item_pos = self.part_sidx + item_idx
                res.append(mm[item_pos+5:item_pos+5+self.ITEM_SZ])
                x = mm[item_pos+1:item_pos+5]
                item_idx = struct.unpack('i', x)[0]
            return res
        return self.shm.get(part_idx=self.part_idx, pf=pf, timeout=timeout)
# 
# item��������Ϣ������������Щ��Ϣ: 
#   fe_ip/fe_port    : ǰ��ip(4�ֽ�)�Ͷ˿�(2�ֽ�)��
#   be_ip/be_port    : ���ip�Ͷ˿ڡ�
#   use_num          : ʹ�ô���(4�ֽ�)��
#   update_time      : ������ʱ�䣬����Ϊtimestamp��float���ͣ�4���ֽڡ�
#   startup_msg_raw  : ���ڱȽϳ������Զ�һЩ����ѡ����������д������u����user��d����database��a����application_name��e����client_encoding�ȵȣ�
#                      ��д��ʹ���ߴ���������bytes��
# ǰ��4��Ĵ�С�ǹ̶��ģ�Ϊ20���ֽڡ���startup_msg_raw����80���ֽڣ�������b'\x00'��䡣
# 
class cnn_info_table(item_table):
    ITEM_SZ = 20 + 80
    
    FE_IP_IDX = 0
    FE_PORT_IDX = 4
    BE_IP_IDX = 6
    BE_PORT_IDX = 10
    USE_NUM_IDX = 12
    UPDATE_TIME_IDX = 16
    STARTUP_MSG_RAW_IDX = 20
    
    def parse_item(self, item_data):
        ret = {}
        ret['fe_ip'] = socket.inet_ntoa(item_data[self.FE_IP_IDX:self.FE_IP_IDX+4])
        ret['fe_port'] = struct.unpack('H', item_data[self.FE_PORT_IDX:self.FE_PORT_IDX+2])[0]
        ret['be_ip'] = socket.inet_ntoa(item_data[self.BE_IP_IDX:self.BE_IP_IDX+4])
        ret['be_port'] = struct.unpack('H', item_data[self.BE_PORT_IDX:self.BE_PORT_IDX+2])[0]
        ret['use_num'] = struct.unpack('i', item_data[self.USE_NUM_IDX:self.USE_NUM_IDX+4])[0]
        x = struct.unpack('f', item_data[self.UPDATE_TIME_IDX:self.UPDATE_TIME_IDX+4])[0]
        ret['update_time'] = datetime.datetime.fromtimestamp(x)
        x = item_data[self.STARTUP_MSG_RAW_IDX:]
        sz = struct.unpack('>i', x[:4])[0]
        ret['startup_msg_raw'] = x[:sz]
        return ret

    def get(self, item_ptr, timeout=None):
        item_data = super().get(item_ptr, None, timeout)
        return self.parse_item(item_data)
    def getall(self, timeout=None):
        item_data_list = super().getall(timeout)
        return [self.parse_item(d) for d in item_data_list]
    def put(self, item_ptr, timeout=None, **kwargs):
        def pf(mm, item_data, item_ptr, part_bound):
            item_pos = part_bound[0] + item_ptr
            for x in item_data:
                s = item_pos + x[0]
                e = item_pos + x[0] + len(x[1])
                mm[s:e] = x[1]
            return len(item_data)
        
        item_data = [] # list of (idx, data)
        for k in kwargs:
            if k == 'fe_ip':
                data = socket.inet_aton(kwargs[k])
                item_data.append((self.FE_IP_IDX, data))
            elif k == 'fe_port':
                data = struct.pack('H', kwargs[k])
                item_data.append((self.FE_PORT_IDX, data))
            elif k == 'be_ip':
                data = socket.inet_aton(kwargs[k])
                item_data.append((self.BE_IP_IDX, data))
            elif k == 'be_port':
                data = struct.pack('H', kwargs[k])
                item_data.append((self.BE_PORT_IDX, data))
            elif k == 'use_num':
                data = struct.pack('i', kwargs[k])
                item_data.append((self.USE_NUM_IDX, data))
            elif k == 'update_time':
                pass
            elif k == 'startup_msg_raw':
                data = kwargs[k]
                if len(data) > 80:
                    raise RuntimeError('len of startup_msg_raw should not be greater than 80:(%s)' % (data, ))
                item_data.append((self.STARTUP_MSG_RAW_IDX, data))
            else:
                raise RuntimeError('unknown parameter %s' % (k, ))
        if not item_data:
            return 0
        # ���Ǹ���update_time����
        x = datetime.datetime.now().timestamp()
        data = struct.pack('f', x)
        item_data.append((self.UPDATE_TIME_IDX, data))
        return super().put(item_ptr, item_data, pf, timeout)

# main
if __name__ == '__main__':
    pass

