document.getElementById("searchBtn")?.addEventListener("click", async ()=>{
  const q = document.getElementById("searchInput").value;
  const dept = document.getElementById("deptSelect").value;
  const res = await fetch(`/search?q=${encodeURIComponent(q)}&dept=${encodeURIComponent(dept)}`);
  const data = await res.json();
  const container = document.getElementById("searchResults");
  if(!data.length){
    container.innerHTML = "<p class='mt-3'>No results</p>";
    return;
  }
  let html = "<h4 class='mt-3'>Search results</h4><div class='row'>";
  for(const b of data){
    html += `<div class="col-md-3 mb-3"><div class="card h-100">
      <img src="${b.image || '/static/images/placeholder.svg'}" class="card-img-top" style="height:170px;object-fit:cover">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title">${b.title}</h5>
        <p class="card-text small mb-1">By ${b.author} (${b.year})</p>
        <p class="card-text small text-muted mb-2">${b.department} • ${b.type}</p>
        <a href="/book/${b.id}" class="mt-auto btn btn-sm btn-outline-primary">View</a>
      </div></div></div>`;
  }
  html += "</div>";
  container.innerHTML = html;
});