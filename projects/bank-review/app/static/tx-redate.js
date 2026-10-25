// Re-datation d'une transaction (virement de compensation rattaché à un autre mois/exercice).
// Toute cellule <td class="tx-date" data-txid data-date data-orig> est rendue ici : date courante,
// rappel de la date banque si la ligne a été déplacée, bouton ✎ d'édition.
(function () {
  function escAttr(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }

  function render(td) {
    const d = td.dataset.date, orig = td.dataset.orig;
    td.innerHTML =
      `<span class="tx-date-val${orig ? ' tx-date-moved' : ''}">${escAttr(d)}</span>` +
      (orig ? `<div class="tx-date-orig" title="Date d'origine sur le relevé bancaire">banque : ${escAttr(orig)}</div>` : '') +
      `<button type="button" class="btn-redate" title="Changer la date de la ligne">✎</button>`;
    td.querySelector('.btn-redate').onclick = (e) => { e.stopPropagation(); edit(td); };
  }

  function edit(td) {
    const d = td.dataset.date, orig = td.dataset.orig;
    td.innerHTML =
      `<input type="date" class="tx-date-input" value="${escAttr(d)}">` +
      `<div class="tx-date-actions">` +
      `<button type="button" class="btn-redate-ok" title="Enregistrer">✓</button>` +
      `<button type="button" class="btn-redate-cancel" title="Annuler">✕</button>` +
      (orig ? `<button type="button" class="btn-redate-reset" title="Revenir à la date banque">↺ ${escAttr(orig)}</button>` : '') +
      `</div>`;
    const input = td.querySelector('input');
    td.onclick = (e) => e.stopPropagation();
    td.querySelector('.btn-redate-cancel').onclick = () => render(td);
    td.querySelector('.btn-redate-ok').onclick = () => save(td, input.value);
    const reset = td.querySelector('.btn-redate-reset');
    if (reset) reset.onclick = () => save(td, orig);
    input.focus();
  }

  async function save(td, value) {
    if (!value || value === td.dataset.date) { render(td); return; }
    const res = await fetch(`/api/transactions/${td.dataset.txid}/redate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date_op: value }),
    });
    if (!res.ok) { alert('Échec du changement de date.'); render(td); return; }
    // La ligne change de mois (et peut-être d'exercice) : les totaux se recalculent au rechargement.
    location.reload();
  }

  window.enhanceTxDates = function (root) {
    (root || document).querySelectorAll('td.tx-date').forEach(render);
  };
  document.addEventListener('DOMContentLoaded', () => window.enhanceTxDates());
})();
