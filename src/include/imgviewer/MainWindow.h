#pragma once
#include "Filter.h"
#include <QMainWindow>
#include <QMenu>
#include <QSplitter>
#include <QToolBar>
#include <QVBoxLayout>

class MainWindow : public QMainWindow {
  Filter filter;

  void setupToolbar(QToolBar *toolbar);
  void setupFilterMenu(QMenu *filterMenu);
  void setupMainLayout(QVBoxLayout *mainLayout);
  void setupImageView(QSplitter *horizontalSplitter);
  void setupRightSplitter(QSplitter *horizontalSplitter);

public:
  MainWindow();
};
