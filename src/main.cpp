#include <QApplication>
#include <imgviewer/MainWindow.h>

int main(int argc, char *argv[]) {
  QApplication app(argc, argv);
  MainWindow win;
  win.resize(1000, 700);
  win.show();
  return app.exec();
}
