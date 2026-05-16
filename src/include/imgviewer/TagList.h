#pragma once
#include <QListWidget>

class TagList : public QListWidget {
public:
  TagList(QWidget *parent = nullptr) : QListWidget(parent) {
    setSelectionMode(QAbstractItemView::MultiSelection);
  }
};
