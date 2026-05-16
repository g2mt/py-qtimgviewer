cmake_minimum_required(VERSION 3.16)
project(hello-qt LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(hello-qt src/main.cpp)
target_link_libraries(hello-qt Qt6::Widgets)
