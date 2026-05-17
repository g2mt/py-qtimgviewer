#pragma once
#include "Filter.h"
#include <QKeyEvent>
#include <QMainWindow>
#include <QMenu>
#include <QMenuBar>
#include <QSplitter>
#include <QToolBar>
#include <QVBoxLayout>

class ImageDetailList;
class ImageView;

class MainWindow : public QMainWindow {
  Filter filter;

  QSplitter *m_horizontalSplitter = nullptr;
  QSplitter *m_rightSplitter = nullptr;
  ImageView *m_imageView = nullptr;
  ImageDetailList *m_imageList = nullptr;
  QToolBar *m_toolbar = nullptr;
  QMenuBar *m_menuBar = nullptr;
  QAction *m_collapseViewAction = nullptr;
  QAction *m_backAction = nullptr;
  QAction *m_forwardAction = nullptr;

  void setupMenuBar();
  void setupToolbar(QToolBar *toolbar);
  void setupFilterMenu(QMenu *filterMenu);
  void setupMainLayout(QVBoxLayout *mainLayout);
  void setupImageView(QSplitter *horizontalSplitter);
  void setupRightSplitter(QSplitter *horizontalSplitter);
  void toggleCollapseView();
  void updateNavButtons();

  void setupEventFilters(QObject *obj);
  bool eventFilter(QObject *watched, QEvent *event);

public:
  MainWindow();
};
