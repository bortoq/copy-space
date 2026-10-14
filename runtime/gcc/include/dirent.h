#ifndef CS_GCC_DIRENT_H
#define CS_GCC_DIRENT_H
struct dirent { unsigned d_ino; unsigned char d_type; char d_name[4097]; };
typedef struct cs_gcc_directory DIR;
#define DT_UNKNOWN 0
#define DT_DIR 4
#define DT_REG 8
#ifdef __cplusplus
extern "C" {
#endif
DIR *opendir(const char *path);
struct dirent *readdir(DIR *directory);
int closedir(DIR *directory);
void rewinddir(DIR *directory);
long telldir(DIR *directory);
void seekdir(DIR *directory, long position);
#ifdef __cplusplus
}
#endif
#endif
