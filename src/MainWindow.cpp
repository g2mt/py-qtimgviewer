#include <QApplication>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QSplitter>
#include <QTabWidget>
#include <QToolButton>
#include <imgviewer/DirectoryList.h>
#include <imgviewer/ImageDetailList.h>
#include <imgviewer/ImageView.h>
#include <imgviewer/MainWindow.h>
#include <imgviewer/TagList.h>

MainWindow::MainWindow() {
  QWidget *centralWidget = new QWidget(this);
  QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);
  mainLayout->setContentsMargins(0, 0, 0, 0);
  mainLayout->setSpacing(0);
  setCentralWidget(centralWidget);

  setupMenuBar();

  m_toolbar = new QToolBar(this);
  addToolBar(m_toolbar);
  setupToolbar(m_toolbar);
  setupMainLayout(mainLayout);

  installEventFilter(this);
  setupEventFilters(this);
}

void MainWindow::setupFilterMenu(QMenu *filterMenu) {
  QAction *nameAct = filterMenu->addAction("Name");
  nameAct->setCheckable(true);
  nameAct->setChecked(true);
  QAction *dateCreatedAct = filterMenu->addAction("Date Created");
  dateCreatedAct->setCheckable(true);
  QAction *dateModifiedAct = filterMenu->addAction("Date Modified");
  dateModifiedAct->setCheckable(true);
  filterMenu->addSeparator();
  QAction *descAction = filterMenu->addAction("Descending");
  descAction->setCheckable(true);
  QAction *natAction = filterMenu->addAction("Natural Sort");
  natAction->setCheckable(true);

  connect(nameAct, &QAction::triggered,
          [this]() { filter.setSortBy(SortBy::Name); });
  connect(dateCreatedAct, &QAction::triggered,
          [this]() { filter.setSortBy(SortBy::DateCreated); });
  connect(dateModifiedAct, &QAction::triggered,
          [this]() { filter.setSortBy(SortBy::DateModified); });
  connect(descAction, &QAction::toggled,
          [this](bool checked) { filter.setDescending(checked); });
  connect(natAction, &QAction::toggled,
          [this](bool checked) { filter.setNaturalSort(checked); });
}

void MainWindow::setupToolbar(QToolBar *toolbar) {
  toolbar->addAction(QIcon::fromTheme("go-previous"), "Back");
  toolbar->addAction(QIcon::fromTheme("go-next"), "Forward");

  QWidget *spacer = new QWidget();
  spacer->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
  toolbar->addWidget(spacer);

  QLineEdit *searchBox = new QLineEdit();
  searchBox->setPlaceholderText("Filter images");
  searchBox->addAction(QIcon::fromTheme("edit-find"),
                       QLineEdit::LeadingPosition);
  searchBox->setMaximumWidth(200);
  toolbar->addWidget(searchBox);
  connect(searchBox, &QLineEdit::textChanged,
          [this](const QString &text) { filter.setSearch(text); });

  QMenu *filterMenu = new QMenu("Filter", this);
  setupFilterMenu(filterMenu);

  QToolButton *filterBtn = new QToolButton();
  filterBtn->setIcon(QIcon::fromTheme("view-filter"));
  filterBtn->setPopupMode(QToolButton::InstantPopup);
  filterBtn->setMenu(filterMenu);
  toolbar->addWidget(filterBtn);
}

void MainWindow::setupMenuBar() {
  m_menuBar = new QMenuBar(this);
  setMenuBar(m_menuBar);

  QMenu *fileMenu = m_menuBar->addMenu("&File");
  QAction *quitAction = fileMenu->addAction("&Quit");
  quitAction->setShortcut(QKeySequence("Ctrl+Q"));
  connect(quitAction, &QAction::triggered, this, &QMainWindow::close);

  QMenu *viewMenu = m_menuBar->addMenu("&View");
  m_collapseViewAction = viewMenu->addAction("&Collapse View");
  m_collapseViewAction->setShortcut(QKeySequence("Tab"));
  m_collapseViewAction->setCheckable(true);
  connect(m_collapseViewAction, &QAction::triggered, this,
          &MainWindow::toggleCollapseView);

  QMenu *filterMenu = m_menuBar->addMenu("Fil&ter");
  setupFilterMenu(filterMenu);
}

void MainWindow::toggleCollapseView() {
  bool collapsed = m_collapseViewAction->isChecked();
  m_toolbar->setVisible(!collapsed);
  m_menuBar->setVisible(!collapsed);
  m_rightSplitter->setVisible(!collapsed);
}

void MainWindow::setupMainLayout(QVBoxLayout *mainLayout) {
  m_horizontalSplitter = new QSplitter(Qt::Horizontal);
  mainLayout->addWidget(m_horizontalSplitter);

  m_imageView = setupImageView(m_horizontalSplitter);
  setupRightSplitter(m_horizontalSplitter, m_imageView);
}

ImageView *MainWindow::setupImageView(QSplitter *horizontalSplitter) {
  ImageView *imageView = new ImageView();
  horizontalSplitter->addWidget(imageView);
  horizontalSplitter->setStretchFactor(0, 6);
  horizontalSplitter->setCollapsible(0, false);
  return imageView;
}

void MainWindow::setupRightSplitter(QSplitter *horizontalSplitter,
                                    ImageView *imageView) {
  m_rightSplitter = new QSplitter(Qt::Vertical);

  QTabWidget *tabs = new QTabWidget();
  DirectoryList *dirList = new DirectoryList(&filter);
  tabs->addTab(dirList, "Directory");
  TagList *tagList = new TagList();
  tabs->addTab(tagList, "Tags");
  m_rightSplitter->addWidget(tabs);
  connect(tagList, &TagList::itemSelectionChanged, [this, tagList]() {
    QList<QString> list;
    for (auto item : tagList->selectedItems())
      list.append(item->text());
    filter.setTags(list);
  });

  ImageDetailList *imageList = new ImageDetailList(&filter);
  m_rightSplitter->addWidget(imageList);
  connect(imageList, &ImageDetailList::imageActivated, imageView,
          &ImageView::setImage);

  horizontalSplitter->addWidget(m_rightSplitter);
  horizontalSplitter->setStretchFactor(1, 1);
  horizontalSplitter->setCollapsible(1, false);
}

void MainWindow::setupEventFilters(QObject *obj) {
  for (QObject *child : obj->children()) {
    if (child->isWidgetType()) {
      child->installEventFilter(this);
    }
    setupEventFilters(child);
  }
}

bool MainWindow::eventFilter(QObject *watched, QEvent *event) {
  if (event->type() == QEvent::KeyPress) {
    QKeyEvent *keyEvent = static_cast<QKeyEvent *>(event);

    if (keyEvent->key() == Qt::Key_Tab) {
      m_collapseViewAction->trigger();
      return false;
    }
  }
  return QMainWindow::eventFilter(watched, event);
}
