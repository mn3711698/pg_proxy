
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
        'idle_timeout' : 60*60*24     ��worker����ʱ�䳬����ֵʱ����worker��
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
��worker��ȱʡ���в�ѯ���ַ�������worker�������ѯ���Ŀ�ͷ��ע���а���s(����/\*s\*/)�����Ҵ��ڴӿ�worker�Ļ���ַ����ӿ�worker��

* pgstmtpool.pyʹ���߳���ʵ�֣�����python��GIL���ƣ�����ֻ��ʹ��һ��CPU������worker��Ŀ���ܻ������ơ������������pgstmtpool.py��������
һ����enable_ha��ΪTrue(��Ϊ�����ӳ�)����������ΪFalse(��Ϊ�����ӳ�)��Ȼ��ǰ���һ��haproxy�������ӳ����л���ɺ���л�������������ӳء�
�����������������ӳغ�2�������ӳ�:

        .) python pgstmtpool.py
        .) python pgstmtpool.py mode=slaver listen=:7778 mpool=127.0.0.1:7777
        .) python pgstmtpool.py mode=slaver listen=:7779 mpool=127.0.0.1:7777

��ѯ����
========
* ������select��俪ͷ��ע�������û��棬��ʽΪ/\*c:n p:n t:t1,t2,...,tn\*/������cָ����������޵�λ���룬tָ�������б���Щ��ͻ�����أ�
���ûָ��c��ָ����t����ô����ձ���ص����л��档���磺/\*c:60 t:t1\*/select count(*) from t1�Ỻ��60�룬����/\*t:t1\*/delete from t1 
where id=10����ջ��档����ֻ��ִ�гɹ���SELECT��Ч��

* p[:n]���ڷ�ҳ���棬ָ���ܹ���ȡ���ټ�¼�����n<=0���߲�ָ�����ȡ���м�¼��sql��������offset <m> limit <n>��β��
��offset��������ļ�¼��ʱ��Ӻ�˶�ȡ��ֻ�е�ָ��cʱp����Ч�����磺/\*c:60 p:1000 t:t1\*/select * from t1 order by id offset 0 limit 10��
�Ỻ��1000����¼������/\*c:60 p:1000 t:t1\*/select * from t1 order by id offset 10 limit 10��ȡ�ڶ�ҳ��ʱ��ͻ�ӻ����ȡ��

* ��ǰ���л��涼�Ǳ������ڴ��еģ�����ע�ⲻҪ����̫���ѯ�����

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
        .) cache                ��ʾSELECT����
        .) fe [list]            �г�����ǰ������
        .) fe count             ��ʾǰ��������
        .) pool [list]          �г�����pool
        .) pool show            �г�ָ��pool�е�worker�����pool id�ö��ŷָ���ûָ��pool id���г�����pool��worker��
                                lastputtime�����һ����Ϣ���ַ���worker��ʱ�䣬lastinfo��worker�Ѿ���������һ����Ϣ������Ϣ��
                                ��������Ϣ���ķַ�ʱ�䣬�����Ϣ�����ѵ�ʱ��(��λ����)���Լ���������Ϣ�����ѵ�ʱ��(��λ����)��
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
          ִ��copy...to stdout��䣬�������outf��������ô��ÿһ�����ݶ������outf�����outf=None����ô
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
        
* �첽��Ϣ���첽��Ϣ��3�֣�ParameterStatus��NoticeResponse��NotificationResponse��

        .) ��ִ�в�ѯ�󣬱������parameter_status_am/notice_am/notification_am�������Ӧ���첽��Ϣ�����ߵ���clear_async_msgs
           ����첽��Ϣ�������첽��Ϣ��Խ��Խ�ࡣ
        .) ����Ҳ���Ե���read_async_msgs(timeout=0)����ȡ�첽��Ϣ���䷵��ֵ��ʾ��ȡ�����첽��Ϣ����������timeout�ǵȴ�ʱ�䣬
           ���ΪNone����С��0��һֱ�ȴ�ֱ������ϢΪֹ������read_async_msgs֮����Ҫ����parameter_status_am/notice_am/notification_am
           �������Ӧ���첽��Ϣ��

