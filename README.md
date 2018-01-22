
pgstmtpool.py [args] ��伶�����ӳ�
========================================
* �����в���������[mode=master|slaver] [listen=host:port] [mpool=host:port] [conf=pgstmtpool.conf.py]

        mode=master|slaver            ָ�������ӳ��������ӳػ��Ǵ����ӳء����û��ָ����ô���������ļ��е�enable_ha��ȷ����
                                      enable_ha=True�������ӳط����Ǵ����ӳء����ָ����mode�����в�������ôenalbe_ha��mode
                                      ��ȷ����mode=master��ʾenable_haΪTrue������ΪFalse��
        listen=host:port              ָ�������ӳصļ���ip��ַ�Ͷ˿ڡ����û��ָ�����������ļ��е�listen������
        mpool=host:port               ָ�������ӳص�ip��ַ�Ͷ˿ڡ�ֻ�Դ����ӳ���Ч�����ָ���ˣ���ô��ѱ������ӳ�ע�ᵽ�����ӳء�
        conf=pgstmtpool.conf.py       ָ�������ļ���

* �����ļ��Ǹ�python�ļ�(ȱʡ��pgstmtpool.conf.py)��all�����ֵ�������ò���������admin_cnn��master�Ǳ���ָ���Ĳ������������������

        'listen' : (host, port)       ָ������ip��port��
        'pseudo_cnn' : {}             �������ӳ��໥ͨ��ʱ�ø����Ӳ���ȥ���ӵ�α���ݿ⣬��Ҫ����host/port/database�����ûָ������admin_cnn��
        'admin_cnn' : {}              ָ�����Ӳ�������Ҫָ��host/port�����ӳ�����Ҫ��Щadmin������ʱ���øò������ӵ�����ʹӿ⡣
                                      ��Ҫָ�����룬���auth������md5�����ָ��md5������룬����ָ���������롣
        'enable_ha' : False           �Ƿ�֧��HA��
        'ha_after_fail_cnt' : 10      ��������������ָ������������ʧ��ʱ���������л���
        'lo_oid' : 9999               �����д����id�������ڴӿ�������trigger�ļ���
        'trigger_file' : 'trigger'    �ӿ��recovery.conf���õĴ���promote���ļ�����
        'worker_min_cnt' : []         ����ָ������n��ǰ������ʱ��Ҫ�ĺ��worker������idx��ֵ��ʾ����idx+1��ǰ������ʱ��Ҫ��worker����
        'worker_per_fe_cnt' : 10      ��ǰ��������worker_min_cnt�Ĵ�Сʱ��ָ��ÿ���ٸ�ǰ��������Ҫһ��������ӡ�
        'master' : (host, port)       �����ַ��
        'slaver' : [(),...]           �ӿ��ַ�б�ͬһ���ӿ���԰�����Σ�Ҳ���԰������⡣
        'user_pwds' : {}              �����û����룬�ӿ�worker����Щ�������ӵ��ӿ⡣����û���auth������md5����Ҫָ����
                                      ���auth������password/scram-sha-256�����ָ�����룬�����trust��ָ���մ���
                                      ���auth����md5����û��ָ�����룬��ô���������ӿ�worker��

* ��pg_hba.conf�в�Ҫ�����ӳص�host/ip���ó�trust����Ϊ��˿�����host/ip�����ӳص�host/ip��������ǰ�˵ġ�
ǰ��������������µ�worker(���ڵ�ǰworker������)����ô�����ݿ�˶�ǰ�˽���auth������������ӳض�ǰ�˽���auth��
������pg_hba.conf�о��������ӳغ�ǰ�����ó�һ����

* admin_cnn�����е��û���Ҫ�ǳ����û�����Ҫָ�����룬�����md5 auth�����������md5������롣

* ǰ�˲���ʹ���������(����begin/end)�������������Ĳ�ѯ���ᱻabort�������������������һ��Query��Ϣ��һ������ִ�С�
psycopg2ȱʡ��autocommit��False�����������Զ�����begin��䣬�����autocommit��ΪTrue�ſ���ʹ�ñ����ӳء�������ö���
�����Ϊһ������ִ�У����԰ѷֺŷָ��Ķ��������Ϊһ�����ִ�С�

* ǰ�������ӵ�ʱ������ȷ���һ��startup_msg��Ϣ������Ϣ����database/user�Լ��������ݿ����������client_encoding/application_name��
��֧��SSL���Ӻ͸������ӡ�ÿ����˶���һ��pool��pool����worker��worker��startup_msg���飬����ǰ�˵Ĳ�ѯ�����startup_msg�ַ�����Ӧ
��worker��ȱʡ���в�ѯ���ַ�������worker�������ѯ���Ŀ�ͷ��/\*s\*/���Ҵ��ڴӿ�worker�Ļ���ַ����ӿ�worker��

