/* gen.inc — directive codegen helpers + tiny semantic checks */

static int word_needs_imm(const char *name) {
  return str_ieq(name, "LITN")  || str_ieq(name, "WORD_LITN")  || str_ieq(name, "ART_WORD_LITN") ||
         str_ieq(name, "LITD")  || str_ieq(name, "WORD_LITD")  || str_ieq(name, "ART_WORD_LITD") ||
         str_ieq(name, "LITS")  || str_ieq(name, "WORD_LITS")  || str_ieq(name, "ART_WORD_LITS") ||
         str_ieq(name, "LITIP") || str_ieq(name, "WORD_LITIP") || str_ieq(name, "ART_WORD_LITIP") ||
         str_ieq(name, "LITAP") || str_ieq(name, "WORD_LITAP") || str_ieq(name, "ART_WORD_LITAP") ||
         str_ieq(name, "LITBP") || str_ieq(name, "WORD_LITBP") || str_ieq(name, "ART_WORD_LITBP") ||
         str_ieq(name, "LITRP") || str_ieq(name, "WORD_LITRP") || str_ieq(name, "ART_WORD_LITRP");
}

static int is_ptr_lit_word(const char *name) {
  return str_ieq(name, "LITAP") || str_ieq(name, "WORD_LITAP") || str_ieq(name, "ART_WORD_LITAP") ||
         str_ieq(name, "LITBP") || str_ieq(name, "WORD_LITBP") || str_ieq(name, "ART_WORD_LITBP") ||
         str_ieq(name, "LITRP") || str_ieq(name, "WORD_LITRP") || str_ieq(name, "ART_WORD_LITRP");
}

static void do_copybits(pstate_t *ps, FILE *out, uint64_t n, uint64_t dst, uint64_t src) {
  emit_lit_word_imm(ps, out, ART_WORD_LITN, n);
  emit_lit_word_imm(ps, out, ART_WORD_LITD, dst);
  emit_lit_word_imm(ps, out, ART_WORD_LITS, src);
  emit_word_by_artidx(ps, out, ART_WORD_COPY);
}

static void do_setbit(pstate_t *ps, FILE *out, uint64_t dst_bitaddr, int val01) {
  uint64_t src = artv(ps, val01 ? ART_CONST1 : ART_CONST0);
  do_copybits(ps, out, 1u, dst_bitaddr, src);
}

static void do_setbyte(pstate_t *ps, FILE *out, uint64_t byte_bitaddr, uint64_t u8) {
  u8 &= 0xFFu;
  for (unsigned off = 0; off < 8u; off++) {
    unsigned bit = (unsigned)((u8 >> (7u - off)) & 1u);
    do_setbit(ps, out, byte_bitaddr + (uint64_t)off, (int)bit);
  }
}

static void do_set24(pstate_t *ps, FILE *out, uint64_t base_bitaddr, uint64_t u24) {
  u24 &= 0xFFFFFFu;
  uint64_t b0 = (u24 >> 16) & 0xFFu;
  uint64_t b1 = (u24 >>  8) & 0xFFu;
  uint64_t b2 = (u24 >>  0) & 0xFFu;
  do_setbyte(ps, out, base_bitaddr + 0u*8u, b0);
  do_setbyte(ps, out, base_bitaddr + 1u*8u, b1);
  do_setbyte(ps, out, base_bitaddr + 2u*8u, b2);
}

/* Generic set-N-bits: write val to dst at bit granularity */
static void do_set_bits(pstate_t *ps, FILE *out, bitaddr_t dst, uint64_t val, unsigned nbits) {
  unsigned full_bytes = nbits / 8u;
  for (unsigned i = 0; i < full_bytes; i++) {
    unsigned shift = (full_bytes - 1u - i) * 8u;
    do_setbyte(ps, out, dst + (uint64_t)i * 8u, (val >> shift) & 0xFFu);
  }
  unsigned rem = nbits % 8u;
  if (rem > 0) {
    unsigned shift = nbits - rem;
    for (unsigned i = 0; i < rem; i++) {
      unsigned bit = (unsigned)((val >> (shift + (rem - 1u - i))) & 1u);
      do_setbit(ps, out, dst + (uint64_t)full_bytes * 8u + (uint64_t)i, (int)bit);
    }
  }
}

/* Write one processor instruction slot at page_addr+slot*instr_bits */
static void do_instr(pstate_t *ps, FILE *out, bitaddr_t page_addr, unsigned slot) {
  bitaddr_t slot_addr = page_addr + (bitaddr_t)slot * (bitaddr_t)ps->vm->instr_bits;
  uint64_t n   = parse_expr(ps);
  uint64_t dst = parse_expr(ps);
  uint64_t src = parse_expr(ps);
  do_set_bits(ps, out, slot_addr + (bitaddr_t)ps->vm->off_n,   n,   ps->vm->n_bits);
  do_set_bits(ps, out, slot_addr + (bitaddr_t)ps->vm->off_dst, dst, ps->vm->addr_bits);
  do_set_bits(ps, out, slot_addr + (bitaddr_t)ps->vm->off_src, src, ps->vm->addr_bits);
}
