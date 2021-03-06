// 
// libmysem.so : g++ -pthread -shared -fPIC -o libmysem.so mysem.cpp -lrt
// 
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h> // for fork
#include <time.h>
#include <errno.h>
#include <string.h>
#include <semaphore.h>
#include <sys/mman.h> // for mmap

extern "C" {

int semsize()
{
    return sizeof(sem_t);
}
int seminit(char *sem, int pshared, unsigned int value)
{
    return sem_init((sem_t *)sem, pshared, value);
}
int semdestroy(char *sem)
{
    return sem_destroy((sem_t *)sem);
}
int semgetvalue(char *sem, int *sval)
{
    return sem_getvalue((sem_t *)sem, sval);
}
int sempost(char *sem)
{
    return sem_post((sem_t *)sem);
}
#define NSEC_PER_SEC (1000000000)
int semwait(char *sem, double timeout)
{
    if (timeout < 0.0)
        return sem_wait((sem_t *)sem);
    else if (timeout == 0.0)
        return sem_trywait((sem_t *)sem);
    else
    {
        struct timespec ts;
        long sec, nsec;
        int ret = clock_gettime(CLOCK_REALTIME, &ts);
        if (ret != 0)
            return ret;
        sec = (long)timeout;
        nsec = (long)((timeout - sec) * NSEC_PER_SEC);
        ts.tv_sec += sec;
        ts.tv_nsec += nsec;
        ts.tv_sec += ts.tv_nsec / NSEC_PER_SEC;
        ts.tv_nsec = ts.tv_nsec % NSEC_PER_SEC;
        return sem_timedwait((sem_t *)sem, &ts);
    }
}

} // end of extern "C"

int check_error(const char * func, int e)
{
    if (e != 0)
    {
        printf("%s fail: %s\n", func, strerror(errno));
        exit(1);
    }
    return e;
}
#ifdef MAIN
int main()
{
    char * addr = (char *)mmap(NULL, 1024, PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
    if (addr == MAP_FAILED)
    {
        printf("mmap fail: %s\n", strerror(errno));
        exit(1);
    }
    int val = 0;
    check_error("init", seminit(addr, 1, 1));
    check_error("getvalue", semgetvalue(addr, &val));
    printf("sem val:%d\n", val);
    
    check_error("wait", semwait(addr, -1));
    check_error("getvalue", semgetvalue(addr, &val));
    printf("after wait, sem val:%d\n", val);
    check_error("post", sempost(addr));
    
    return 0;
}
#endif
