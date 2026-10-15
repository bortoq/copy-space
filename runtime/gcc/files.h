#ifndef CS_GCC_FILES_H
#define CS_GCC_FILES_H
#include <stddef.h>
#include <stdint.h>
enum { CS_FS_READ=1, CS_FS_WRITE=2, CS_FS_CREATE=4, CS_FS_TRUNC=8,
       CS_FS_APPEND=16, CS_FS_EXCL=32 };
int cs_gcc_fs_mount(unsigned char *blob, unsigned size);
int cs_gcc_fs_open(const char *path, unsigned flags);
int cs_gcc_fs_close(int fd);
int cs_gcc_fs_read(int fd, void *data, size_t size);
int cs_gcc_fs_write(int fd, const void *data, size_t size);
int cs_gcc_fs_seek(int fd, int64_t offset, int origin);
int cs_gcc_fs_stat(const char *path, unsigned *size, int *directory, unsigned *inode);
int cs_gcc_fs_fstat(int fd, unsigned *size, unsigned *inode);
int cs_gcc_fs_unlink(const char *path);
int cs_gcc_fs_output(const char *path, const unsigned char **data, unsigned *size);
/* Replace a closed writable file without copying. On success the filesystem
   owns the malloc-allocated buffer; on failure ownership stays with the caller. */
int cs_gcc_fs_replace_owned(const char *path, unsigned char *data, unsigned size);
int cs_gcc_fs_directory_open(const char *path);
int cs_gcc_fs_access(const char *path, int write, int execute);
void cs_gcc_fs_directory_close(void);
int cs_gcc_fs_directory_next(const char *path, unsigned *cursor, char *name,
                            unsigned capacity, unsigned *inode, int *directory);
#endif
