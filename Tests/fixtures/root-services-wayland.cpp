// Inert layer-shell attachment: IPC's untouched Loader can compile in QtTest.
#include <QQmlExtensionPlugin>
#include <qqml.h>

class LayerAttachment : public QObject {
  Q_OBJECT
  Q_PROPERTY(int exclusionMode MEMBER exclusionMode)
public:
  using QObject::QObject;
  int exclusionMode = 0;
};

class FixtureLayershell : public QObject {
  Q_OBJECT
public:
  static LayerAttachment *qmlAttachedProperties(QObject *object) {
    return new LayerAttachment(object);
  }
};
QML_DECLARE_TYPEINFO(FixtureLayershell, QML_HAS_ATTACHED_PROPERTIES)

class FixtureExclusionMode : public QObject {
  Q_OBJECT
public:
  enum Mode { Ignore };
  Q_ENUM(Mode)
};

class FixtureWaylandPlugin : public QQmlExtensionPlugin {
  Q_OBJECT
  Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
  void registerTypes(const char *uri) override {
    qmlRegisterUncreatableType<FixtureLayershell>(uri, 1, 0, "WlrLayershell",
                                                  "Attached only");
    qmlRegisterUncreatableType<FixtureExclusionMode>(uri, 1, 0, "ExclusionMode",
                                                     "Enum only");
  }
};

#include "root-services-wayland.moc"
