
pg_proxy.py [conf_file]
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

* pg_proxy�����û���������ת����������ߴӿ⣬�û�����'_r'��β�����Ӷ�ת�����ӿ⣬��roundrobin��ʽ��ѡ��ӿ⡣

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
