/* Guest newlib operations. No operation here is executed by the host. */
#include "copy_space.h"
#include "files.h"
#ifdef CS_GCC_FRAMED_OUTPUT
#include "response.h"
extern int cs_gcc_finish(int status);
#endif
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <unistd.h>

#ifndef CS_GCC_HEAP_BYTES
#define CS_GCC_HEAP_BYTES (256u * 1024u)
#endif
#ifndef CS_GCC_MEMORY_BYTES
#define CS_GCC_MEMORY_BYTES (64u * 1024u * 1024u)
#endif

static union {
    long double alignment;
    unsigned char bytes[CS_GCC_HEAP_BYTES];
} heap;
static size_t heap_used;
static unsigned streams = 7;

void *_sbrk(ptrdiff_t increment)
{
    size_t next;
    if (increment >= 0) {
        if ((size_t)increment > sizeof(heap.bytes) - heap_used) {
            errno = ENOMEM;
            return (void *)-1;
        }
        next = heap_used + (size_t)increment;
    } else {
        /* Avoid negating PTRDIFF_MIN. */
        size_t decrease = (size_t)(-(increment + 1)) + 1;
        if (decrease > heap_used) {
            errno = ENOMEM;
            return (void *)-1;
        }
        next = heap_used - decrease;
    }
    void *previous = heap.bytes + heap_used;
    heap_used = next;
    return previous;
}

static int valid_stream(int fd)
{
    return fd >= 0 && fd <= 2 && (streams & (1u << fd));
}

_READ_WRITE_RETURN_TYPE _read(int fd, void *buffer, size_t count)
{
    if (fd>=3) return cs_gcc_fs_read(fd,buffer,count);
    if (fd != 0 || !valid_stream(fd)) { errno = EBADF; return -1; }
    if (count > INT_MAX) { errno = EINVAL; return -1; }
    int result = cs_read(buffer, (unsigned)count);
    if (result < 0) errno = EIO;
    return result;
}

_READ_WRITE_RETURN_TYPE _write(int fd, const void *buffer, size_t count)
{
    if (fd>=3) return cs_gcc_fs_write(fd,buffer,count);
    if ((fd != 1 && fd != 2) || !valid_stream(fd)) { errno = EBADF; return -1; }
    if (count > INT_MAX) { errno = EINVAL; return -1; }
#ifdef CS_GCC_FRAMED_OUTPUT
    return cs_gcc_capture_write(fd,buffer,count);
#else
    int result = cs_write(buffer, (unsigned)count);
    if (result < 0) errno = EIO;
    return result;
#endif
}

int _close(int fd)
{
    if (fd>=3) return cs_gcc_fs_close(fd);
    if (!valid_stream(fd)) { errno = EBADF; return -1; }
    streams &= ~(1u << fd);
    return 0;
}

int _fstat(int fd, struct stat *result)
{
    if (!result) { errno = EFAULT; return -1; }
    if (fd>=3) {
        unsigned size,inode;
        if (cs_gcc_fs_fstat(fd,&size,&inode)) return -1;
        memset(result,0,sizeof(*result));
        result->st_mode=S_IFREG|0666; result->st_nlink=1;
        result->st_size=size; result->st_dev=1; result->st_ino=inode;
        return 0;
    }
    if (!valid_stream(fd)) { errno = EBADF; return -1; }
    memset(result, 0, sizeof(*result));
    result->st_mode = S_IFCHR;
    result->st_nlink = 1;
    return 0;
}

int _isatty(int fd)
{
    errno = valid_stream(fd) ? ENOTTY : EBADF;
    return 0;
}

off_t _lseek(int fd, off_t offset, int origin)
{
    if (fd>=3) return cs_gcc_fs_seek(fd,offset,origin);
    (void)offset; (void)origin;
    errno = valid_stream(fd) ? ESPIPE : EBADF;
    return (off_t)-1;
}

