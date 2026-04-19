/**
 * feedback-widget.js — Floating feedback widget
 * Usage: <script src="..." data-api="http://localhost:3333" data-project="my-app"></script>
 */
(function () {
  'use strict';

  var script = document.currentScript || (function () {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  var API_URL = (script && script.dataset.api) || 'http://localhost:3333';
  var PROJECT = (script && script.dataset.project) || window.location.hostname;
  var AUTO_ERRORS = (script && script.dataset.autoErrors) !== 'false';

  var TYPES = [
    { id: 'bug',        emoji: '🐛', label: 'Bug' },
    { id: 'feature',    emoji: '✨', label: 'Feature' },
    { id: 'suggestion', emoji: '💡', label: 'Suggestion' },
  ];

  // ── Styles ──────────────────────────────────────────────────────────────
  var CSS = `
    #fb-widget-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 99998;
      width: 52px; height: 52px; border-radius: 50%;
      background: #4f46e5; color: #fff; border: none;
      font-size: 22px; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,.25);
      display: flex; align-items: center; justify-content: center;
      transition: transform .15s, background .15s;
    }
    #fb-widget-btn:hover { background: #4338ca; transform: scale(1.08); }
    #fb-panel {
      position: fixed; bottom: 88px; right: 24px; z-index: 99999;
      width: 320px; background: #fff; border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,.18); padding: 20px;
      font-family: system-ui, sans-serif; font-size: 14px; color: #111;
      display: none; flex-direction: column; gap: 12px;
    }
    #fb-panel.fb-open { display: flex; }
    #fb-panel h3 { margin: 0; font-size: 15px; font-weight: 600; }
    #fb-type-row { display: flex; gap: 8px; }
    .fb-type-btn {
      flex: 1; padding: 7px 4px; border: 2px solid #e5e7eb; border-radius: 8px;
      background: #fff; cursor: pointer; font-size: 12px; text-align: center;
      transition: border-color .1s, background .1s;
    }
    .fb-type-btn:hover, .fb-type-btn.active {
      border-color: #4f46e5; background: #eef2ff;
    }
    .fb-type-btn span { display: block; font-size: 18px; }
    #fb-msg {
      width: 100%; box-sizing: border-box; padding: 8px 10px;
      border: 1.5px solid #e5e7eb; border-radius: 8px; resize: vertical;
      min-height: 80px; font-size: 13px; font-family: inherit;
      outline: none; transition: border-color .1s;
    }
    #fb-msg:focus { border-color: #4f46e5; }
    #fb-submit {
      padding: 9px; background: #4f46e5; color: #fff; border: none;
      border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600;
      transition: background .15s;
    }
    #fb-submit:hover { background: #4338ca; }
    #fb-submit:disabled { background: #a5b4fc; cursor: not-allowed; }
    #fb-status { font-size: 12px; text-align: center; min-height: 16px; color: #6b7280; }
    #fb-status.ok { color: #059669; }
    #fb-status.err { color: #dc2626; }
    #fb-close-btn {
      position: absolute; top: 12px; right: 14px;
      background: none; border: none; font-size: 18px; cursor: pointer; color: #9ca3af;
      line-height: 1;
    }
    #fb-close-btn:hover { color: #111; }
    #fb-error-toast {
      position: fixed; bottom: 88px; right: 24px; z-index: 99997;
      width: 300px; background: #fef2f2; border: 1.5px solid #fca5a5;
      border-radius: 10px; padding: 12px 16px; font-family: system-ui, sans-serif;
      font-size: 13px; color: #991b1b; display: none; flex-direction: column; gap: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,.1);
    }
    #fb-error-toast.fb-open { display: flex; }
    #fb-error-toast strong { font-size: 13px; }
    #fb-toast-btns { display: flex; gap: 8px; }
    #fb-toast-btns button {
      flex: 1; padding: 5px; border-radius: 6px; border: none;
      cursor: pointer; font-size: 12px; font-weight: 600;
    }
    #fb-toast-report { background: #dc2626; color: #fff; }
    #fb-toast-dismiss { background: #fee2e2; color: #991b1b; }
  `;

  // ── DOM ──────────────────────────────────────────────────────────────────
  function inject() {
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    // Toggle button
    var btn = document.createElement('button');
    btn.id = 'fb-widget-btn';
    btn.title = 'Feedback';
    btn.textContent = '💬';
    document.body.appendChild(btn);

    // Panel
    var panel = document.createElement('div');
    panel.id = 'fb-panel';
    panel.innerHTML = `
      <button id="fb-close-btn" title="Fermer">×</button>
      <h3>Envoyer un retour</h3>
      <div id="fb-type-row">
        ${TYPES.map(t => `<button class="fb-type-btn" data-type="${t.id}"><span>${t.emoji}</span>${t.label}</button>`).join('')}
      </div>
      <textarea id="fb-msg" placeholder="Décris le problème ou l'idée…"></textarea>
      <button id="fb-submit">Envoyer</button>
      <div id="fb-status"></div>
    `;
    document.body.appendChild(panel);

    // Error toast
    var toast = document.createElement('div');
    toast.id = 'fb-error-toast';
    toast.innerHTML = `
      <strong>🔴 Erreur JS détectée</strong>
      <div id="fb-toast-msg"></div>
      <div id="fb-toast-btns">
        <button id="fb-toast-report">Signaler</button>
        <button id="fb-toast-dismiss">Ignorer</button>
      </div>
    `;
    document.body.appendChild(toast);

    bindEvents(btn, panel, toast);
  }

  // ── State ────────────────────────────────────────────────────────────────
  var selectedType = 'bug';
  var pendingError = null;

  function bindEvents(btn, panel, toast) {
    // Toggle panel
    btn.addEventListener('click', function () {
      var isOpen = panel.classList.contains('fb-open');
      panel.classList.toggle('fb-open', !isOpen);
      toast.classList.remove('fb-open');
      if (!isOpen) setType(selectedType);
    });

    document.getElementById('fb-close-btn').addEventListener('click', function () {
      panel.classList.remove('fb-open');
    });

    // Type selection
    panel.querySelectorAll('.fb-type-btn').forEach(function (b) {
      b.addEventListener('click', function () { setType(b.dataset.type); });
    });

    // Submit
    document.getElementById('fb-submit').addEventListener('click', submitFeedback);

    // Error toast buttons
    document.getElementById('fb-toast-report').addEventListener('click', function () {
      if (pendingError) {
        sendFeedback('error', pendingError.message, pendingError.stack);
        pendingError = null;
      }
      toast.classList.remove('fb-open');
    });

    document.getElementById('fb-toast-dismiss').addEventListener('click', function () {
      toast.classList.remove('fb-open');
      pendingError = null;
    });
  }

  function setType(type) {
    selectedType = type;
    document.querySelectorAll('.fb-type-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.type === type);
    });
  }

  function submitFeedback() {
    var msg = document.getElementById('fb-msg').value.trim();
    var status = document.getElementById('fb-status');
    var submitBtn = document.getElementById('fb-submit');

    if (!msg) {
      status.textContent = 'Merci d\'écrire un message.';
      status.className = 'err';
      return;
    }

    submitBtn.disabled = true;
    status.textContent = 'Envoi…';
    status.className = '';

    sendFeedback(selectedType, msg, null, function (ok) {
      submitBtn.disabled = false;
      if (ok) {
        status.textContent = 'Merci ! Retour enregistré.';
        status.className = 'ok';
        document.getElementById('fb-msg').value = '';
        setTimeout(function () {
          document.getElementById('fb-panel').classList.remove('fb-open');
          status.textContent = '';
          status.className = '';
        }, 1800);
      } else {
        status.textContent = 'Erreur lors de l\'envoi.';
        status.className = 'err';
      }
    });
  }

  function sendFeedback(type, message, stack, callback) {
    var body = {
      type: type,
      message: message,
      url: window.location.href,
      project: PROJECT,
      userAgent: navigator.userAgent,
    };
    if (stack) body.stack = stack;

    fetch(API_URL + '/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (r) { callback && callback(r.ok); })
      .catch(function () { callback && callback(false); });
  }

  // ── Automatic JS error capture ───────────────────────────────────────────
  function showErrorToast(message, stack) {
    pendingError = { message: message, stack: stack };
    var toastMsg = document.getElementById('fb-toast-msg');
    if (toastMsg) {
      toastMsg.textContent = message.slice(0, 120);
      document.getElementById('fb-error-toast').classList.add('fb-open');
      // Auto-dismiss after 12s if not acted on
      setTimeout(function () {
        if (pendingError) {
          document.getElementById('fb-error-toast').classList.remove('fb-open');
          pendingError = null;
        }
      }, 12000);
    }
  }

  if (AUTO_ERRORS) {
    window.addEventListener('error', function (e) {
      var msg = e.message || 'Unknown error';
      var stack = e.error && e.error.stack ? e.error.stack : (e.filename + ':' + e.lineno);
      // Ignore cross-origin script errors (no useful info)
      if (msg === 'Script error.' && !stack) return;
      showErrorToast(msg, stack);
    });

    window.addEventListener('unhandledrejection', function (e) {
      var msg = 'Unhandled Promise rejection';
      var stack = '';
      if (e.reason) {
        msg = (e.reason.message || String(e.reason)).slice(0, 200);
        stack = e.reason.stack || '';
      }
      showErrorToast(msg, stack);
    });
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
