#include "pf_all.h"

static int interpret(char *line)
{
    ThrowCode result = pfInterpretText(line);
    if(result == THROW_BYE) return 1;
    if(result)
    {
        pfReportThrow(result);
        return -1;
    }
    return 0;
}

int main(void)
{
    char line[TIB_SIZE];
    unsigned int length = 0;
    ExecToken entry = 0;
    int code = 0, done = 0;
    pfSetQuiet(1);
    if(pfInitialize(NULL, 0, &entry)) return 3;
#ifdef COPY_SPACE_C_COMPILER
    /* The C precedence parser has more calls per nesting level than the
     * interactive Forth interpreter. Keep the ordinary task unchanged. */
    PForthTask initial_task = pfGetCurrentTask();
    PForthTask compiler_task = pfCreateTask(512, 2048);
    if(!compiler_task) { pfTerminate(); return 3; }
    pfSetCurrentTask(compiler_task);
    pfDeleteTask(initial_task);
#endif
    while(!done)
    {
        unsigned char c;
        int count = cs_read(&c, 1);
        if(count < 0) { code = 1; break; }
        if(count == 0 || c == '\n' || c == '\r')
        {
            int result = 0;
            line[length] = 0;
            if(length) result = interpret(line);
            length = 0;
            if(result < 0) { code = 2; break; }
            done = result > 0 || count == 0;
        }
        else
        {
            if(length == sizeof line-1)
            {
                pfMessage("pForth: input line too long\n");
                code = 2;
                break;
            }
            line[length++] = (char)c;
        }
    }
    if(!code && gVarState)
    {
        pfMessage("pForth: unfinished definition\n");
        code = 2;
    }
    if(!code) code = (int)gVarByeCode;
    pfTerminate();
    return code;
}
