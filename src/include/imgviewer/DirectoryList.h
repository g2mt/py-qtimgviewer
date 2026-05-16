#pragma once
#include <QListWidget>

class DirectoryList : public QListWidget {
public:
  DirectoryList(QWidget *parent = nullptr) : QListWidget(parent) {
    setSelectionMode(QAbstractItemView::MultiSelection);
  }
};
