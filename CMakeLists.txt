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
    src/TagListContainer.cpp 
    src/ImageDetailList.cpp
    src/ImageDetailModel.cpp
    src/utils.cpp

    ### Contains Q_OBJECT macros, needed for automoc
    src/include/imgviewer/DirectoryList.h
    src/include/imgviewer/Filter.h
    src/include/imgviewer/ImageView.h
    src/include/imgviewer/ImageDetailList.h
    src/include/imgviewer/ImageDetailModel.h
    src/include/imgviewer/TagList.h
    src/include/imgviewer/TagListContainer.h
)
target_compile_definitions(imgviewer PRIVATE -DQT_DEPRECATED_WARNINGS)
target_include_directories(imgviewer PRIVATE src/include)
target_link_libraries(imgviewer PRIVATE Qt6::Widgets)

find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
  pkg_check_modules(LIBARCHIVE libarchive)
endif()

if(LIBARCHIVE_FOUND)
  target_compile_definitions(imgviewer PRIVATE IMGVIEWER_FEAT_ARCHIVE)
  target_include_directories(imgviewer PRIVATE ${LIBARCHIVE_INCLUDE_DIRS})
  target_link_libraries(imgviewer PRIVATE ${LIBARCHIVE_LIBRARIES})
  message(STATUS "libarchive found - archive support enabled")
else()
  message(STATUS "libarchive not found - archive support disabled")
endif()

include(GNUInstallDirs)

install(TARGETS imgviewer RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

install(
  FILES branding/logo-circle.png
  RENAME imgviewer.png
  DESTINATION ${CMAKE_INSTALL_DATADIR}/icons
)

install(
  FILES branding/imgviewer.desktop
  DESTINATION ${CMAKE_INSTALL_DATADIR}/applications
)
