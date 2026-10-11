pragma Singleton
import QtQuick

QtObject {
    readonly property int done: 4
    property var requests: []

    function createRequest() {
        const request = {
            "readyState": 0,
            "status": 0,
            "responseText": "",
            "url": "",
            "onreadystatechange": null,
            "open": function(method, url) {
                this.url = url;
            },
            "send": function() {
                Transport.requests.push(this);
            }
        };
        return request;
    }

    function respond(index, status, payload) {
        const request = requests[index];
        request.status = status;
        request.responseText = typeof payload === "string" ? payload : JSON.stringify(payload);
        request.readyState = done;
        request.onreadystatechange();
    }

    function reset() {
        requests = [];
    }

}
