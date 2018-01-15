
pgstmtpool.py [conf_file] ��伶�����ӳ�
========================================
* �����ļ��Ǹ�python�ļ�(ȱʡ��pgstmtpool.conf.py)��all�����ֵ�������ò���������admin_cnn��master�Ǳ���ָ���Ĳ������������������

        'listen' : (host, port)       ָ������ip��port��
        'admin_cnn' : {}              ָ�����Ӳ�������Ҫָ��host/port�����ӳ�����Ҫ��Щadmin������ʱ���øò������ӵ�����ʹӿ⡣
        'enable_ha' : False           �Ƿ�֧��HA��
        'ha_after_fail_cnt' : 10      ��������������ָ������������ʧ��ʱ���������л���
        'lo_oid' : 9999               �����д����id�������ڴӿ�������trigger�ļ���
        'trigger_file' : 'trigger'    �ӿ��recovery.conf���õĴ���promote���ļ�����
        'worker_min_cnt' : []         ����ָ������n��ǰ������ʱ��Ҫ�ĺ��worker������idx��ֵ��ʾ����idx+1��ǰ������ʱ��Ҫ��worker����
        'worker_per_fe_cnt' : 10      ��ǰ��������worker_min_cnt�Ĵ�Сʱ��ָ��ÿ���ٸ�ǰ��������Ҫһ��������ӡ�
        'master' : (host, port)       �����ַ��
        'slaver' : [(),...]           �ӿ��ַ�б�
        'conn_params' : [{},...]      ���Ӳ����б�(���ܰ���host/port)����ǰ�˲���������һ��ƥ���ʱ��Ż������ӿ�worker��
* ��pg_hba.conf�в�Ҫ�����ӳص�host/ip���ó�trust����Ϊ��ǰ�˵�һ������ʱ�������ݿ��auth�ģ���ʱ���ݿ�˿����������ӳص�host/ip��
admin_cnn�����е��û���Ҫ�ǳ����û���admin_cnn/conn_params�г��˰���startup_msg��Ϣ�еĲ����⣬���ܻ���Ҫpassword(�������trust auth)��

* ǰ�������ӵ�ʱ������ȷ���һ��startup_msg��Ϣ������Ϣ����database/user�Լ��������ݿ����������client_encoding/application_name��
��֧��SSL���Ӻ͸������ӡ�ÿ����˶���һ��pool��pool����worker��worker��startup_msg���飬����ǰ�˵Ĳ�ѯ�����startup_msg�ַ�����Ӧ
��worker��ȱʡ���в�ѯ���ַ�������worker�������ѯ���Ŀ�ͷ��/\*s\*/���Ҵ��ڴӿ�worker�Ļ���ַ����ӿ�worker��

* pgstmtpool.pyʹ���߳���ʵ�֣�����python��GIL���ƣ�����ֻ��ʹ��һ��CPU������worker��Ŀ���ܻ������ơ������������pgstmtpool.py������
ֻ��һ����enable_ha��ΪTrue(��Ϊ�����ӳ�)����������ΪFalse(��Ϊ�����ӳ�)��Ȼ��ǰ���һ��haproxy���������ַ��������������л���ʱ��
�����ӳ�ֻ�ܴ���ֻ����ѯ��TODO:�����汾�������������ӳ�֮��ͨ�ţ������ӳ����л���ɺ���л�������������ӳء�����ʵ�ֿ���������
�����ӳ����ӵ������ӳص�α���ݿ�pseudo��Ȼ��ִ������pool changemaster pool_id��

HA�����л�
==========
* ��������������ha_after_fail_cnt������ʧ�ܲ���enable_haΪTrue����Ὺʼ�л��������л��������£�

        1) �����дӿ���ѡһ�����յ�wal��־���µĴӿ⡣
        2) ��ѡ���Ĵӿ�����Ϊ���⡣
        3) �޸������ӿ��recovery.conf�����ļ���
        4) ���µ������ϴ����ӿ��õ��ĸ���slot��
        5) �����ӿ�ʹ���޸���Ч��
* ǰ���3/4/5����Ҫ�õ�switchfunc.sql�еĺ�������Щ��������pl/python3u��д�ġ����ֻ��һ���ӿ⣬��ô����Ҫ��Щ������
Ŀǰswitchfunc.sql�еĺ�����2�����ƣ�postgresql�İ�װĿ¼��dataĿ¼���ܰ����ո��Լ�primary_conninfo�е���ֵ���ܰ����ո�

α���ݿ�pseudo
==============
* ������psql���ӵ����ݿ�pseudo�鿴���ӳصĸ�����Ϣ�������ݿ��е��û���/���룬��������pg_hba.conf������pseudo��auth������

* ���ӵ�pseudo��ֻ��ִ��֧�ֵ��������������Щ���

        .) cmd                  �г���������
        .) shutdown             shutdown���ӳ�
        .) fe [list]            �г�����ǰ������
        .) pool [list]          �г�����pool
        .) pool show            �г�ָ��pool�е�worker�����pool id�ö��ŷָ���ûָ��pool id���г�����pool��worker��
        .) pool add             ����һ��pool��������host:port��ֻ�����Ӵӿ�pool��
        .) pool remove          ɾ��һ��pool��������pool id��ֻ��ɾ���ӿ�pool��
        .) pool remove_worker   ɾ��һ��worker��������pool id��worker id������ɾ��������ߴӿ�pool�е�worker��
        .) pool new_worker      ����һ��worker��������pool id�����Ӳ�����
