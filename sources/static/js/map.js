/* Карта портала на Leaflet + тайлы OpenStreetMap.
   Ключ и регистрация не нужны, обязательна только атрибуция. */

(function (global) {
  "use strict";

  var TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  var ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

  function baseMap(element, center, zoom) {
    var map = L.map(element).setView(center, zoom);
    L.tileLayer(TILES, { maxZoom: 18, attribution: ATTRIBUTION }).addTo(map);
    return map;
  }

  /** Маркер-«капля» в цвете категории с эмодзи внутри. */
  function pin(color, icon) {
    return L.divIcon({
      className: "",
      html:
        '<div class="map-pin" style="background:' + (color || "#17624a") + '">' +
        "<span>" + (icon || "•") + "</span></div>",
      iconSize: [30, 30],
      iconAnchor: [15, 30],
      popupAnchor: [0, -28],
    });
  }

  function popupHtml(item) {
    var html = '<span class="popup-title">' + item.title + "</span>";
    if (item.village) {
      html += '<span class="text-muted">' + item.village + "</span><br>";
    }
    if (item.status !== "active") {
      html += "<em>" + item.status_label + "</em><br>";
    }
    if (item.short) {
      html += item.short + "<br>";
    }
    return html + '<a href="' + item.url + '">Подробнее →</a>';
  }

  var portalMap = {
    /** Одна точка: карточка объекта. */
    single: function (element) {
      if (!element) return;
      var lat = parseFloat(element.dataset.lat);
      var lng = parseFloat(element.dataset.lng);
      var map = baseMap(element, [lat, lng], 12);
      L.marker([lat, lng], { icon: pin(element.dataset.color, element.dataset.icon) })
        .addTo(map)
        .bindPopup(element.dataset.title);
    },

    /** Все объекты каталога с фильтром по категориям. */
    all: function (element, options) {
      if (!element) return;
      options = options || {};
      var map = baseMap(element, options.center, options.zoom);
      var layers = {};
      var bounds = [];

      fetch(options.url)
        .then(function (response) { return response.json(); })
        .then(function (data) {
          data.items.forEach(function (item) {
            var marker = L.marker([item.lat, item.lng], { icon: pin(item.color, item.icon) })
              .bindPopup(popupHtml(item));
            if (!layers[item.category]) {
              layers[item.category] = L.layerGroup().addTo(map);
            }
            marker.addTo(layers[item.category]);
            bounds.push([item.lat, item.lng]);
          });

          if (bounds.length) {
            map.fitBounds(bounds, { padding: [30, 30] });
          }

          document.querySelectorAll("[data-category-toggle]").forEach(function (input) {
            input.addEventListener("change", function () {
              var layer = layers[input.dataset.categoryToggle];
              if (!layer) return;
              if (input.checked) {
                map.addLayer(layer);
              } else {
                map.removeLayer(layer);
              }
            });
          });
        })
        .catch(function () {
          element.innerHTML =
            '<div class="p-4 text-center text-muted">Не удалось загрузить данные карты.</div>';
        });
    },

    /** Точки одного маршрута, соединённые линией в порядке следования. */
    route: function (element, options) {
      if (!element) return;
      options = options || {};
      var map = baseMap(element, options.center, options.zoom);
      var line = [];

      (options.points || []).forEach(function (point, index) {
        L.marker([point.lat, point.lng], { icon: pin(point.color, String(index + 1)) })
          .addTo(map)
          .bindPopup('<span class="popup-title">' + point.title + "</span>" +
                     '<a href="' + point.url + '">Подробнее →</a>');
        line.push([point.lat, point.lng]);
      });

      if (line.length > 1) {
        L.polyline(line, { color: "#17624a", weight: 3, dashArray: "6 6" }).addTo(map);
      }
      if (line.length) {
        map.fitBounds(line, { padding: [40, 40] });
      }
    },
  };

  global.portalMap = portalMap;
})(window);
