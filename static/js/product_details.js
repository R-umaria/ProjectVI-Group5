document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("productDetail");
  const titleEl = document.getElementById("pdName");

  if (!container) {
    if (titleEl) titleEl.textContent = "Missing #productDetail";
    return;
  }

  const productId = Number(container.dataset.productId);
  if (!productId) {
    if (titleEl) titleEl.textContent = "Missing product id on page";
    return;
  }

  // ---------- Load product + reviews ----------
  try {
    const res = await fetch(`/api/products/${productId}`);
    if (!res.ok) {
      if (titleEl) titleEl.textContent = `API error (${res.status})`;
      return;
    }

    const p = await res.json();

    // product fields
    document.getElementById("pdName").textContent = p.name || "Unknown Product";
    document.getElementById("pdPrice").textContent = `$${((p.price_cents || 0) / 100).toFixed(2)}`;
    document.getElementById("pdDesc").textContent = p.description || "";
    document.getElementById("pdCategory").textContent = p.category || "";

    const img = document.getElementById("pdImg");
    img.src = p.image_url || "";
    img.alt = p.name || "Product";

    // rating summary
    const avg = p.reviews_summary?.avg_rating ?? 0;
    const count = p.reviews_summary?.count ?? 0;
    document.getElementById("pdRatingText").textContent = `${Number(avg).toFixed(1)} (${count} reviews)`;

    // reviews list
    const list = document.getElementById("reviewsList");
    const reviews = p.reviews || [];

    list.innerHTML = reviews.length
      ? reviews.map(r => `
          <div class="bg-white border border-[#e0ddd8] rounded-lg p-4 flex justify-between gap-6">
            <div>
              <div class="font-semibold text-[#3d3d3d]">Customer</div>
              <div class="text-sm text-[#777]">${r.review_date || ""}</div>
              <div class="mt-2 text-[#3d3d3d]">${escapeHtml(r.comment || "")}</div>
            </div>
            <div class="text-[#8b4513] font-semibold">
              ${"★".repeat(r.rating || 0)}${"☆".repeat(5 - (r.rating || 0))}
            </div>
          </div>
        `).join("")
      : `<div class="text-[#777]">No reviews yet.</div>`;

  } catch (e) {
    console.error(e);
    if (titleEl) titleEl.textContent = "JS error — check console";
  }

  // ---------- Add to Cart ----------
  const cartBtn = document.getElementById("addToCartBtn");
  if (cartBtn) {
    cartBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/cart/items", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ product_id: productId, quantity: 1 })
        });

        if (res.status === 401) {
          window.location.href = `/login?redirect=/products/${productId}`;
          return;
        }

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          alert(data?.error || "Failed to add to cart");
          return;
        }

        alert("Added to cart!");
      } catch (e) {
        console.error(e);
        alert("Network error adding to cart");
      }
    });
  }

  // ---------- Submit Review ----------
  const submitBtn = document.getElementById("submitReviewBtn");
  if (submitBtn) {
    submitBtn.addEventListener("click", async () => {
      const rating = Number(document.getElementById("reviewRating")?.value);
      const comment = document.getElementById("reviewComment")?.value || "";

      if (!rating || rating < 1 || rating > 5) {
        alert("Please select a rating (1–5).");
        return;
      }

      try {
        const res = await fetch(`/api/products/${productId}/reviews`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating, comment })
        });

        if (res.status === 401) {
          window.location.href = `/login?redirect=/products/${productId}`;
          return;
        }

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          alert(data?.error || "Failed to submit review");
          return;
        }

        alert("Review submitted!");
        window.location.reload();
      } catch (e) {
        console.error(e);
        alert("Network error submitting review");
      }
    });
  }
});

function escapeHtml(str) {
  return (str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}