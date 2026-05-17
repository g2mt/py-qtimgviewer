#pragma once
#include <QWidget>

class Filter;
class QLineEdit;
class TagList;

class TagListContainer : public QWidget {
  Q_OBJECT
public:
  TagListContainer(Filter *filter, QWidget *parent = nullptr);

private slots:
  void filterTags(const QString &text);

private:
  TagList *m_tagList;
  QLineEdit *m_filterInput;
};
