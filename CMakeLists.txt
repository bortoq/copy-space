cmake_minimum_required(VERSION 3.16)

project(copy_space_native C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Put runtime binaries into the existing repo location used by scripts: build/bin
set(_OUTDIR "${CMAKE_SOURCE_DIR}/build/bin")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${_OUTDIR}")
foreach(cfg DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  string(TOUPPER "${cfg}" cfg_u)
  set("CMAKE_RUNTIME_OUTPUT_DIRECTORY_${cfg_u}" "${_OUTDIR}")
endforeach()

# Reasonable warnings
if(MSVC)
  add_compile_options(/W4)
else()
  add_compile_options(-Wall -Wextra)
endif()

# -------------------- core VM library --------------------

set(VM_SRCS
  src/vm/space.c
  src/vm/bitcpy.c
)

if(EXISTS "${CMAKE_SOURCE_DIR}/src/vm/diag/vmrep.c")
  list(APPEND VM_SRCS src/vm/diag/vmrep.c)
endif()

add_library(vmcore STATIC ${VM_SRCS})
target_include_directories(vmcore PUBLIC
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/vm"
)

# -------------------- tools (5 bins total) --------------------

add_executable(vmrun src/tools/vmrun.c)
target_link_libraries(vmrun PRIVATE vmcore)

add_executable(vmprep_forth0 src/tools/vmprep_forth0.c)
target_link_libraries(vmprep_forth0 PRIVATE vmcore)

add_executable(forth0c src/tools/forth0c.c)
target_link_libraries(forth0c PRIVATE vmcore)

add_executable(mkbench_bulkcopy src/tools/mkbench_bulkcopy.c)
target_link_libraries(mkbench_bulkcopy PRIVATE vmcore)

file(GLOB MKIMAGE_STD7_FIXED_SRCS
  "${CMAKE_SOURCE_DIR}/src/mkimage/mkimage_std7_fixed.c"
  "${CMAKE_SOURCE_DIR}/src/mkimage/std7_fixed/*.c"
)

add_executable(mkimage_std7_fixed ${MKIMAGE_STD7_FIXED_SRCS})
target_include_directories(mkimage_std7_fixed PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/vm"
  "${CMAKE_SOURCE_DIR}/src/mkimage/std7_fixed"
)
target_link_libraries(mkimage_std7_fixed PRIVATE vmcore)
