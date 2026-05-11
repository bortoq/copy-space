/* space.h — Copy-Space VM
 *
 * Модель:
 *  - Единая память vm->space[] (SPACE_BYTES), адресуемая в БИТАХ.
 *  - Единственная операция "вычисления": copy(n_bits, dst_bit, src_bit).
 *  - "Процессор" — это область памяти, содержащая PROCESSOR_N слотов инструкций.
 *  - Один тик VM:
 *      (1) обслуживает MMIO (stdin/stdout/ halt) по handshake-регистрам,
 *      (2) выполняет слоты 0..PROCESSOR_N-1 в режиме fetch-execute.
 *
 * Инструкция в памяти:
 *  - имеет три поля: n, dst, src
 *  - ширина адреса (ADDR_BITS) выводится из SPACE_BYTES
 *  - N_BITS = ADDR_BITS
 *  - INSTR_BITS = 3 * ADDR_BITS (и ADDR_BITS округляется до кратности 8 => INSTR_BITS кратно 8)
 *  - кодировка битов внутри байта: bit0 = MSB (0x80), MSB-first.
 *
 * Параллельные "слои":
 *  - Если в одном слое ни один битовый индекс space не используется более одного раза
 *    (включая чтение), то слой независим и эквивалентен параллельному шагу.
 *
 * Loader 3B (слой-за-слоем):
 *  - VM не имеет встроенного "state" для переключения слоёв.
 *  - Переход к следующему слою реализуется самим копикодом:
 *      * slot0 = NOP (n=0), а в его dst-поле хранится указатель на следующий слой (бит-адрес)
 *      * предпоследний слот патчит src-поле последнего слота
 *      * последний слот копирует PROCESSOR_BITS бит следующего слоя в область процессора
 */

#ifndef COPYSPACE_H_
#define COPYSPACE_H_

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <limits.h>

#if CHAR_BIT != 8
#  error "Copy-Space VM requires CHAR_BIT==8"
#endif

/* -------------------- User-tunable knobs -------------------- */

/* По умолчанию: 512 KiB */
#ifndef VM_SPACE_BYTES
#define VM_SPACE_BYTES (512u * 1024u)
#endif

/* По умолчанию: 64 слота */
#ifndef VM_PROCESSOR_N
#define VM_PROCESSOR_N 64u
#endif

/* -------------------- Types -------------------- */

typedef uint64_t bitaddr_t;

typedef struct {
  uint64_t n;
  uint64_t dst;
  uint64_t src;
} vm_inst_t;


/* -------------------- VM error diagnostics (recorded on VM_ERR) -------------------- */

typedef enum {
  VM_E_NONE = 0,
  VM_E_SRC_BOUNDS = 1,
  VM_E_DST_BOUNDS = 2,
  VM_E_ALIGN32 = 3
} vm_err_kind_t;

typedef struct {
  vm_err_kind_t kind;
  uint64_t tick;     /* 0-based tick index */
  unsigned slot;     /* processor slot index */
  vm_inst_t ins;     /* offending instruction */
  bitaddr_t space_bits;
} vm_err_t;


typedef enum {
  VM_OK   = 0,   /* тик выполнен */
  VM_HALT = 1,   /* останов по HALT */
  VM_ERR  = -1   /* ошибка (I/O или выход за границы и т.п.) */
} vm_rc_t;

/* -------------------- VM object -------------------- */

typedef struct vm_mmio_layout {
  bitaddr_t base;

  /* IN channel */
  bitaddr_t in_req;   /* 1 bit */
  bitaddr_t in_done;  /* 1 bit */
  bitaddr_t in_eof;   /* 1 bit */
  bitaddr_t in_err;   /* 1 bit */
  bitaddr_t in_dst;   /* ADDR_BITS */
  bitaddr_t in_len;   /* N_BITS */
  bitaddr_t in_got;   /* N_BITS */

  /* OUT channel */
  bitaddr_t out_req;  /* 1 bit */
  bitaddr_t out_done; /* 1 bit */
  bitaddr_t out_err;  /* 1 bit */
  bitaddr_t out_src;  /* ADDR_BITS */
  bitaddr_t out_len;  /* N_BITS */
  bitaddr_t out_got;  /* N_BITS */

  /* Control */
  bitaddr_t halt;     /* 1 bit */

  bitaddr_t end;      /* 1 past end */
} vm_mmio_layout_t;

