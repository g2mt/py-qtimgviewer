#pragma once
#include <QFrame>
#include <QKeyEvent>
#include <QLabel>
#include <QPixmap>
#include <QPoint>
#include <QPointF>

// Camera describes the affine mapping between image-space pixels and the
// widget's screen-space pixels. The point `imageTarget` (in image
// coordinates) is mapped to the widget position `offset` (relative to the
// widget's top-left corner). Distances are multiplied by `zoom`, where 1.0
// means one image pixel maps to one widget pixel. `zoom` must be > 0.
struct Camera {
  float zoom = 1.0f;
  QPointF imageTarget;
  QPointF offset;

  QPointF imageToScreen(const QPointF &p) const {
    return (p - imageTarget) * zoom + offset;
  }

  QPointF screenToImage(const QPointF &p) const {
    return (p - offset) / zoom + imageTarget;
  }
};

class ImageView : public QFrame {
  Q_OBJECT

public:
  ImageView(QWidget *parent = nullptr);
  void setImage(const QString &path);

signals:
  void collapseRequested();

protected:
  void dragEnterEvent(QDragEnterEvent *event) override;
  void dragMoveEvent(QDragMoveEvent *event) override;
  void dropEvent(QDropEvent *event) override;
  void keyPressEvent(QKeyEvent *event) override;
  void mousePressEvent(QMouseEvent *event) override;
  void mouseMoveEvent(QMouseEvent *event) override;
  void mouseReleaseEvent(QMouseEvent *event) override;
  void wheelEvent(QWheelEvent *event) override;
  void resizeEvent(QResizeEvent *event) override;
  void paintEvent(QPaintEvent *event) override;

private:
  void updateImageDisplay();
  bool hasImage() const;
  // Reset the camera so the image is fit to the widget width and centered.
  void resetCamera();

  QLabel *m_placeholder;
  QPixmap m_pixmap;
  Camera m_camera;
  QPointF m_lastMousePos;
  bool m_panning = false;
};
