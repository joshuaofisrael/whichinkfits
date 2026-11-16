(function () {
  var KEY = "wif-consent";
  var banner = document.getElementById("consent-banner");
  var loader = document.getElementById("ga4-loader");
  var src = loader ? (loader.getAttribute("data-ga4-src") || "") : "";
  var match = src.match(/[?&]id=(G-[A-Za-z0-9]+)/);
  var gaId = match ? match[1] : "";

  function gtag() {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(arguments);
  }
  if (typeof window.gtag !== "function") window.gtag = gtag;

  function loadGa() {
    if (!gaId || window.__wifGaLoaded) return;
    window.__wifGaLoaded = true;
    window.gtag("consent", "update", { analytics_storage: "granted" });
    var s = document.createElement("script");
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
    window.gtag("js", new Date());
    window.gtag("config", gaId);
  }

  function hide() {
    if (!banner) return;
    var back = document.getElementById("cookie-settings");
    banner.hidden = true;
    if (back && banner.contains(document.activeElement)) back.focus();
  }

  function choose(value) {
    try { localStorage.setItem(KEY, value); } catch (e) {}
    if (value === "granted") loadGa();
    else {
      window.gtag("consent", "update", {
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied",
        analytics_storage: "denied"
      });
    }
    hide();
  }

  function openBanner() {
    if (!banner) return;
    banner.hidden = false;
    var accept = document.getElementById("consent-accept");
    if (accept) accept.focus();
  }

  var saved = "";
  try { saved = localStorage.getItem(KEY) || ""; } catch (e) {}
  if (saved === "granted") loadGa();
  else if (!saved && banner) banner.hidden = false;

  var acceptBtn = document.getElementById("consent-accept");
  var rejectBtn = document.getElementById("consent-reject");
  if (acceptBtn) acceptBtn.addEventListener("click", function () { choose("granted"); });
  if (rejectBtn) rejectBtn.addEventListener("click", function () { choose("denied"); });
  var settings = document.getElementById("cookie-settings");
  if (settings) settings.addEventListener("click", function (e) {
    e.preventDefault();
    openBanner();
  });
})();
