cmake_minimum_required(VERSION 3.16)

project(copy_space_native C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# With -B build, binaries have the same paths as the Make build.
set(_OUTDIR "${CMAKE_BINARY_DIR}/bin")
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

add_library(bitcopy STATIC src/bitcopy.c)
target_include_directories(bitcopy PUBLIC "${CMAKE_SOURCE_DIR}/src")
add_library(space_kernel STATIC src/space.c)
target_link_libraries(space_kernel PUBLIC bitcopy)
add_library(space_runtime STATIC src/space_run.c src/core.c src/space_trace.c)
target_link_libraries(space_runtime PUBLIC space_kernel)

add_executable(space src/space_main.c)
target_link_libraries(space PRIVATE space_runtime)
add_executable(assembler src/assembler.c)
target_link_libraries(assembler PRIVATE bitcopy)

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
  add_executable(test_bitcopy tests/test_bitcopy.c)
  target_link_libraries(test_bitcopy PRIVATE bitcopy)
  add_test(NAME bitcopy COMMAND test_bitcopy)
  add_executable(test_space_runtime tests/test_space_runtime.c)
  target_link_libraries(test_space_runtime PRIVATE space_runtime)
  add_test(NAME space_runtime COMMAND test_space_runtime)
  add_executable(space_image_proof tests/space_image_proof.c)
  target_link_libraries(space_image_proof PRIVATE space_runtime)
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_executable(test_rv32i_io_partial tests/test_rv32i_io_partial.c)
    target_link_libraries(test_rv32i_io_partial PRIVATE space_runtime)
  endif()
  add_test(NAME assembler_limits
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tests/test_assembler.py"
            --assembler "$<TARGET_FILE:assembler>"
            --artifacts "${CMAKE_BINARY_DIR}/assembler-test-artifacts")
endif()
