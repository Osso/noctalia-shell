import QtQuick
pragma Singleton

QtObject {
    id: transport

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
                request.url = url;
            },
            "send": function() {
                transport.requests.push(request);
            }
        };
        return request;
    }

    function respond(index, status, payload) {
        const request = transport.requests[index];
        request.status = status;
        request.responseText = typeof payload === "string" ? payload : JSON.stringify(payload);
        request.readyState = transport.done;
        request.onreadystatechange();
    }

    function reset() {
        transport.requests = [];
    }

}
