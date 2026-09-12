// fretladder: www.fretladder.com answers with a 301 to the apex, path and query kept.
// A CloudFront Function on the distribution's viewer-request (tools/www_redirect.sh
// creates, tests, publishes and attaches it). Runtime cloudfront-js-2.0.
function handler(event) {
  var request = event.request;
  var host = request.headers.host && request.headers.host.value;
  if (!host || host.indexOf('www.') !== 0) {
    return request;
  }
  var qs = '';
  var keys = Object.keys(request.querystring);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i], entry = request.querystring[k];
    var values = entry.multiValue ? entry.multiValue : [entry];
    for (var j = 0; j < values.length; j++) {
      qs += (qs ? '&' : '?') + encodeURIComponent(k) + '=' + encodeURIComponent(values[j].value);
    }
  }
  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: { location: { value: 'https://' + host.slice(4) + request.uri + qs } }
  };
}