* pgstmtpool.pyʹ���߳���ʵ�֣�����python��GIL���ƣ�����ֻ��ʹ��һ��CPU������worker��Ŀ���ܻ������ơ������������pgstmtpool.py��������
һ����enable_ha��ΪTrue(��Ϊ�����ӳ�)����������ΪFalse(��Ϊ�����ӳ�)��Ȼ��ǰ���һ��haproxy�������ӳ����л���ɺ���л�������������ӳء�
�����������������ӳغ�2�������ӳ�:

        .) python pgstmtpool.py
        .) python pgstmtpool.py mode=slaver listen=:7778 mpool=127.0.0.1:7777
        .) python pgstmtpool.py mode=slaver listen=:7779 mpool=127.0.0.1:7777

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
        .) log_msg              �Ƿ��ӡ����Ϣ��û��ָ����������ʾ��ǰ��log_msg���ã�������Ϊָ����ֵ��
                                on/1/true/t��ʾTrue��������ʾFalse��
        .) spool                �г������ӳء�
        .) register             �ڲ�������
        .) change_master        �ڲ�������
        .) shutdown             shutdown���ӳ�
        .) fe [list]            �г�����ǰ������
        .) fe count             ��ʾǰ��������
        .) pool [list]          �г�����pool
        .) pool show            �г�ָ��pool�е�worker�����pool id�ö��ŷָ���ûָ��pool id���г�����pool��worker��
        .) pool add             ����һ��pool��������host:port��ֻ�����Ӵӿ�pool��
        .) pool remove          ɾ��һ��pool��������pool id��ֻ��ɾ���ӿ�pool��
        .) pool remove_worker   ɾ��һ��worker��������pool id��worker id������ɾ��������ߴӿ�pool�е�worker��
        .) pool new_worker      ����һ��worker��������pool id�����Ӳ�����

* ��Ҫ����û�ͬʱ���ӵ�pseudoִ���޸Ĳ�����

pgnet.pgconn
===================
* pgconn������Ϊ�ͻ��˿�ʹ�ã���������ѭpython DB-API�淶��������ִ�����׳��쳣pgfatal��pgerror��pgfatal��ʾ�����Ѿ������ã�
  ����pgfatal���쳣�����errstr�Ǵ��󴮣�errmsg�Ǻ��쳣��صĴ�����Ϣ��������pgerror��errstr�Ǵ��󴮣�errmsg�Ǵ�����Ϣ��ErrorResponse��
  ���Ե���pgconn.errmsg(pgerror_ex)��ð���������Ϣ��map��errstr��errmsg��������һ��ΪNone����������������None��
  �ӿ����£�

        pgconn(**kwargs)
          ����һ�����ӣ��ؼ��ֲ���������host/port/database/user/password/application_name/client_encoding��
          �Լ�����GUC��������֧��unix domain socket��
        query(sql)
          ִ��sql��䣬�����������÷ֺŷָ�������QueryResult������Ƕ��������ô����QueryResult�б�
          ��Ҫ�øú���ִ��copy��䣬��copyin/copyout������
        query2(sql, args_list, discard_qr=False)
          ����չ��ѯЭ��ִ��sql��䣬sql���ܰ���������䣬sql�еĲ�����$1..$n��ʾ��args_list�ǲ���ֵ�б�
          �����е����У��������sql����2����������ôargs_list��Ԫ�ر����Ǵ�СΪ2�����С�
          �������Ҫ��ѯ���(����INSERT/UPDATE/DELETE)����ô���԰�discard_qr��ΪTrue������������΢������ܡ�
          ��Ҫ�øú���ִ��copy��䣬��copyin/copyout������
        copyin(sql, data_list, batch=10)
          ִ��copy...from stdin��䣬data_list���������б�ȱʡ�������е�����\t�ָ���β��\n��
          batchָ��ÿ�η��Ͷ��ٸ���Ϣ������ÿ�����ݵĴ�С������Ӧ��ֵ��
        copyout(sql, outf)
          ִ��copy...to stdout��䣬�������outf��������ô��ÿһ�����ݶ��ص���outf�����outf=None����ô
          ����QueryResult���������б�
        trans()
          ��������context manager��
        errmsg(ex)
          ex��pgerror���󣬷��ذ���������Ϣ��map��
        quote_literal(v)
          ��̬�������������������ⲿ��������Ҫ�øú�������һ�£��Է�ֹsqlע�룬������query2ִ�С�
        quote_ident(v)
          ��̬�����������������ı�ʶ������Ҫ�øú�������һ�£��Է�ֹsqlע�롣ע���Сд���⡣

* QueryResult��rowdesc���ΪNone���ͱ�ʾִ�е���û�з��ؽ������䣬����INSERT/DELETE��

        cnn = pgnet.pgconn()
        res = cnn.query('select * from t1')
        for row in res:
            print(list(row))
        
        cnn.query2('insert into t1 values($1,$2)', ((i, i*i) for i in range(1000)))
        
        cnn.copyin('copy t1 from stdin', ('%s\t%s\n' % (i, i*i) for i in range(1000)))
        
        _, rows = cnn.copyout('copy t1 to stdout')
        for r in rows:
            print(r)
        
        with cnn.trans():
            cnn.query('insert into t1 values(1, 1)')
            ....
            cnn.query('insert into t2 values(100, 100)')
        

<����>pg_proxy.py [conf_file]
=============================
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
