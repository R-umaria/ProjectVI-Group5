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
