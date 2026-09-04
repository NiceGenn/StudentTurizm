/* Фильтры каталога для статической витрины на GitHub Pages.

   В полной версии фильтрацию делает Django: условия уходят на сервер в
   адресе запроса. Статический хостинг адрес запроса игнорирует и всегда
   отдаёт один и тот же файл, поэтому здесь та же выборка выполняется в
   браузере по данным, которые уже лежат в карточках (data-category,
   data-village, data-season, data-text). */

(function () {
  "use strict";

  var form = document.getElementById("catalog-filters");
  var grid = document.getElementById("catalog-grid");
  if (!form || !grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-attraction-card]"));
  var empty = document.getElementById("catalog-empty");
  var total = document.getElementById("catalog-total");

  function value(name) {
    var field = form.elements[name];
    return field ? field.value.trim().toLowerCase() : "";
  }

  function apply() {
    var query = value("q");
    var category = value("category");
    var village = value("village");
    var season = value("season");
    var shown = 0;

    cards.forEach(function (wrapper) {
      var card = wrapper.querySelector(".card-object");
      var data = card ? card.dataset : {};
      var ok =
        (!category || data.category === category) &&
        (!village || data.village === village) &&
        (!season || data.season === season) &&
        (!query || (data.text || "").indexOf(query) !== -1);

      wrapper.classList.toggle("d-none", !ok);
      if (ok) shown += 1;
    });

    if (empty) empty.classList.toggle("d-none", shown !== 0);
    if (total) {
      var label = shown === 1 ? total.dataset.one : total.dataset.many;
      total.textContent = shown === 1 ? label : label + ": " + shown;
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    apply();
  });

  ["category", "village", "season"].forEach(function (name) {
    var field = form.elements[name];
    if (field) field.addEventListener("change", apply);
  });

  var search = form.elements.q;
  if (search) search.addEventListener("input", apply);

  // Кнопка «Сбросить» в витрине очищает форму, а не ведёт на сервер.
  var reset = form.querySelector("a.btn-link");
  if (reset) {
    reset.addEventListener("click", function (event) {
      event.preventDefault();
      form.reset();
      apply();
    });
  }
})();