* ��Ҫ����û�ͬʱ���ӵ�pseudoִ���޸Ĳ�����


<����>pg_proxy.py [conf_file]
=======================
* �����ļ�conf_file�Ǹ�python�ļ���������һ��dict����pg_proxy_conf�����ֵ����������Щ�

        'listen' : (host, port)                               ָ��������ip�Ͷ˿ڡ�
        'master' : (host, port)                               ָ�������ַ��
        'conninfo' : {'name':value, ...}                      ָ���������ӵ�master��promote���û���/���ݿ�/����ȣ������ǳ����û�������ָ����name�У�user/pw/db/conn_retry_num/conn_retry_interval/query_interval/lo_oid��user����ָ����
        'promote' : (host, port)                              ָ����������Ϊ����Ĵӿ�ĵ�ַ��
        'slaver_list' : [(host, port), ...]                   ָ������ֻ�����ӵĴӿ��б�
        'idle_cnn_timeout' : 300                              ָ���������ӵ�lifetime����λ���롣
        'active_cnn_timeout' : 300                            ָ������ӿ���ʱ�����ƣ��������ʱ�䳬ʱ����ô�ͶϿ�fe�����ӡ����Ϊ0�ǾͲ����ƿ���ʱ�䡣(Ŀǰ��֧����չ��ѯЭ��)
        'recv_sz_per_poll' : 4                                ÿ��pollһ�������������ն������ݣ���λ��K��
        'disable_conds_list' : [[(name, value), ...], ...]    ��active_cnn_timeout>0�������øò���ָ�������ƿ���ʱ������ӡ�����ָ����name��user/database�Լ��������Գ�����startup��Ϣ���е�������
        'pg_proxy_pw' : 'pg2pg'                               ָ�����ӵ�α���ݿ�pg_proxy��ʱ����Ҫ�����롣
        'log' : {'name' : value, ...}                         ָ��logging��ص����ã�����ָ�������У�filename, level��level������Ϊlogging.DEBUG/INFO/WARNING/ERROR����ָ��filename����stderr�����
* ע��master/promote/slaver_list��֧��unix domain socket��listenҲ��֧��unix domain socket��

* pg_proxy�����û���������ת����������ߴӿ⣬�û����������'@ro'�����Ӷ�ת�����ӿ⣬��roundrobin��ʽ��ѡ��ӿ⡣

* ������down�������ָ����promote���ã���ô�ͻ��������Ϊ���⡣���ָ����promote����ôslaver_list�е�
�ӿ�������ӵ�promote����ӿ⣬������ֱ�����ӵ�master�������������б��봴��һ��OIDΪ9999������Ϊ�յĴ����
������OID������lo_oid�����ã�ȱʡֵΪ9999���ô����������promote������trigger�ļ���
����ӿ��ϵ�recovery.conf�е�trigger_file��Ҫ��Ϊ'trigger_file'��

* pg_proxy.pyֻ֧��postgres version 3Э�飬��֧��SSL���ӣ���֤��������ֻ֧��trust/password/md5��������֤����û�в��ԡ�
������pg_hba.conf��ʱ����Ҫע�����ADDRESS���������pg_proxy.py���ڵķ�������IP��ַ��
������ò�Ҫ���ó�trust����������֪���û���/���ݿ�����˭�����Ե�¼���ݿ⡣

* pg_proxy.py��Ҫpython 3.3�����ϰ汾����֧��windows��ֻ֧��session��������ӳأ���֧������/��伶������ӳء�
��֧�ָ������ӣ��޸ļ��д������֧�֣������������Ӳ���֧�ֳع��ܣ�Ҳ����˵�����ƿͻ��˶Ͽ����Ӻ󣬵�be�˵�����ҲӦ�öϿ���

α���ݿ�
========
������psql���ӵ�α���ݿ�pg_proxy�鿴��ǰ״̬��ȱʡ������pg2pg���û������⡣����4����: connection/process/server/startupmsg��
ֻ֧�ֵ����select��ѯ������process/server��֧�ֲ�ѯ��������ѡ��
- connection : ����ÿ��fe/be���ӶԵ���Ϣ����������ӺͿ������ӡ�
- process    : ����ÿ�����ӽ��̵�������Ϣ��
- server     : ����ÿ�����ݿ�server��������Ϣ��
- startupmsg : ����ÿ�����ӵ�startup��Ϣ�����Լ������Ƿ���С�

pg_proxy.py�Ľṹ
=================
* ����������ʱ����AF_UNIX socket(�����������̺��ӽ���֮��ͨ��)�Լ�AF_INET socket(��������pg�ͻ��˵�����)��
* Ȼ�󴴽�n�����ӳؽ���(P)���Լ�һ����������(W)���ڴ�������������(M)���������󣬱��緢��CancelRequest�������л�����ȵȡ�
* M��P֮��ͨ��UDS(unix domain socket)ͨ�ţ�����֮�����Ϣ�У�
    * M->P ���pending_fe_connection�Ѿ����յ�StartupMessage����ôM�������ļ��������Լ�StartupMessage���͸�P��P��ѡ������ǣ�P�еĿ��е�BE����
      ��StartupMessage��pending_fe_connectionƥ�䣻�������P��û��ƥ������ӣ���ô��ѡ��������ٵ�P���ӿ��ѡ������roundrobin��ʽ��
    * P->M �����ӽ������߶Ͽ���ʱ��P���������Ϣ����M��
* M��W֮����Ҫ��M��W���͹���������Ϣ����ǰ�Ĺ���������Ϣ�У�����CancelRequest�������л������
