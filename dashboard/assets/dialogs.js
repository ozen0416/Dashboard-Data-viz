// Ouverture / fermeture des fenêtres de détail (<dialog> natif).
// showModal() rend le reste de la page inerte, piège le focus et gère la touche Échap.
document.addEventListener("click", function (e) {
  var opener = e.target.closest("[data-dialog-open]");
  if (opener) {
    var dlg = document.getElementById(opener.getAttribute("data-dialog-open"));
    if (dlg && !dlg.open) {
      dlg._opener = opener;
      dlg.showModal();
      // Les graphiques rendus pendant que la fenêtre était cachée doivent reprendre leur largeur.
      requestAnimationFrame(function () {
        if (window.Plotly) {
          dlg.querySelectorAll(".js-plotly-plot").forEach(function (g) { window.Plotly.Plots.resize(g); });
        }
      });
    }
    return;
  }
  if (e.target.closest("[data-dialog-close]")) {
    e.target.closest("dialog").close();
    return;
  }
  // Clic sur le fond assombri (en dehors du contenu) : fermeture.
  if (e.target.tagName === "DIALOG") {
    e.target.close();
  }
});

// Au retour, le focus revient sur la vignette qui a ouvert la fenêtre.
document.addEventListener("close", function (e) {
  if (e.target._opener) { e.target._opener.focus(); }
}, true);
