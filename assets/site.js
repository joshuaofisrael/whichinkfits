(function () {
  var input = document.getElementById("q");
  var out = document.getElementById("search-results");
  if (!input || !out || !window.INK_INDEX) return;
  function show() {
    var q = input.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
    out.innerHTML = "";
    if (q.length < 2) { out.hidden = true; return; }
    var hits = window.INK_INDEX.filter(function (r) { return r.k.indexOf(q) >= 0; }).slice(0, 24);
    out.hidden = false;
    if (!hits.length) {
      var li = document.createElement("li");
      li.textContent = "No matching model or cartridge in this guide. Read the number on the printer and on the box, then check the manufacturer page.";
      out.appendChild(li);
      return;
    }
    hits.forEach(function (r) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = r.u;
      a.textContent = r.n;
      li.appendChild(a);
      var b = document.createElement("span");
      b.className = "badge";
      b.textContent = r.t;
      li.appendChild(b);
      out.appendChild(li);
    });
  }
  input.addEventListener("input", show);
  var form = document.getElementById("finder");
  if (form) form.addEventListener("submit", function (e) { e.preventDefault(); show(); });
})();
