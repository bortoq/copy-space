typedef unsigned (*callback)(unsigned);
typedef void (*action)(unsigned);
typedef unsigned (*many_callback)(unsigned,unsigned,unsigned,unsigned,
                                 unsigned,unsigned,unsigned,unsigned);
struct callback_result { unsigned a,b,c,d; };
typedef struct callback_result (*result_callback)(unsigned);
unsigned invoke(callback,unsigned);
unsigned compare_callbacks(callback,callback);
void notify(action,unsigned);
unsigned invoke_many(many_callback,unsigned,unsigned,unsigned,unsigned,
                     unsigned,unsigned,unsigned,unsigned);
struct callback_result collect(result_callback,unsigned);
