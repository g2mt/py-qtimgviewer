#include <imgviewer/TagList.h>
#include <imgviewer/TagListContainer.h>

#include <QLineEdit>
#include <QTreeWidgetItem>
#include <QVBoxLayout>

TagListContainer::TagListContainer(Filter *filter, QWidget *parent)
    : QWidget(parent) {
  QVBoxLayout *layout = new QVBoxLayout(this);
  layout->setContentsMargins(0, 0, 0, 0);
  layout->setSpacing(0);

  m_tagList = new TagList(filter);
  layout->addWidget(m_tagList, 1);

  m_filterInput = new QLineEdit();
  m_filterInput->setPlaceholderText("Search tags...");
  m_filterInput->setClearButtonEnabled(true);
  layout->addWidget(m_filterInput);

  connect(m_filterInput, &QLineEdit::textChanged, this,
          &TagListContainer::filterTags);
}

void TagListContainer::filterTags(const QString &text) {
  for (int i = 0; i < m_tagList->topLevelItemCount(); ++i) {
    QTreeWidgetItem *item = m_tagList->topLevelItem(i);
    bool visible = text.isEmpty() ||
                   item->text(1).contains(text, Qt::CaseInsensitive);
    item->setHidden(!visible);
  }
}
