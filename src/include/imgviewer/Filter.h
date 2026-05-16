#pragma once
#include <QList>
#include <QObject>
#include <QString>

enum class SortBy { Name, DateCreated, DateModified };

class Filter : public QObject {
  Q_OBJECT
  QString _search;
  SortBy _sortBy = SortBy::Name;
  bool _descending = false;
  bool _naturalSort = false;
  QList<QString> _directories;
  QList<QString> _tags;

public:
signals:
  void changed();

public:
  QString search() const { return _search; }
  void setSearch(const QString &s) {
    if (_search != s) {
      _search = s;
      emit changed();
    }
  }

  SortBy sortBy() const { return _sortBy; }
  void setSortBy(SortBy s) {
    if (_sortBy != s) {
      _sortBy = s;
      emit changed();
    }
  }

  bool descending() const { return _descending; }
  void setDescending(bool d) {
    if (_descending != d) {
      _descending = d;
      emit changed();
    }
  }

  bool naturalSort() const { return _naturalSort; }
  void setNaturalSort(bool n) {
    if (_naturalSort != n) {
      _naturalSort = n;
      emit changed();
    }
  }

  const QList<QString> &directories() const { return _directories; }
  void setDirectories(const QList<QString> &d) {
    if (_directories != d) {
      _directories = d;
      emit changed();
    }
  }

  const QList<QString> &tags() const { return _tags; }
  void setTags(const QList<QString> &t) {
    if (_tags != t) {
      _tags = t;
      emit changed();
    }
  }
};
