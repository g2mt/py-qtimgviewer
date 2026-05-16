#include <imgviewer/ImageDetailList.h>
#include <imgviewer/ImageDetailModel.h>

#include <QPainter>
#include <QPixmap>
#include <QStyledItemDelegate>

namespace {

constexpr int kRowHeight = 100;
constexpr int kThumbnailMargin = 4;
constexpr int kThumbnailBox = kRowHeight - 2 * kThumbnailMargin;

// Renders each row as a fixed-height card: thumbnail on the left, file name
// on the right. Uniform sizeHint lets QListView use setUniformItemSizes().
class ImageDetailDelegate : public QStyledItemDelegate {
public:
  using QStyledItemDelegate::QStyledItemDelegate;

  QSize sizeHint(const QStyleOptionViewItem &option,
                 const QModelIndex &index) const override {
    Q_UNUSED(index);
    return QSize(option.rect.width(), kRowHeight);
  }

  void paint(QPainter *painter, const QStyleOptionViewItem &option,
             const QModelIndex &index) const override {
    painter->save();
    if (option.state & QStyle::State_Selected)
      painter->fillRect(option.rect, option.palette.highlight());

    const QRect thumbBox(option.rect.left() + kThumbnailMargin,
                         option.rect.top() + kThumbnailMargin, kThumbnailBox,
                         kThumbnailBox);
    const QPixmap thumb =
        index.data(ImageDetailModel::ThumbnailRole).value<QPixmap>();
    if (!thumb.isNull()) {
      QSize scaled = thumb.size().scaled(thumbBox.size(), Qt::KeepAspectRatio);
      QRect dst(QPoint(0, 0), scaled);
      dst.moveCenter(thumbBox.center());
      painter->drawPixmap(dst, thumb);
    } else {
      painter->setPen(option.palette.mid().color());
      painter->drawRect(thumbBox);
    }

    const int textLeft = thumbBox.right() + kThumbnailMargin * 2;
    const QRect textRect(textLeft, option.rect.top(),
                         option.rect.right() - textLeft - kThumbnailMargin,
                         option.rect.height());
    const QString name = index.data(ImageDetailModel::FileNameRole).toString();
    painter->setPen((option.state & QStyle::State_Selected)
                        ? option.palette.highlightedText().color()
                        : option.palette.text().color());
    const QString elided =
        option.fontMetrics.elidedText(name, Qt::ElideMiddle, textRect.width());
    painter->drawText(textRect, Qt::AlignVCenter | Qt::AlignLeft, elided);

    painter->restore();
  }
};

} // namespace

ImageDetailList::ImageDetailList(Filter *filter, QWidget *parent)
    : QListView(parent) {
  setViewMode(QListView::ListMode);
  setResizeMode(QListView::Adjust);
  setLayoutMode(QListView::Batched);
  setMovement(QListView::Static);
  setUniformItemSizes(true);
  setSelectionMode(QAbstractItemView::SingleSelection);
  setItemDelegate(new ImageDetailDelegate(this));

  m_model = new ImageDetailModel(filter, this);
  setModel(m_model);

  connect(this, &QListView::clicked, this, &ImageDetailList::onClicked);
}

void ImageDetailList::onClicked(const QModelIndex &index) {
  const QString path = index.data(ImageDetailModel::FilePathRole).toString();
  if (!path.isEmpty())
    emit imageActivated(path);
}
