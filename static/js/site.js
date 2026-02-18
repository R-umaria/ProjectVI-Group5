// Shared UI helpers: toast notifications + navbar cart badge updates
function ensureToastRoot() {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "toast-root";
    root.setAttribute("aria-live", "polite");
    root.setAttribute("aria-atomic", "true");
    document.body.appendChild(root);
  }
  return root;
}

function showToast(message, variant = "success", opts = {}) {
  const { duration = 3000 } = opts;
  const root = ensureToastRoot();

  const toast = document.createElement("div");
  toast.className = `toast toast-${variant}`;
  toast.setAttribute("role", "status");

  const msg = document.createElement("div");
  msg.className = "toast-msg";
  msg.textContent = message;

  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast-close";
  close.setAttribute("aria-label", "Dismiss notification");
  close.textContent = "×";

  toast.appendChild(msg);
  toast.appendChild(close);
  root.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => toast.classList.add("show"));

  let removed = false;
  const remove = () => {
    if (removed) return;
    removed = true;
    toast.classList.remove("show");
    // Allow transition to finish
    setTimeout(() => toast.remove(), 220);
  };

  close.addEventListener("click", remove);

  if (duration && duration > 0) {
    setTimeout(remove, duration);
  }
}

function getNavCartBadge() {
  let badge = document.getElementById("navCartBadge");
  if (badge) return badge;

  // Fallback: create it if base template didn't render it for some reason
  const cartBtn = document.querySelector("a.cartbtn");
  if (!cartBtn) return null;

  badge = document.createElement("span");
  badge.id = "navCartBadge";
  badge.className = "badge";
  badge.dataset.count = "0";
  badge.style.display = "none";
  badge.setAttribute("aria-label", "0 items in cart");
  cartBtn.appendChild(badge);
  return badge;
}

function setNavCartCount(count) {
  const badge = getNavCartBadge();
  if (!badge) return;

  const c = Math.max(0, parseInt(count || 0, 10) || 0);
  badge.dataset.count = String(c);
  badge.textContent = c > 9 ? "9+" : String(c);
  badge.setAttribute("aria-label", `${c} items in cart`);
  badge.style.display = c > 0 ? "" : "none";
}

function bumpNavCartCount(delta) {
  const badge = getNavCartBadge();
  const current = parseInt(badge?.dataset?.count || "0", 10) || 0;
  const d = parseInt(delta || 0, 10) || 0;
  setNavCartCount(current + d);
}

async function refreshNavCartCount() {
  try {
    const res = await fetch("/api/cart", { credentials: "same-origin" });
    if (!res.ok) return;
    const data = await res.json();
    const count = (data.items || []).reduce((sum, it) => sum + (parseInt(it.quantity || 0, 10) || 0), 0);
    setNavCartCount(count);
  } catch (_) {
    // ignore
  }
}

async function addToCart(productId, quantity) {
  const qty = parseInt(quantity || 1, 10) || 1;

  const res = await fetch("/api/cart/items", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({product_id: productId, quantity: qty})
  });

  const msg = document.getElementById("add-msg");
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const errMsg = (data.error && data.error.message) ? data.error.message : "Failed to add to cart";
    if (msg) msg.textContent = errMsg;
    showToast(errMsg, "error", { duration: 4000 });
    return;
  }

  // Immediate UI feedback
  if (msg) msg.textContent = "Added to cart.";
  showToast("Added to cart", "success");

  // Update navbar badge instantly, then reconcile with server
  bumpNavCartCount(qty);
  refreshNavCartCount();
}

