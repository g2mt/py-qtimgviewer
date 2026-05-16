#pragma once
#include "Filter.h"
#include <QMainWindow>
#include <QMenu>
#include <QMenuBar>
#include <QSplitter>
#include <QToolBar>
#include <QVBoxLayout>

class ImageView;

class MainWindow : public QMainWindow {
  Filter filter;

  QSplitter *m_horizontalSplitter = nullptr;
  QSplitter *m_rightSplitter = nullptr;
  ImageView *m_imageView = nullptr;
  QToolBar *m_toolbar = nullptr;
  QMenuBar *m_menuBar = nullptr;
  QAction *m_collapseViewAction = nullptr;

  void setupMenuBar();
  void setupToolbar(QToolBar *toolbar);
  void setupFilterMenu(QMenu *filterMenu);
  void setupMainLayout(QVBoxLayout *mainLayout);
  ImageView *setupImageView(QSplitter *horizontalSplitter);
  void setupRightSplitter(QSplitter *horizontalSplitter, ImageView *imageView);
  void toggleCollapseView();

public:
  MainWindow();
};
