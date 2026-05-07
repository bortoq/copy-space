/* forth0c_syms.inc — ART symbol table helpers (included into forth0c TU). */

typedef struct {
  const char *name;
  unsigned art_idx;
} sym_t;

static int str_ieq(const char *a, const char *b) {
  while (*a && *b) {
    unsigned ca = (unsigned char)*a++;
    unsigned cb = (unsigned char)*b++;
    if (tolower(ca) != tolower(cb)) return 0;
  }
  return *a == 0 && *b == 0;
}

static const sym_t g_syms[] = {
  /* core */
  {"HEAD_CELL", ART_HEAD_CELL}, {"ART_HEAD_CELL", ART_HEAD_CELL},
  {"NEXT_IMG",  ART_NEXT_IMG},  {"ART_NEXT_IMG",  ART_NEXT_IMG},
  {"VAR_IP",    ART_VAR_IP},    {"ART_VAR_IP",    ART_VAR_IP},

  {"WORD_SETUP",  ART_WORD_SETUP},  {"ART_WORD_SETUP",  ART_WORD_SETUP},  {"SETUP",  ART_WORD_SETUP},
  {"WORD_INREQ",  ART_WORD_INREQ},  {"ART_WORD_INREQ",  ART_WORD_INREQ},  {"INREQ",  ART_WORD_INREQ},
  {"WORD_OUTREQ", ART_WORD_OUTREQ}, {"ART_WORD_OUTREQ", ART_WORD_OUTREQ}, {"OUTREQ", ART_WORD_OUTREQ},
  {"WORD_HALT",   ART_WORD_HALT},   {"ART_WORD_HALT",   ART_WORD_HALT},   {"HALT",   ART_WORD_HALT},

  {"VAR_LOOP",     ART_VAR_LOOP},     {"ART_VAR_LOOP",     ART_VAR_LOOP},
  {"WORD_SAVEIP",  ART_WORD_SAVEIP},  {"ART_WORD_SAVEIP",  ART_WORD_SAVEIP},  {"SAVEIP",  ART_WORD_SAVEIP},
  {"WORD_JMP",     ART_WORD_JMP},     {"ART_WORD_JMP",     ART_WORD_JMP},     {"JMP",     ART_WORD_JMP},
  {"WORD_SETOLEN", ART_WORD_SETOLEN}, {"ART_WORD_SETOLEN", ART_WORD_SETOLEN}, {"SETOLEN", ART_WORD_SETOLEN},
  {"WORD_IFGOT0",  ART_WORD_IFGOT0},  {"ART_WORD_IFGOT0",  ART_WORD_IFGOT0},  {"IFGOT0",  ART_WORD_IFGOT0},

  {"VAR_N",   ART_VAR_N},   {"ART_VAR_N",   ART_VAR_N},
  {"VAR_DST", ART_VAR_DST}, {"ART_VAR_DST", ART_VAR_DST},
  {"VAR_SRC", ART_VAR_SRC}, {"ART_VAR_SRC", ART_VAR_SRC},

  {"WORD_LITN",  ART_WORD_LITN},  {"ART_WORD_LITN",  ART_WORD_LITN},  {"LITN",  ART_WORD_LITN},
  {"WORD_LITD",  ART_WORD_LITD},  {"ART_WORD_LITD",  ART_WORD_LITD},  {"LITD",  ART_WORD_LITD},
  {"WORD_LITS",  ART_WORD_LITS},  {"ART_WORD_LITS",  ART_WORD_LITS},  {"LITS",  ART_WORD_LITS},
  {"WORD_COPY",  ART_WORD_COPY},  {"ART_WORD_COPY",  ART_WORD_COPY},  {"COPY",  ART_WORD_COPY},
  {"WORD_LITIP", ART_WORD_LITIP}, {"ART_WORD_LITIP", ART_WORD_LITIP}, {"LITIP", ART_WORD_LITIP},

  {"BA", ART_BA}, {"ART_BA", ART_BA},
  {"BB", ART_BB}, {"ART_BB", ART_BB},
  {"BC", ART_BC}, {"ART_BC", ART_BC},
  {"BR", ART_BR}, {"ART_BR", ART_BR},
  {"T0", ART_T0}, {"ART_T0", ART_T0},
  {"T1", ART_T1}, {"ART_T1", ART_T1},

  {"WORD_BNOT", ART_WORD_BNOT}, {"ART_WORD_BNOT", ART_WORD_BNOT}, {"BNOT", ART_WORD_BNOT},
  {"WORD_BAND", ART_WORD_BAND}, {"ART_WORD_BAND", ART_WORD_BAND}, {"BAND", ART_WORD_BAND},

  {"CONST1", ART_CONST1}, {"ART_CONST1", ART_CONST1},
  {"CONST0", ART_CONST0}, {"ART_CONST0", ART_CONST0},
  {"TESTG",  ART_TESTG},  {"ART_TESTG",  ART_TESTG},

  {"WORD_BOR",  ART_WORD_BOR},  {"ART_WORD_BOR",  ART_WORD_BOR},  {"BOR",  ART_WORD_BOR},
  {"WORD_BXOR", ART_WORD_BXOR}, {"ART_WORD_BXOR", ART_WORD_BXOR}, {"BXOR", ART_WORD_BXOR},

  /* 2a */
  {"WORD_ADD24", ART_WORD_ADD24}, {"ART_WORD_ADD24", ART_WORD_ADD24}, {"ADD24", ART_WORD_ADD24},
  {"VAR_A24",    ART_VAR_A24},    {"ART_VAR_A24",    ART_VAR_A24},
  {"VAR_B24",    ART_VAR_B24},    {"ART_VAR_B24",    ART_VAR_B24},
  {"VAR_SUM24",  ART_VAR_SUM24},  {"ART_VAR_SUM24",  ART_VAR_SUM24},
  {"VAR_COUT",   ART_VAR_COUT},   {"ART_VAR_COUT",   ART_VAR_COUT},
  {"WORD_EQ24",  ART_WORD_EQ24},  {"ART_WORD_EQ24",  ART_WORD_EQ24},  {"EQ24", ART_WORD_EQ24},
  {"VAR_EQ",     ART_VAR_EQ},     {"ART_VAR_EQ",     ART_VAR_EQ},
  {"WORD_LT24",  ART_WORD_LT24},  {"ART_WORD_LT24",  ART_WORD_LT24},  {"LT24", ART_WORD_LT24},
  {"VAR_LT",     ART_VAR_LT},     {"ART_VAR_LT",     ART_VAR_LT},

  /* 2b pointers */
  {"WORD_LITAP", ART_WORD_LITAP}, {"ART_WORD_LITAP", ART_WORD_LITAP}, {"LITAP", ART_WORD_LITAP},
  {"WORD_LITBP", ART_WORD_LITBP}, {"ART_WORD_LITBP", ART_WORD_LITBP}, {"LITBP", ART_WORD_LITBP},
  {"WORD_LITRP", ART_WORD_LITRP}, {"ART_WORD_LITRP", ART_WORD_LITRP}, {"LITRP", ART_WORD_LITRP},
  {"VAR_AP",     ART_VAR_AP},     {"ART_VAR_AP",     ART_VAR_AP},
  {"VAR_BP",     ART_VAR_BP},     {"ART_VAR_BP",     ART_VAR_BP},
  {"VAR_RP",     ART_VAR_RP},     {"ART_VAR_RP",     ART_VAR_RP},
  {"OFFTAB",     ART_OFFTAB},     {"ART_OFFTAB",     ART_OFFTAB},
  {"WORD_EQ24P", ART_WORD_EQ24P}, {"ART_WORD_EQ24P", ART_WORD_EQ24P}, {"EQ24P", ART_WORD_EQ24P},

  /* scratch/devices */
  {"TESTSCR_BASE", ART_TESTSCR_BASE}, {"ART_TESTSCR_BASE", ART_TESTSCR_BASE},
  {"TESTSCR_END",  ART_TESTSCR_END},  {"ART_TESTSCR_END",  ART_TESTSCR_END},
  {"BUS_BASE",     ART_BUS_BASE},     {"ART_BUS_BASE",     ART_BUS_BASE},
  {"TERM0_DESC",   ART_TERM0_DESC},   {"ART_TERM0_DESC",   ART_TERM0_DESC},

  /* ptrprims */
  {"WORD_LOAD24AP",  ART_WORD_LOAD24AP},  {"ART_WORD_LOAD24AP",  ART_WORD_LOAD24AP},  {"LOAD24AP",  ART_WORD_LOAD24AP},
  {"WORD_LOAD24BP",  ART_WORD_LOAD24BP},  {"ART_WORD_LOAD24BP",  ART_WORD_LOAD24BP},  {"LOAD24BP",  ART_WORD_LOAD24BP},
  {"WORD_STORE24RP", ART_WORD_STORE24RP}, {"ART_WORD_STORE24RP", ART_WORD_STORE24RP}, {"STORE24RP", ART_WORD_STORE24RP},
};

static int sym_lookup_art_idx(const char *name, unsigned *out_idx) {
  /* allow ART[NN] */
  if ((name[0]=='A'||name[0]=='a') && (name[1]=='R'||name[1]=='r') && (name[2]=='T'||name[2]=='t') && name[3]=='[') {
    const char *p = name + 4;
    char *e = NULL;
    errno = 0;
    unsigned long v = strtoul(p, &e, 10);
    if (errno == 0 && e && *e == ']') {
      *out_idx = (unsigned)v;
      return 1;
    }
  }

  for (size_t i = 0; i < sizeof(g_syms)/sizeof(g_syms[0]); i++) {
    if (str_ieq(name, g_syms[i].name)) {
      *out_idx = g_syms[i].art_idx;
      return 1;
    }
  }
  return 0;
}
