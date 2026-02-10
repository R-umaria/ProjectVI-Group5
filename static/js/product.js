document.addEventListener("DOMContentLoaded", () => {
  loadProductsFromUrl();

  // Enter key triggers search
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
  const q = document.getElementById("q")?.value.trim();
  const category = document.getElementById("category")?.value;
  const sort = document.getElementById("sort")?.value;

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

  document.getElementById("q").value = q;
  document.getElementById("category").value = category;
  document.getElementById("sort").value = sort;

  const apiParams = new URLSearchParams();
  apiParams.set("limit", "50");
  apiParams.set("offset", "0");
  if (q) apiParams.set("q", q);
  if (category) apiParams.set("category", category);
  if (sort) apiParams.set("sort", sort);

  const res = await fetch(`/api/products?${apiParams.toString()}`);
  const data = await res.json();

  const items = data.items || [];

  const countEl = document.getElementById("resultsCount");
  if (countEl) countEl.textContent = items.length;

  const grid = document.getElementById("grid");
  if (!grid) return;

  grid.innerHTML = items.map(renderCard).join("");
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
          <span>$${(p.price_cents / 100).toFixed(2)}</span>
          <span class="text-muted-foreground text-sm">${p.category || ""}</span>
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