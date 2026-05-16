cmake_minimum_required(VERSION 3.16)
project(imgviewer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(imgviewer 
    src/main.cpp 
    src/MainWindow.cpp 
    src/Filter.cpp 
    src/ImageView.cpp 
    src/DirectoryList.cpp 
    src/TagList.cpp 
    src/ImageDetailList.cpp
)
target_compile_definitions(imgviewer PRIVATE -DQT_DEPRECATED_WARNINGS)
target_include_directories(imgviewer PRIVATE src/include)
target_link_libraries(imgviewer Qt6::Widgets)
