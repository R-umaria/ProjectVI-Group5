document.addEventListener("DOMContentLoaded", () => {
  loadProductsFromUrl();

  const searchInput = document.getElementById("q");
  if (searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") runSearch();
    });
  }

  const categorySelect = document.getElementById("category");
  if (categorySelect) categorySelect.addEventListener("change", runSearch);

  const sortSelect = document.getElementById("sort");
  if (sortSelect) sortSelect.addEventListener("change", runSearch);

  const clearBtn = document.getElementById("clearBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      window.location.href = "/products";
    });
  }
});

function runSearch() {
  const q = document.getElementById("q")?.value.trim() || "";
  const category = document.getElementById("category")?.value || "";
  const sort = document.getElementById("sort")?.value || "";

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (sort) params.set("sort", sort);

  const qs = params.toString();
  window.location.href = qs ? `/products?${qs}` : "/products";
}

async function loadProductsFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q") || "";
  const category = params.get("category") || "";
  const sort = params.get("sort") || "popular";

  const qEl = document.getElementById("q");
  const catEl = document.getElementById("category");
  const sortEl = document.getElementById("sort");
  if (qEl) qEl.value = q;
  if (catEl) catEl.value = category;
  if (sortEl) sortEl.value = sort;

  const apiParams = new URLSearchParams();
  apiParams.set("limit", "50");
  apiParams.set("offset", "0");
  if (q) apiParams.set("q", q);
  if (sort) apiParams.set("sort", sort);

  const res = await fetch(`/api/products?${apiParams.toString()}`);
  const data = await res.json();
  const items = data.items || [];

  const normalize = (s) => {
    s = (s || "").toString().toLowerCase();
    if (!s) return "";
    if (s.endsWith("ies")) return s.slice(0, -3) + "y";
    if (s.endsWith("es")) return s.slice(0, -2);
    if (s.endsWith("s")) return s.slice(0, -1);
    return s;
  };

  const sel = normalize(category);

  const filtered = items.filter((p) => {
    const text = ((p.name || "") + " " + (p.description || "")).toLowerCase();
    const qOk = !q || text.includes(q.toLowerCase());

    const pCat = normalize(p.category || p.category_name);
    const catOk = !sel || pCat === sel;

    return qOk && catOk;
  });

  const countEl = document.getElementById("resultsCount");
  if (countEl) countEl.textContent = filtered.length;

  const grid = document.getElementById("grid");
  if (!grid) return;

  grid.innerHTML = filtered.map(renderCard).join("");
}

function renderCard(p) {
  const image = p.image_url
    ? `<img src="${p.image_url}" class="w-full h-full object-cover">`
    : `<div class="w-full h-full flex items-center justify-center text-4xl">🎁</div>`;

  return `
    <article class="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
      <div class="h-56 bg-muted flex items-center justify-center">
        ${image}
      </div>

      <div class="p-4">
        <div class="inline-flex px-3 py-1 rounded-full text-xs bg-muted mb-3">Featured</div>

        <h3 class="font-serif text-xl leading-tight">${escapeHtml(p.name)}</h3>

        <div class="mt-2 flex justify-between">
          <span>$${((p.price_cents || 0) / 100).toFixed(2)}</span>
          <span class="text-muted-foreground text-sm">${escapeHtml(p.category || "")}</span>
        </div>

        <div class="mt-4 flex gap-2">
          <a href="/products/${p.id}" class="flex-1 text-center bg-muted py-2 rounded-lg">
            View
          </a>
          <button onclick="addToCart(${p.id})" class="flex-1 bg-primary text-primary-foreground py-2 rounded-lg">
            Add to Cart
          </button>
        </div>
      </div>
    </article>
  `;
}

function escapeHtml(str) {
  return (str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function addToCart(productId) {
  try {
    const res = await fetch("/api/cart/items", {   // ✅ correct endpoint
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      console.log("Add to cart failed:", data);
      alert(data?.error?.message || "Failed to add to cart");
      return;
    }

    alert("Added to cart!");
  } catch (e) {
    console.error(e);
    alert("Network error adding to cart");
  }
}