#include "include/dirent.h"
#include "files.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
struct cs_gcc_directory { unsigned cursor; struct dirent entry; char *path; };

DIR *opendir(const char *path)
{
    if (!path) { errno=EINVAL; return NULL; }
    DIR *result=calloc(1,sizeof(*result));
    if (!result) { errno=ENOMEM; return NULL; }
    result->path=malloc(strlen(path)+1);
    if (!result->path) { free(result); errno=ENOMEM; return NULL; }
    strcpy(result->path,path);
    if (cs_gcc_fs_directory_open(path)) { free(result->path); free(result); return NULL; }
    return result;
}

struct dirent *readdir(DIR *directory)
{
    if (!directory) { errno=EINVAL; return NULL; }
    int is_directory;
    int result=cs_gcc_fs_directory_next(directory->path,&directory->cursor,
        directory->entry.d_name,sizeof(directory->entry.d_name),&directory->entry.d_ino,&is_directory);
    if (result<=0) return NULL;
    directory->entry.d_type=is_directory ? DT_DIR : DT_REG;
    return &directory->entry;
}

int closedir(DIR *directory)
{
    if (!directory) { errno=EINVAL; return -1; }
    cs_gcc_fs_directory_close(); free(directory->path); free(directory); return 0;
}
void rewinddir(DIR *directory) { if (directory) directory->cursor=0; else errno=EINVAL; }
long telldir(DIR *directory) { if (directory) return directory->cursor; errno=EINVAL; return -1; }
void seekdir(DIR *directory, long position)
{
    if (!directory || position<0 || position>1024) { errno=EINVAL; return; }
    directory->cursor=(unsigned)position;
}
