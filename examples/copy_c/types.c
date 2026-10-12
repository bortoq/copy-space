void copy(unsigned char *destination, unsigned char *source, int n)
{
    while (n--)
        *destination++ = *source++;
}

int main(void)
{
    unsigned int source = 0x01020304, destination = 0;
    copy((unsigned char *)&destination, (unsigned char *)&source, 4);
    return *(unsigned char *)&destination + sizeof(short) + sizeof(_Bool);
}
