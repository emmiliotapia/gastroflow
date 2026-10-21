/**
 * GastroFlow UI Notifications & Dialogs System
 * Componente moderno, reactivo y ad-hoc para reemplazar alert(), confirm() y prompt()
 * con estética premium (Glassmorphism, Tailwind, animaciones fluidas, sonido opcional).
 */

(function () {
  // Inyectar contenedor de Toasts si no existe
  let toastContainer = null;
  let modalContainer = null;

  function ensureContainers() {
    if (!document.getElementById('gf-toast-container')) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'gf-toast-container';
      toastContainer.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-2.5 pointer-events-none max-w-sm sm:max-w-md w-full px-4 sm:px-0';
      document.body.appendChild(toastContainer);
    } else {
      toastContainer = document.getElementById('gf-toast-container');
    }

    if (!document.getElementById('gf-modal-container')) {
      modalContainer = document.createElement('div');
      modalContainer.id = 'gf-modal-container';
      modalContainer.className = 'fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-200';
      document.body.appendChild(modalContainer);
    } else {
      modalContainer = document.getElementById('gf-modal-container');
    }
  }

  // Estilos CSS para animaciones
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gfToastIn {
      from { opacity: 0; transform: translateY(-12px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes gfToastOut {
      from { opacity: 1; transform: translateY(0) scale(1); }
      to { opacity: 0; transform: translateY(-12px) scale(0.96); }
    }
    .gf-toast-enter {
      animation: gfToastIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    .gf-toast-exit {
      animation: gfToastOut 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
  `;
  document.head.appendChild(style);

  // Helper para sonidos de notificación usando Web Audio API
  function playSound(type) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;
      if (type === 'success') {
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.12); // A5
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (type === 'error') {
        osc.frequency.setValueAtTime(260, now);
        osc.frequency.exponentialRampToValueAtTime(196, now + 0.15);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (type === 'bell') {
        osc.frequency.setValueAtTime(783.99, now); // G5
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      }
    } catch (e) {}
  }

  window.GastroNotify = {
    /**
     * Muestra una notificación Toast elegante flotante
     * @param {Object} opts - { title, message, type: 'success'|'error'|'info'|'warning'|'order', duration: 4000 }
     */
    show(opts) {
      ensureContainers();
      const {
        title = '',
        message = '',
        type = 'success',
        duration = 4500,
        action = null
      } = typeof opts === 'string' ? { message: opts } : opts;

      // Iconos e Identidad cromática ad-hoc
      const config = {
        success: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-emerald-500/30 text-emerald-600 dark:text-emerald-400',
          badgeBg: 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border-emerald-200/50',
          icon: 'check-circle-2',
          glow: 'shadow-lg shadow-emerald-500/10'
        },
        error: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-rose-500/30 text-rose-600 dark:text-rose-400',
          badgeBg: 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-200/50',
          icon: 'alert-triangle',
          glow: 'shadow-lg shadow-rose-500/10'
        },
        warning: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-amber-500/30 text-amber-600 dark:text-amber-400',
          badgeBg: 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border-amber-200/50',
          icon: 'alert-circle',
          glow: 'shadow-lg shadow-amber-500/10'
        },
        order: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-brand-500/40 text-brand-600 dark:text-brand-400',
          badgeBg: 'bg-orange-50 dark:bg-orange-950/60 text-brand-600 dark:text-brand-400 border-orange-200/50',
          icon: 'chef-hat',
          glow: 'shadow-xl shadow-brand-500/15'
        },
        bell: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-indigo-500/30 text-indigo-600 dark:text-indigo-400',
          badgeBg: 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border-indigo-200/50',
          icon: 'bell-ring',
          glow: 'shadow-lg shadow-indigo-500/10'
        },
        info: {
          bg: 'bg-white/95 dark:bg-slate-900/95 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200',
          badgeBg: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200',
          icon: 'info',
          glow: 'shadow-lg shadow-slate-900/5'
        }
      }[type] || config.info;

      const toast = document.createElement('div');
      toast.className = `pointer-events-auto flex items-start gap-3.5 p-4 rounded-2xl border backdrop-blur-xl ${config.bg} ${config.glow} gf-toast-enter transition-all`;

      toast.innerHTML = `
        <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 border ${config.badgeBg}">
          <i data-lucide="${config.icon}" class="w-5 h-5"></i>
        </div>
        <div class="flex-1 min-w-0 pt-0.5">
          ${title ? `<h5 class="text-xs sm:text-sm font-bold text-slate-900 dark:text-white leading-tight">${title}</h5>` : ''}
          <p class="text-xs text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed break-words">${message}</p>
          ${action ? `
            <button class="mt-2.5 px-3 py-1.5 rounded-lg bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-bold hover:opacity-90 transition">
              ${action.label}
            </button>
          ` : ''}
        </div>
        <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg transition" onclick="this.parentElement.remove()">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      `;

      toastContainer.appendChild(toast);
      if (window.lucide) window.lucide.createIcons({ root: toast });

      if (type === 'order') playSound('success');
      else if (type === 'error') playSound('error');
      else if (type === 'bell') playSound('bell');

      const removeToast = () => {
        toast.classList.remove('gf-toast-enter');
        toast.classList.add('gf-toast-exit');
        setTimeout(() => toast.remove(), 200);
      };

      if (duration > 0) {
        setTimeout(removeToast, duration);
      }

      return toast;
    },

    /**
     * Modal interactivo estilo Sheet / Dialog para alertas importantes
     */
    modal(opts) {
      return new Promise((resolve) => {
        ensureContainers();
        const {
          title = 'Aviso del Sistema',
          message = '',
          icon = 'bell',
          type = 'order',
          confirmText = 'Entendido',
          cancelText = null,
          input = null, // { placeholder: '...', value: '...' } si es prompt
        } = typeof opts === 'string' ? { message: opts } : opts;

        const iconColors = {
          order: 'bg-brand-50 text-brand-600 border-brand-200',
          success: 'bg-emerald-50 text-emerald-600 border-emerald-200',
          error: 'bg-rose-50 text-rose-600 border-rose-200',
          warning: 'bg-amber-50 text-amber-600 border-amber-200',
          bell: 'bg-indigo-50 text-indigo-600 border-indigo-200'
        }[type] || 'bg-slate-100 text-slate-700 border-slate-200';

        const btnColor = {
          order: 'bg-brand-500 hover:bg-brand-600 text-white shadow-brand-500/20',
          success: 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/20',
          error: 'bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/20',
          warning: 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-500/20'
        }[type] || 'bg-slate-900 hover:bg-slate-800 text-white shadow-slate-900/10';

        modalContainer.innerHTML = `
          <div class="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-3xl p-6 sm:p-7 max-w-sm sm:max-w-md w-full shadow-2xl transform transition-all duration-200 scale-95 opacity-0 text-center flex flex-col items-center" id="gf-modal-card">
            <div class="w-14 h-14 rounded-2xl border flex items-center justify-center mb-4 ${iconColors} shadow-sm">
              <i data-lucide="${icon}" class="w-7 h-7"></i>
            </div>
            
            <h4 class="text-base sm:text-lg font-outfit font-black text-slate-900 dark:text-white leading-snug">${title}</h4>
            <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-2 leading-relaxed whitespace-pre-line">${message}</p>

            ${input ? `
              <div class="w-full mt-4 text-left">
                <input type="text" id="gf-modal-input" class="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-slate-900 dark:text-white text-sm font-semibold focus:outline-none focus:border-brand-500" placeholder="${input.placeholder || ''}" value="${input.value || ''}" autofocus>
              </div>
            ` : ''}

            <div class="flex items-center gap-2.5 w-full mt-6">
              ${cancelText ? `
                <button type="button" id="gf-btn-cancel" class="flex-1 py-3 rounded-xl text-xs sm:text-sm font-bold text-slate-600 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 transition">
                  ${cancelText}
                </button>
              ` : ''}
              <button type="button" id="gf-btn-confirm" class="flex-1 py-3 rounded-xl text-xs sm:text-sm font-bold shadow-md transition ${btnColor}">
                ${confirmText}
              </button>
            </div>
          </div>
        `;

        if (window.lucide) window.lucide.createIcons({ root: modalContainer });

        // Animación de entrada
        modalContainer.classList.remove('opacity-0', 'pointer-events-none');
        modalContainer.classList.add('opacity-100');
        const card = document.getElementById('gf-modal-card');
        setTimeout(() => {
          card.classList.remove('scale-95', 'opacity-0');
          card.classList.add('scale-100', 'opacity-100');
          const inputEl = document.getElementById('gf-modal-input');
          if (inputEl) inputEl.focus();
        }, 10);

        const closeWithResult = (res) => {
          card.classList.remove('scale-100', 'opacity-100');
          card.classList.add('scale-95', 'opacity-0');
          modalContainer.classList.remove('opacity-100');
          modalContainer.classList.add('opacity-0', 'pointer-events-none');
          setTimeout(() => {
            modalContainer.innerHTML = '';
            resolve(res);
          }, 200);
        };

        const confirmBtn = document.getElementById('gf-btn-confirm');
        confirmBtn.onclick = () => {
          const inputEl = document.getElementById('gf-modal-input');
          const val = inputEl ? inputEl.value : true;
          closeWithResult(val);
        };

        const cancelBtn = document.getElementById('gf-btn-cancel');
        if (cancelBtn) {
          cancelBtn.onclick = () => closeWithResult(null);
        }

        const inputEl = document.getElementById('gf-modal-input');
        if (inputEl) {
          inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') confirmBtn.click();
            if (e.key === 'Escape') if (cancelBtn) cancelBtn.click();
          });
        }
      });
    },

    /**
     * Reemplazo directo para window.alert() con diseño corporativo
     */
    alert(message, title = 'GastroFlow') {
      return this.modal({
        title,
        message,
        type: 'order',
        icon: 'check-circle-2',
        confirmText: 'Entendido'
      });
    },

    /**
     * Reemplazo directo para window.prompt()
     */
    prompt(message, defaultValue = '', title = 'GastroFlow') {
      return this.modal({
        title,
        message,
        type: 'order',
        icon: 'edit-3',
        input: { value: defaultValue },
        confirmText: 'Aceptar',
        cancelText: 'Cancelar'
      });
    },

    /**
     * Reemplazo directo para window.confirm()
     */
    confirm(message, title = '¿Estás seguro?') {
      return this.modal({
        title,
        message,
        type: 'warning',
        icon: 'help-circle',
        confirmText: 'Sí, continuar',
        cancelText: 'Cancelar'
      });
    }
  };

  // Reemplazar globalmente las funciones nativas para interceptar llamadas
  window.gfAlert = (msg, title) => window.GastroNotify.alert(msg, title);
  window.gfPrompt = (msg, def, title) => window.GastroNotify.prompt(msg, def, title);
  window.gfToast = (opts) => window.GastroNotify.show(opts);
})();
