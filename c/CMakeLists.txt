cmake_minimum_required(VERSION 3.16)
project(salahlib_c C)

add_library(prayer_times STATIC src/prayer_times.c)
target_include_directories(prayer_times PUBLIC include)
target_link_libraries(prayer_times m)

add_executable(prayer_times_dump tools/dump.c)
target_link_libraries(prayer_times_dump prayer_times m)

enable_testing()
add_executable(prayer_times_test test/test_kernel.c)
target_link_libraries(prayer_times_test prayer_times m)
add_test(NAME kernel COMMAND prayer_times_test)

add_executable(prayer_times_aladhan_test test/test_aladhan.c)
target_link_libraries(prayer_times_aladhan_test prayer_times m)
add_test(NAME aladhan COMMAND prayer_times_aladhan_test)
