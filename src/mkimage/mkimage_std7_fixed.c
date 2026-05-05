/* file: src/mkimage/mkimage_std7_fixed.c
 * date: 2026-05-04
 * purpose: wrapper entrypoint for std7_fixed mkimage (calls legacy, later calls modular builder)
 */
int std7_fixed_legacy_main(int argc, char **argv);

int main(int argc, char **argv) {
  return std7_fixed_legacy_main(argc, argv);
}
