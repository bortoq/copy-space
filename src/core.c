#include "core.h"

const size core[] = {
  CORE_STATUS_BITS, 3 * INSTRUCTION_SIZE + N_SIZE + ADDRESS_SIZE + CORE_ENTRY_SHIFT,
  INSTRUCTION_SIZE + N_SIZE + ADDRESS_SIZE,
  CORE_INPUT_BITS, CORE_BUFFER_START, 0,
  0, 0, 0,
  CORE_LAYER_BITS, PROCESSOR_START, CORE_TABLE_START,
};

static void encode(unsigned char *image, size base, const size *rows)
{
  size slot, field, bit;
  for(slot = 0; slot < 4; ++slot)
    for(field = 0; field < INSTRUCTION_FIELDS; ++field)
      for(bit = 0; bit < s[field]; ++bit)
      {
        size position = base + slot * INSTRUCTION_SIZE + o[field] + bit;
        image[position / CHAR_BIT] |= (unsigned char)
          (((rows[slot * INSTRUCTION_FIELDS + field] >> bit) & 1u)
           << (CHAR_BIT - 1 - position % CHAR_BIT));
      }
}

int core_init(void)
{
  const size activate[] = {0, 0, 0, 0, 0, 0, 0, 0, 0,
                          CORE_LAYER_BITS, PROCESSOR_START, CORE_BUFFER_START};
  const size failure[] = {0, 0, 0, 0, 0, 0,
                         CORE_ERROR_MESSAGE_BITS, CORE_ERROR_MESSAGE_START, 0,
                         CORE_LAYER_BITS, PROCESSOR_START, CORE_ERROR_ZERO_START};
  size_t bytes = (CORE_TABLE_START + CORE_TABLE_BITS + CHAR_BIT - 1) / CHAR_BIT;
  size entry;
  unsigned char *image = calloc(bytes, 1);
  int result;
  if(!image)
    return -1;
  encode(image, PROCESSOR_START, core);
  encode(image, CORE_RESTART_START, core);
  memcpy(image + CORE_ERROR_MESSAGE_START / CHAR_BIT,
         CORE_ERROR_MESSAGE, sizeof CORE_ERROR_MESSAGE - 1);
  for(entry = 0; entry < (1u << CORE_STATUS_BITS); ++entry)
    encode(image, CORE_TABLE_START + entry * CORE_BOOT_BITS,
           entry == 2 * CORE_INPUT_BITS ? activate : failure);
  result = space_init(image, bytes);
  free(image);
  return result;
}

int core_load_file(const char *path)
{
  FILE *file = fopen(path, "rb");
  unsigned char *image;
  size_t bytes;
  int result;
  if(!file)
    return -1;
  image = malloc((size_t)VM_SPACE_BYTES + 1);
  if(!image)
  {
    fclose(file);
    return -1;
  }
  bytes = fread(image, 1, (size_t)VM_SPACE_BYTES + 1, file);
  result = ferror(file) ? -1 : space_init(image, bytes);
  if(fclose(file) != 0)
    result = -1;
  free(image);
  return result;
}
