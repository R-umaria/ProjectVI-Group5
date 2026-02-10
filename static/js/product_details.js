document.addEventListener("DOMContentLoaded", async () => {
  // expects your template to set data-product-id on main container
  const container = document.getElementById("productDetail");
  if (!container) return;

  const productId = container.dataset.productId;
  const res = await fetch(`/api/products/${productId}`);
  const p = await res.json();

  // Fill image + title + price + desc
  document.getElementById("pdName").textContent = p.name;
  document.getElementById("pdPrice").textContent = `$${(p.price_cents / 100).toFixed(2)}`;
  document.getElementById("pdDesc").textContent = p.description || "";
  document.getElementById("pdCategory").textContent = p.category || "";

  const img = document.getElementById("pdImg");
  img.src = p.image_url || "";
  img.alt = p.name;

  // Rating summary
  const avg = p.reviews_summary?.avg_rating || 0;
  const count = p.reviews_summary?.count || 0;
  document.getElementById("pdRatingText").textContent = `${avg.toFixed(1)} (${count} reviews)`;

  // Render reviews list
  const list = document.getElementById("reviewsList");
  const reviews = p.reviews || [];
  list.innerHTML = reviews.length
    ? reviews.map(r => `
        <div class="bg-white border border-[#e0ddd8] rounded-lg p-4 flex justify-between gap-6">
          <div>
            <div class="font-semibold text-[#3d3d3d]">Customer</div>
            <div class="text-sm text-[#777]">${r.review_date ? r.review_date : ""}</div>
            <div class="mt-2 text-[#3d3d3d]">${escapeHtml(r.comment || "")}</div>
          </div>
          <div class="text-[#8b4513] font-semibold">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</div>
        </div>
      `).join("")
    : `<div class="text-[#777]">No reviews yet.</div>`;
});

function escapeHtml(str) {
  return (str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}