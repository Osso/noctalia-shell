// Fixture transport for real QML XMLHttpRequest; never opens a network
// connection.
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QQmlEngine>
#include <QQmlExtensionPlugin>
#include <QQmlNetworkAccessManagerFactory>
#include <QTimer>

class FixtureReply final : public QNetworkReply {
public:
  FixtureReply(const QNetworkRequest &request, QObject *parent)
      : QNetworkReply(parent) {
    setRequest(request);
    setUrl(request.url());
    const bool geocode = request.url().host() == "assets.noctalia.dev";
    QFile fixture(qEnvironmentVariable("LOCATION_FIXTURES") +
                  (geocode ? "/geocode.json" : "/weather.json"));
    if (!fixture.open(QIODevice::ReadOnly))
      qFatal("Cannot read location provider fixture");
    const auto response = QJsonDocument::fromJson(fixture.readAll()).object();
    body = response.value("body").toString().toUtf8();
    setAttribute(QNetworkRequest::HttpStatusCodeAttribute,
                 response.value("status").toInt());
    setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    open(QIODevice::ReadOnly);
    QTimer::singleShot(10, this, [this]() {
      setFinished(true);
      emit readyRead();
      emit finished();
    });
  }
  void abort() override {}
  qint64 bytesAvailable() const override {
    return body.size() - offset + QNetworkReply::bytesAvailable();
  }

protected:
  qint64 readData(char *destination, qint64 maximum) override {
    const auto count = qMin(maximum, body.size() - offset);
    if (count == 0)
      return -1;
    memcpy(destination, body.constData() + offset, count);
    offset += count;
    return count;
  }

private:
  QByteArray body;
  qint64 offset = 0;
};

class FixtureManager final : public QNetworkAccessManager {
public:
  using QNetworkAccessManager::QNetworkAccessManager;

protected:
  QNetworkReply *createRequest(Operation operation,
                               const QNetworkRequest &request,
                               QIODevice *) override {
    if (operation != GetOperation ||
        (request.url().host() != "assets.noctalia.dev" &&
         request.url().host() != "api.open-meteo.com"))
      qFatal("Unexpected location provider request");
    QFile requests(qEnvironmentVariable("LOCATION_FIXTURES") + "/requests.txt");
    if (!requests.open(QIODevice::WriteOnly | QIODevice::Append))
      qFatal("Cannot write location request evidence");
    requests.write(request.url().toEncoded() + '\n');
    return new FixtureReply(request, this);
  }
};

class FixtureFactory final : public QQmlNetworkAccessManagerFactory {
public:
  QNetworkAccessManager *create(QObject *parent) override {
    return new FixtureManager(parent);
  }
};

class LocationNetworkPlugin final : public QQmlExtensionPlugin {
  Q_OBJECT
  Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
  void registerTypes(const char *uri) override { qmlRegisterModule(uri, 1, 0); }
  void initializeEngine(QQmlEngine *engine, const char *) override {
    engine->setNetworkAccessManagerFactory(&factory);
  }

private:
  FixtureFactory factory;
};

#include "LocationNetworkPlugin.moc"
