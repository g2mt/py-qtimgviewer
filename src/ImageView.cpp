#include <imgviewer/ImageView.h>
#include <QDragEnterEvent>
#include <QDragMoveEvent>
#include <QDropEvent>
#include <QMimeData>
#include <QMouseEvent>
#include <QPainter>
#include <QResizeEvent>
#include <QUrl>
#include <QVBoxLayout>
#include <QWheelEvent>
#include <algorithm>

namespace {
// Multiplicative zoom factor applied per wheel "notch" (120 eighths of a
// degree, the standard step on most mice).
constexpr float kZoomStepPerNotch = 1.15f;
constexpr float kMinZoom = 0.01f;
constexpr float kMaxZoom = 100.0f;
} // namespace

ImageView::ImageView(QWidget *parent) : QFrame(parent) {
  QVBoxLayout *layout = new QVBoxLayout(this);
  layout->setContentsMargins(0, 0, 0, 0);

  m_placeholder = new QLabel("Select an image...");
  m_placeholder->setAlignment(Qt::AlignCenter);
  layout->addWidget(m_placeholder);

  setStyleSheet("background-color: #333; color: #eee;");
  setAcceptDrops(true);
}

void ImageView::setImage(const QString &path) {
  m_pixmap = QPixmap(path);
  resetCamera();
  updateImageDisplay();
}

bool ImageView::hasImage() const { return !m_pixmap.isNull(); }

void ImageView::resetCamera() {
  if (!hasImage()) {
    m_camera = Camera{};
    return;
  }

  // Fit the image to the widget width and center it vertically. The image's
  // top-left corner (0, 0) is taken as the camera target so `offset` is the
  // on-screen position of that corner.
  const float fitZoom =
      m_pixmap.width() > 0 ? float(width()) / float(m_pixmap.width()) : 1.0f;
  m_camera.zoom = fitZoom > 0.0f ? fitZoom : 1.0f;
  m_camera.imageTarget = QPointF(0.0, 0.0);
  m_camera.offset =
      QPointF(0.0, (height() - m_pixmap.height() * m_camera.zoom) / 2.0);
}

void ImageView::updateImageDisplay() {
  m_placeholder->setVisible(!hasImage());
  if (hasImage()) {
    m_placeholder->hide();
  }
  update();
}

void ImageView::paintEvent(QPaintEvent *event) {
  QFrame::paintEvent(event);
  if (!hasImage())
    return;

  QPainter painter(this);
  painter.setRenderHint(QPainter::SmoothPixmapTransform, true);

  // The destination rectangle is the image's bounds mapped through the camera.
  const QPointF topLeft = m_camera.imageToScreen(QPointF(0.0, 0.0));
  const QSizeF dstSize(m_pixmap.width() * m_camera.zoom,
                       m_pixmap.height() * m_camera.zoom);
  painter.drawPixmap(QRectF(topLeft, dstSize), m_pixmap,
                     QRectF(m_pixmap.rect()));
}

void ImageView::resizeEvent(QResizeEvent *event) {
  QFrame::resizeEvent(event);
  if (hasImage())
    update();
}

void ImageView::dragEnterEvent(QDragEnterEvent *event) {
  if (event->mimeData()->hasUrls()) {
    for (const QUrl &url : event->mimeData()->urls()) {
      if (url.isLocalFile()) {
        QString path = url.toLocalFile();
        if (path.endsWith(".png", Qt::CaseInsensitive) ||
            path.endsWith(".jpg", Qt::CaseInsensitive) ||
            path.endsWith(".jpeg", Qt::CaseInsensitive) ||
            path.endsWith(".bmp", Qt::CaseInsensitive) ||
            path.endsWith(".gif", Qt::CaseInsensitive) ||
            path.endsWith(".webp", Qt::CaseInsensitive) ||
            path.endsWith(".tiff", Qt::CaseInsensitive) ||
            path.endsWith(".tif", Qt::CaseInsensitive)) {
          event->acceptProposedAction();
          return;
        }
      }
    }
  }
}

void ImageView::dragMoveEvent(QDragMoveEvent *event) {
  event->acceptProposedAction();
}

void ImageView::dropEvent(QDropEvent *event) {
  if (event->mimeData()->hasUrls()) {
    for (const QUrl &url : event->mimeData()->urls()) {
      if (url.isLocalFile()) {
        setImage(url.toLocalFile());
        return;
      }
    }
  }
}

void ImageView::mousePressEvent(QMouseEvent *event) {
  if (hasImage() && event->button() == Qt::LeftButton) {
    m_panning = true;
    m_lastMousePos = event->position();
    setCursor(Qt::ClosedHandCursor);
  }
  QFrame::mousePressEvent(event);
}

void ImageView::mouseMoveEvent(QMouseEvent *event) {
  if (m_panning) {
    const QPointF delta = event->position() - m_lastMousePos;
    m_camera.offset += delta;
    m_lastMousePos = event->position();
    update();
  }
  QFrame::mouseMoveEvent(event);
}

void ImageView::mouseReleaseEvent(QMouseEvent *event) {
  if (m_panning && event->button() == Qt::LeftButton) {
    m_panning = false;
    setCursor(Qt::ArrowCursor);
  }
  QFrame::mouseReleaseEvent(event);
}

void ImageView::wheelEvent(QWheelEvent *event) {
  if (!hasImage()) {
    QFrame::wheelEvent(event);
    return;
  }

  // Zoom around the cursor by re-anchoring the camera: the image point
  // currently under the cursor is recorded, the zoom is updated, and the
  // camera is configured so that same image point still lands at the cursor.
  const QPointF cursor = event->position();
  const QPointF imagePointUnderCursor = m_camera.screenToImage(cursor);

  const float notches = event->angleDelta().y() / 120.0f;
  const float factor = std::pow(kZoomStepPerNotch, notches);
  m_camera.zoom = std::clamp(m_camera.zoom * factor, kMinZoom, kMaxZoom);

  m_camera.imageTarget = imagePointUnderCursor;
  m_camera.offset = cursor;

  update();
  event->accept();
}
