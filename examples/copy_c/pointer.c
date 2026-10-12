/* The callee writes the caller's local object through its byte address. */
int increment(int *value);

int main(void)
{
    int value = 7;
    increment(&value);
    return value;
}

int increment(int *value)
{
    *value = *value + 1;
    return *value;
}
