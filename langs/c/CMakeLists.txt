cmake_minimum_required(VERSION 3.16)
project(salahlib_c VERSION 0.1.0 LANGUAGES C)

# Regenerate the method registry header whenever shared/methods.json changes.
set(METHODS_HEADER ${CMAKE_CURRENT_SOURCE_DIR}/include/methods_generated.h)
set(METHODS_GEN ${CMAKE_CURRENT_SOURCE_DIR}/../../scripts/generate_c_methods.py)
add_custom_command(
    OUTPUT ${METHODS_HEADER}
    COMMAND python3 ${METHODS_GEN}
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../../shared/methods.json ${METHODS_GEN}
    COMMENT "Generating methods_generated.h from methods.json"
    VERBATIM
)
add_custom_target(generate_methods DEPENDS ${METHODS_HEADER})

add_library(prayer_times STATIC src/prayer_times.c src/methods.c)
target_include_directories(prayer_times PUBLIC include)
target_link_libraries(prayer_times m)
add_dependencies(prayer_times generate_methods)

add_executable(prayer_times_dump tools/dump.c)
target_link_libraries(prayer_times_dump prayer_times m)

enable_testing()
add_executable(prayer_times_test test/test_kernel.c)
target_link_libraries(prayer_times_test prayer_times m)
add_test(NAME kernel COMMAND prayer_times_test)

add_executable(prayer_times_aladhan_test test/test_aladhan.c)
target_link_libraries(prayer_times_aladhan_test prayer_times m)
add_test(NAME aladhan COMMAND prayer_times_aladhan_test)

add_executable(prayer_times_methods_test test/test_methods.c)
target_link_libraries(prayer_times_methods_test prayer_times m)
add_test(NAME methods COMMAND prayer_times_methods_test)
