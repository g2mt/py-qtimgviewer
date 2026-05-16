#pragma once
#include <QFrame>

class ImageView : public QFrame {
public:
  ImageView(QWidget *parent = nullptr) : QFrame(parent) {
    setStyleSheet("background-color: #333; color: white;");
  }
};
