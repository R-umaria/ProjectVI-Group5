async function addToCart(productId, quantity) {
  const res = await fetch("/api/cart/items", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({product_id: productId, quantity: parseInt(quantity || 1)})
  });
  const msg = document.getElementById("add-msg");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    msg.textContent = (data.error && data.error.message) ? data.error.message : "Failed to add to cart";
    return;
  }
  msg.textContent = "Added to cart.";
}

async function updateQty(itemId, qty) {
  if (qty < 1) return;
  const res = await fetch(`/api/cart/items/${itemId}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({quantity: qty})
  });
  if (res.ok) window.location.reload();
}

async function removeItem(itemId) {
  const res = await fetch(`/api/cart/items/${itemId}`, {method: "DELETE"});
  if (res.ok) window.location.reload();
}

async function placeOrder() {
  const res = await fetch("/api/orders", {
    method: "POST"//,
    // headers: { "Content-Type": "application/json" },
    // body: JSON.stringify({}),
    // credentials: "same-origin"
  }); // Might have to add headers/body/credentials later if any issues arise
  const el = document.getElementById("order-msg");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    el.textContent = (data.error && data.error.message) ? data.error.message : "Checkout failed";
    return;
  }
  el.textContent = `Order placed! Order ID: ${data.id}`;
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