async function updateQty(itemId, qty) {
  if (qty < 1) return;
  const res = await fetch(`/api/cart/items/${itemId}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    credentials: "same-origin",
    body: JSON.stringify({quantity: qty})
  });
  if (res.ok) window.location.reload();
}

async function removeItem(itemId) {
  const res = await fetch(`/api/cart/items/${itemId}`, {method: "DELETE", credentials: "same-origin"});
  if (res.ok) window.location.reload();
}

async function placeOrder() {
  const res = await fetch("/api/orders", {
    method: "POST",
    credentials: "same-origin"
  });
  const el = document.getElementById("order-msg");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errMsg = (data.error && data.error.message) ? data.error.message : "Checkout failed";
    if (el) el.textContent = errMsg;
    showToast(errMsg, "error", { duration: 5000 });
    return;
  }
  if (el) el.textContent = `Order placed! Order ID: ${data.id}`;
  showToast("Order placed successfully", "success");
  // Cart will be cleared server-side; update badge
  setNavCartCount(0);
  refreshNavCartCount();
}

// --- Product detail helpers (UI only; no API changes) ---
// Safe to include globally; activates only when [data-product-detail] is present.
window.BWLProductDetail = (function () {
  let qty = 1;

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function getRoot() {
    return document.querySelector('[data-product-detail]');
  }

  function getMaxQty() {
    const root = getRoot();
    const max = parseInt(root?.dataset?.maxQty || '99', 10);
    return Number.isFinite(max) && max > 0 ? max : 99;
  }

  function getUnitPriceCents() {
    const root = getRoot();
    const p = parseInt(root?.dataset?.unitPriceCents || '0', 10);
    return Number.isFinite(p) ? p : 0;
  }

  function fmtMoney(cents) {
    return `$${(cents / 100).toFixed(2)}`;
  }

  function renderQty() {
    const el = document.getElementById('bwlQty');
    const elM = document.getElementById('bwlQtyMobile');
    if (el) el.textContent = String(qty);
    if (elM) elM.textContent = String(qty);

    const stickyBtn = document.getElementById('bwlStickyBtn');
    if (stickyBtn) {
      const total = getUnitPriceCents() * qty;
      stickyBtn.textContent = fmtMoney(total);
    }
  }

  function changeQty(delta) {
    const maxQty = getMaxQty();
    qty = clamp(qty + (parseInt(delta, 10) || 0), 1, maxQty);
    renderQty();
  }

  async function addToCartFromPage() {
    const root = getRoot();
    const pid = parseInt(root?.dataset?.productId || '0', 10);
    if (!pid) return;
    await addToCart(pid, qty);
  }

  function initStars() {
    const ratingInput = document.getElementById('bwlRating');
    const label = document.getElementById('bwlRatingLabel');
    const buttons = Array.from(document.querySelectorAll('.star-btn'));
    if (!ratingInput || buttons.length === 0) return;

    const labels = {
      1: 'Poor',
      2: 'Fair',
      3: 'Good',
      4: 'Very Good',
      5: 'Excellent'
    };

    function setRating(v) {
      const val = clamp(parseInt(v, 10) || 0, 1, 5);
      ratingInput.value = String(val);
      buttons.forEach((b) => {
        const s = parseInt(b.dataset.star || '0', 10);
        b.classList.toggle('active', s <= val);
      });
      if (label) label.textContent = labels[val] || '';
    }

    buttons.forEach((btn) => {
      btn.addEventListener('click', () => setRating(btn.dataset.star));
      btn.addEventListener('mouseenter', () => {
        const v = parseInt(btn.dataset.star || '0', 10);
        buttons.forEach((b) => {
          const s = parseInt(b.dataset.star || '0', 10);
          b.classList.toggle('active', s <= v);
        });
      });
    });

    const wrap = buttons[0].closest('.star-input');
    wrap?.addEventListener('mouseleave', () => {
      const v = parseInt(ratingInput.value || '0', 10);
      if (!v) {
        buttons.forEach((b) => b.classList.remove('active'));
        if (label) label.textContent = '';
        return;
      }
      setRating(v);
    });
  }

  function initCharCount() {
    const counter = document.getElementById('bwlCharCount');
    const textarea = document.querySelector('textarea[name="comment"]');
    if (!counter || !textarea) return;
    const update = () => (counter.textContent = String(textarea.value.length));
    textarea.addEventListener('input', update);
    update();
  }

  function validateReviewForm(form) {
    const rating = document.getElementById('bwlRating')?.value;
    if (!rating) {
      alert('Please select a rating.');
      return false;
    }
    return true;
  }

  function init() {
    if (!getRoot()) return;
    renderQty();
    initStars();
    initCharCount();
  }

  document.addEventListener('DOMContentLoaded', init);

  return {
    changeQty,
    addToCart: addToCartFromPage,
    validateReviewForm,
  };
})();
