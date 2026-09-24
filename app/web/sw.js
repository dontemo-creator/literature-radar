/* Service worker: keeps the app shell installable and makes the last results
 * readable with no connection.
 *
 * Note: browsers only register a service worker on a secure origin, which
 * means localhost works but a plain-HTTP LAN address (http://192.168.x.x)
 * does not.  Registration failure there is expected and harmless -- iOS still
 * honours the manifest for "Add to Home Screen", so the app opens standalone;
 * it just will not work offline.
 */
'use strict';

var VERSION = 'literature-radar-v9';
var SHELL = [
  '/',
  '/static/styles.css',
  '/static/app.js',
  '/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/apple-touch-icon.png'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(VERSION)
      .then(function (c) { return c.addAll(SHELL); })
      .catch(function () { /* a missing asset must not block install */ })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        return k === VERSION ? null : caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Icons are immutable -- cache first is safe and saves a round trip.
  if (url.pathname.indexOf('/static/icons/') === 0) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          if (res && res.ok) {
            var copy = res.clone();
            caches.open(VERSION).then(function (c) { c.put(req, copy); });
          }
          return res;
        });
      })
    );
    return;
  }

  // Everything else -- the shell (HTML/CSS/JS) and the API -- is network
  // first, falling back to the cache when offline.  Cache first here would
  // serve a stale UI for a whole extra load after every update.
  e.respondWith(
    fetch(req).then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        if (url.pathname.indexOf('/api/') === 0) {
          return new Response(
            JSON.stringify({ error: 'offline', detail: '当前离线，且没有可用的缓存结果' }),
            { status: 503, headers: { 'Content-Type': 'application/json' } });
        }
        return caches.match('/');
      });
    })
  );
});
