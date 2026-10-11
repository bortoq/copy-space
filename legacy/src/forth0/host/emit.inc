/* emit.inc — token emission + ART reads */

static void write_be(FILE *f, uint64_t v, unsigned nbytes) {
  for (unsigned i = 0; i < nbytes; i++) {
    unsigned shift = 8u*(nbytes-1u-i);
    fputc((int)((v >> shift) & 0xFFu), f);
  }
}

static void emit_u(vm_t *vm, FILE *out, uint64_t v) {
  unsigned nbytes = vm->addr_bits / 8u;
  if (nbytes == 0 || (vm->addr_bits % 8u) != 0) {
    fprintf(stderr, "forth0c: unsupported addr_bits=%u\n", vm->addr_bits);
    exit(1);
  }
  if (vm->addr_bits < 64u) {
    uint64_t mask = (1ull << vm->addr_bits) - 1ull;
    v &= mask;
  }
  write_be(out, v, nbytes);
}

static uint64_t art_read(vm_t *vm, bitaddr_t ART, unsigned idx) {
  return vm_read_uint(vm, ART + (bitaddr_t)idx * (bitaddr_t)vm->addr_bits, vm->addr_bits);
}

static uint64_t artv(pstate_t *ps, unsigned idx) {
  if (idx >= ps->art_count) {
    fprintf(stderr, "forth0c: internal: ART idx out of range: %u\n", idx);
    exit(1);
  }
  return art_read(ps->vm, ps->ART, idx);
}

static void emit_word_by_artidx(pstate_t *ps, FILE *out, unsigned word_art_idx) {
  uint64_t w = artv(ps, word_art_idx);
  if (!w) {
    fprintf(stderr, "forth0c: %s:%u: ART[%u] is 0 (word missing)\n", ps->lx->path, ps->lx->line, word_art_idx);
    exit(1);
  }
  emit_u(ps->vm, out, w);
}

static void emit_lit_word_imm(pstate_t *ps, FILE *out, unsigned lit_word_art_idx, uint64_t imm) {
  emit_word_by_artidx(ps, out, lit_word_art_idx);
  emit_u(ps->vm, out, imm);
}