typedef struct vm {
  uint8_t  *space;
  size_t    space_bytes;
  bitaddr_t space_bits;

  unsigned  processor_n;

  /* derived widths */
  unsigned  addr_bits;     /* rounded up to multiple of 8 */
  unsigned  n_bits;        /* == addr_bits */
  unsigned  instr_bits;    /* == 3*addr_bits */
  unsigned  instr_bytes;   /* instr_bits/8 */

  bitaddr_t processor_start; /* 0 */
  bitaddr_t processor_bits;  /* processor_n * instr_bits */

  /* field offsets inside instruction */
  unsigned off_n;     /* 0 */
  unsigned off_dst;   /* n_bits */
  unsigned off_src;   /* n_bits + addr_bits */

  vm_mmio_layout_t mmio;

  /* conventional workspace base (first free bit after MMIO) */
  bitaddr_t workspace_base;
  /* diagnostics */
  int strict_align32; /* if set, enforce 32-bit alignment for VAR_AP/VAR_BP/VAR_RP (std7_fixed) */
  uint64_t tick_counter; /* increments per vm_tick() call that completes */
  vm_err_t last_err;

} vm_t;

/* -------------------- Bit copy primitive -------------------- */

void bitcpy(size_t n_bits,
            const void *src_org, size_t src_bit,
            void *dst_org, size_t dst_bit);

/* -------------------- VM API -------------------- */

int     vm_init(vm_t *vm, size_t space_bytes, unsigned processor_n);
void    vm_free(vm_t *vm);

vm_rc_t vm_tick(vm_t *vm, FILE *in, FILE *out);
vm_rc_t vm_run(vm_t *vm, uint64_t life, FILE *in, FILE *out);

/* -------------------- Encoding helpers (arbitrary bit width) -------------------- */

/* bit get/set (MSB-first within byte) */
unsigned vm_bit_get(const vm_t *vm, bitaddr_t pos);
void     vm_bit_set(vm_t *vm, bitaddr_t pos, unsigned v);

/* read/write up to 64-bit unsigned, MSB-first */
uint64_t vm_read_uint(const vm_t *vm, bitaddr_t pos, unsigned width);
void     vm_write_uint(vm_t *vm, bitaddr_t pos, unsigned width, uint64_t value);

/* instruction read/write at bit address ip */
vm_inst_t vm_read_inst(const vm_t *vm, bitaddr_t ip);
void      vm_write_inst(vm_t *vm, bitaddr_t ip, vm_inst_t in);

/* processor slot addressing */
static inline bitaddr_t vm_proc_slot_ip(const vm_t *vm, unsigned slot) {
  return vm->processor_start + (bitaddr_t)slot * (bitaddr_t)vm->instr_bits;
}
static inline bitaddr_t vm_proc_slot_field_ip(const vm_t *vm, unsigned slot, unsigned field_off_bits) {
  return vm_proc_slot_ip(vm, slot) + (bitaddr_t)field_off_bits;
}

/* -------------------- Convenience: build a minimal boot layer with loader 3B --------------------
 *
 * Эта функция НЕ является "логикой VM"; это просто помощник, который записывает
 * копикод в область процессора.
 *
 * Конвенция loader-а 3B:
 *  - slot0: NOP (n=0), но в его dst поле лежит "next_layer_ptr" (битовый адрес слоя-образа)
 *  - patch_slot = PROCESSOR_N-2:
 *        copy ADDR_BITS, dst = (src-field of load_slot), src = (dst-field of slot0)
 *  - load_slot  = PROCESSOR_N-1:
 *        copy PROCESSOR_BITS, dst = PROCESSOR_START, src = (patched)
 *
 * После одного тика boot-слой загрузит слой по адресу next_layer_ptr.
 */
int vm_build_boot_loader_layer(vm_t *vm, bitaddr_t next_layer_ptr);

#endif /* COPYSPACE_H_ */
