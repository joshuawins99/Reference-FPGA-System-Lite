#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define WriteIO(addr,val)       (*(volatile unsigned char*) (addr) = (val))
#define WriteIO32(addr,val)     (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)            (*(volatile unsigned char*) (addr))
#define ReadIO32(addr)          (*(volatile uint32_t*) (addr))

void Print (unsigned char, char *);
char* ReadVersion ();
char* readFPGA (char *);
void writeFPGA (char *, char *);
char* executeCommandsSerial(char *);
void ReadUART();

