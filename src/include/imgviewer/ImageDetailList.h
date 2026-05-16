#pragma once
#include <QListView>

class ImageDetailList : public QListView {
public:
  ImageDetailList(QWidget *parent = nullptr) : QListView(parent) {
    setViewMode(QListView::ListMode);
    setResizeMode(QListView::Adjust);
    setLayoutMode(QListView::Batched);
    setMovement(QListView::Static);
    setUniformItemSizes(true);
  }
};