int _open(const char *path, int flags, int mode)
{
    (void)mode;
    int allowed=O_ACCMODE|O_CREAT|O_EXCL|O_TRUNC|O_APPEND;
#ifdef O_CLOEXEC
    allowed|=O_CLOEXEC;
#endif
#ifdef O_NOCTTY
    allowed|=O_NOCTTY;
#endif
#ifdef O_BINARY
    allowed|=O_BINARY;
#endif
    if ((flags & ~allowed) || (flags & O_ACCMODE)==O_ACCMODE) { errno=EINVAL; return -1; }
    unsigned mapped=(flags & O_ACCMODE)==O_RDONLY ? CS_FS_READ :
                    (flags & O_ACCMODE)==O_WRONLY ? CS_FS_WRITE : CS_FS_READ|CS_FS_WRITE;
    if (flags & O_CREAT) mapped|=CS_FS_CREATE;
    if (flags & O_EXCL) mapped|=CS_FS_EXCL;
    if (flags & O_TRUNC) mapped|=CS_FS_TRUNC;
    if (flags & O_APPEND) mapped|=CS_FS_APPEND;
    return cs_gcc_fs_open(path,mapped);
}

int _unlink(const char *path) { return cs_gcc_fs_unlink(path); }
int _stat(const char *path, struct stat *result)
{
    if (!result) { errno=EFAULT; return -1; }
    unsigned size,inode; int directory;
    if (cs_gcc_fs_stat(path,&size,&directory,&inode)) return -1;
    memset(result,0,sizeof(*result)); result->st_mode=(directory ? S_IFDIR|0555 : S_IFREG|0666);
    result->st_nlink=1; result->st_size=size; result->st_dev=1; result->st_ino=inode;
    return 0;
}

char *getcwd(char *buffer, size_t size)
{
    int allocated=0;
    if (!buffer) {
        if (!size) size=2;
        buffer=malloc(size); if (!buffer) { errno=ENOMEM; return NULL; }
        allocated=1;
    }
    if (size<2) { if (allocated) free(buffer); errno=ERANGE; return NULL; }
    buffer[0]='/'; buffer[1]=0; return buffer;
}

pid_t _getpid(void) { return 1; }
int _kill(pid_t pid, int signal)
{
    (void)pid; (void)signal; errno = ENOSYS; return -1;
}

void _exit(int code)
{
#ifdef CS_GCC_FRAMED_OUTPUT
    code=cs_gcc_finish(code);
#endif
    cs_exit(code);
}

int access(const char *path, int mode)
{
    if (mode & ~(R_OK|W_OK|X_OK)) { errno=EINVAL; return -1; }
    return cs_gcc_fs_access(path,mode & W_OK,mode & X_OK);
}

long sysconf(int name)
{
    switch (name) {
    case _SC_PAGESIZE: return 4096;
    case _SC_PHYS_PAGES: return CS_GCC_MEMORY_BYTES/4096;
    case _SC_AVPHYS_PAGES: return (sizeof(heap.bytes)-heap_used)/4096;
    case _SC_OPEN_MAX: return 64;
    case _SC_CLK_TCK: return 100;
#ifdef _SC_NPROCESSORS_ONLN
    case _SC_NPROCESSORS_ONLN: return 1;
#endif
#ifdef _SC_NPROCESSORS_CONF
    case _SC_NPROCESSORS_CONF: return 1;
#endif
    default: errno=EINVAL; return -1;
    }
}

int _gettimeofday(struct timeval *value, void *zone)
{
    static uint64_t logical_microseconds;
    if (!value) { errno=EFAULT; return -1; }
    if (zone) { errno=EINVAL; return -1; }
    if (logical_microseconds==UINT64_MAX) { errno=EOVERFLOW; return -1; }
    value->tv_sec=(time_t)(logical_microseconds/1000000);
    value->tv_usec=(suseconds_t)(logical_microseconds%1000000);
    ++logical_microseconds; return 0;
}
