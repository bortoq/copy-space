typedef __SIZE_TYPE__ size_t;
typedef unsigned char byte;
#define NOIPA __attribute__((noinline,noipa))
#define BUFFER 512
extern void *memcpy(void *,const void *,size_t);
extern void *memmove(void *,const void *,size_t);
extern void *memset(void *,int,size_t);
extern int memcmp(const void *,const void *,size_t);
static byte a[BUFFER],b[BUFFER];
static const unsigned lengths[]={0,1,2,3,7,8,15,16,17,31,32,63,64,65,127,128,255,256,257};
#define LENGTHS (sizeof(lengths)/sizeof(lengths[0]))
static byte pattern(unsigned i,unsigned salt) { return (byte)(i^(i>>5)^salt); }
NOIPA static void seed(void *buffer,unsigned size,unsigned bias,unsigned salt)
{
    volatile byte *p=buffer;
    for(unsigned i=0;i<size;++i)p[i]=pattern(i-bias,salt);
}
NOIPA static unsigned check_pattern(const void *buffer,unsigned size,unsigned bias,unsigned salt)
{
    const volatile byte *p=buffer;
    for(unsigned i=0;i<size;++i)if(p[i]!=pattern(i-bias,salt))return 0;
    return 1;
}
NOIPA static unsigned check_copy(const void *buffer,unsigned dest,unsigned src,unsigned n,
                                unsigned outside,unsigned inside,unsigned fill)
{
    const volatile byte *p=buffer;
    for(unsigned i=0;i<BUFFER;++i){
        byte expected=pattern(i,outside);
        if(i>=dest && i-dest<n)expected=fill?(byte)inside:pattern(src+i-dest,inside);
        if(p[i]!=expected)return 0;
    }
    return 1;
}
NOIPA static void *copy_bytes(void *d,const void *s,size_t n) { return memcpy(d,s,n); }
NOIPA static void *move_bytes(void *d,const void *s,size_t n) { return memmove(d,s,n); }
NOIPA static void *fill_bytes(void *d,int v,size_t n) { return memset(d,v,n); }
NOIPA static int compare_bytes(const void *x,const void *y,size_t n) { return memcmp(x,y,n); }
NOIPA static void *builtin_copy(void *d,const void *s,size_t n) { return __builtin_memcpy(d,s,n); }

unsigned copy_checks(void)
{
    const unsigned offsets[3][2]={{0,0},{1,2},{3,1}};unsigned passed=0;
    for(unsigned k=0;k<LENGTHS;++k)for(unsigned j=0;j<3;++j){
        unsigned d=offsets[j][0],s=offsets[j][1],n=lengths[k];
        seed(a,BUFFER,0,37);seed(b,BUFFER,0,209);
        void *ret=copy_bytes(a+d,b+s,n);
        passed+=(ret==a+d && check_copy(a,d,s,n,37,209,0) && check_pattern(b,BUFFER,0,209));
    }
    return passed;
}
unsigned move_checks(void)
{
    const unsigned offsets[7][2]={{0,0},{1,0},{0,1},{3,7},{7,3},{129,0},{0,129}};
    unsigned passed=0;
    for(unsigned k=0;k<LENGTHS;++k)for(unsigned j=0;j<7;++j){
        unsigned d=offsets[j][0],s=offsets[j][1],n=lengths[k];seed(a,BUFFER,0,37);
        void *ret=move_bytes(a+d,a+s,n);
        passed+=(ret==a+d && check_copy(a,d,s,n,37,37,0));
    }
    return passed;
}
unsigned fill_checks(void)
{
    const int values[]={0,1,127,128,255,0x12345,-1};unsigned passed=0;
    for(unsigned k=0;k<LENGTHS;++k)for(unsigned j=0;j<7;++j){
        unsigned d=k%3,n=lengths[k];seed(a,BUFFER,0,37);
        void *ret=fill_bytes(a+d,values[j],n);
        passed+=(ret==a+d && check_copy(a,d,0,n,37,(unsigned)values[j],1));
    }
    return passed;
}
unsigned compare_checks(void)
{
    unsigned passed=0;
    for(unsigned k=0;k<LENGTHS;++k)for(unsigned offset=0;offset<3;++offset){
        unsigned x=offset,y=3-offset,n=lengths[k];
        seed(a,BUFFER,x,37);seed(b,BUFFER,y,37);
        passed+=compare_bytes(a+x,b+y,n)==0;
        if(n)for(unsigned j=0;j<3;++j){
            unsigned pos=j==0?0:j==1?n/2:n-1;byte old=b[y+pos];b[y+pos]=(byte)(old^128);
            int expected=old<b[y+pos]?-1:1;
            int v=compare_bytes(a+x,b+y,n);passed+=((v>0)-(v<0))==expected;
            v=compare_bytes(b+y,a+x,n);passed+=((v>0)-(v<0))==-expected;
            b[y+pos]=old;
        }
        if(!check_pattern(a,BUFFER,x,37) || !check_pattern(b,BUFFER,y,37))return 0;
    }
    return passed;
}
struct block { byte data[256]; unsigned guard; };
_Static_assert(sizeof(struct block)==260,"test block must have no padding");
NOIPA static void assign(struct block *d,const struct block *s) { *d=*s; }
unsigned aggregate_checks(void)
{
    struct block x,y;unsigned passed=0;
    for(unsigned i=0;i<4;++i){
        seed(&x,sizeof x,0,37);seed(&y,sizeof y,0,100+i);
        assign(&x,&y);
        passed+=check_pattern(&x,sizeof x,0,100+i) && check_pattern(&y,sizeof y,0,100+i);
    }
    return passed;
}
unsigned builtin_checks(void)
{
    unsigned passed=0;
    for(unsigned k=0;k<LENGTHS;++k){
        unsigned n=lengths[k];seed(a,BUFFER,0,37);seed(b,BUFFER,0,209);
        void *ret=builtin_copy(a+3,b+5,n);
        passed+=ret==a+3 && check_copy(a,3,5,n,37,209,0) && check_pattern(b,BUFFER,0,209);
    }
    return passed;
}
