document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('themePreference');

  // ============ SIDEBAR FUNCTIONALITY ============
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const sidebarItems = document.querySelectorAll('.sidebar-item');

  const toggleSidebar = () => {
    sidebar.classList.toggle('active');
    sidebarOverlay.classList.toggle('active');
  };

  const closeSidebar = () => {
    sidebar.classList.remove('active');
    sidebarOverlay.classList.remove('active');
  };

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
  }

  if (sidebarClose) {
    sidebarClose.addEventListener('click', closeSidebar);
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
  }

  // Close sidebar when a sidebar item is clicked
  sidebarItems.forEach((item) => {
    item.addEventListener('click', () => {
      closeSidebar();
      // Update active state based on current page
      updateSidebarActiveState();
    });
  });

  // Update sidebar active state based on current page
  const updateSidebarActiveState = () => {
    const currentPath = window.location.pathname;
    sidebarItems.forEach((item) => {
      const href = item.getAttribute('href');
      item.classList.remove('active');
      if (href === currentPath) {
        item.classList.add('active');
      }
    });
  };

  // Set initial active state
  updateSidebarActiveState();

  // ============ EXISTING THEME FUNCTIONALITY ============

  if (savedTheme) {
    body.setAttribute('data-theme', savedTheme);
  }

  const applyThemeLabel = (theme) => {
    if (!themeToggle) return;
    themeToggle.textContent = theme === 'dark' ? '🌙' : '☀️';
  };

  applyThemeLabel(body.getAttribute('data-theme') || 'dark');

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      body.setAttribute('data-theme', currentTheme);
      localStorage.setItem('themePreference', currentTheme);
      applyThemeLabel(currentTheme);
    });
  }

  document.querySelectorAll('[data-refresh-url]').forEach((button) => {
    button.addEventListener('click', async () => {
      const url = button.getAttribute('data-refresh-url');
      button.disabled = true;
      button.textContent = 'Refreshing...';

      try {
        const response = await fetch(url, { method: 'GET' });
        if (!response.ok) {
          throw new Error('Refresh failed');
        }

        window.location.href = '/';
      } catch (error) {
        button.textContent = 'Retry Refresh';
        button.disabled = false;
        alert('Unable to refresh the IMDb data right now.');
      }
    });
  });

  const pageName = body.getAttribute('data-page');
  if (pageName === 'movies_page') {
    initMoviesPage();
  }

  if (pageName === 'analytics_page') {
    initAnalyticsPage();
  }
});

function initMoviesPage() {
  const tableBody = document.getElementById('movieTableBody');
  const searchInput = document.getElementById('movieSearch');
  const ratingFilter = document.getElementById('ratingFilter');
  const yearFilter = document.getElementById('yearFilter');
  const prevPageBtn = document.getElementById('prevPage');
  const nextPageBtn = document.getElementById('nextPage');
  const pageInfo = document.getElementById('pageInfo');

  if (!tableBody || !searchInput || !ratingFilter || !yearFilter) return;

  const rawMovies = JSON.parse(document.getElementById('movie-data')?.textContent || '[]');
  let currentPage = 1;
  let pageSize = 20;
  let activeSort = { key: 'rank', direction: 'asc' };

  const getFilteredMovies = () => {
    const searchText = searchInput.value.trim().toLowerCase();
    const minRating = Number.parseFloat(ratingFilter.value || '0');
    const selectedYear = yearFilter.value;

    return [...rawMovies]
      .filter((movie) => {
        const matchesSearch = !searchText || movie.title.toLowerCase().includes(searchText);
        const matchesRating = !minRating || Number(movie.rating) >= minRating;
        const matchesYear = !selectedYear || String(movie.year) === selectedYear;
        return matchesSearch && matchesRating && matchesYear;
      })
      .sort((a, b) => {
        let result = 0;
        const left = a[activeSort.key];
        const right = b[activeSort.key];

        if (activeSort.key === 'rank' || activeSort.key === 'year') {
          result = Number(left) - Number(right);
        } else if (activeSort.key === 'rating') {
          result = Number(left) - Number(right);
        } else {
          result = String(left).localeCompare(String(right));
        }

        return activeSort.direction === 'asc' ? result : -result;
      });
  };

  const renderTable = () => {
    const filteredMovies = getFilteredMovies();
    const totalPages = Math.max(1, Math.ceil(filteredMovies.length / pageSize));
    currentPage = Math.min(currentPage, totalPages);

    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const paginatedMovies = filteredMovies.slice(start, end);

    tableBody.innerHTML = paginatedMovies.map((movie) => `
      <tr>
        <td>#${movie.rank}</td>
        <td>${movie.title}</td>
        <td>${movie.year}</td>
        <td>${movie.rating}</td>
      </tr>
    `).join('');

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;
  };

  document.querySelectorAll('[data-sort]').forEach((header) => {
    header.addEventListener('click', () => {
      const key = header.getAttribute('data-sort');
      if (activeSort.key === key) {
        activeSort.direction = activeSort.direction === 'asc' ? 'desc' : 'asc';
      } else {
        activeSort.key = key;
        activeSort.direction = 'asc';
      }
      currentPage = 1;
      renderTable();
    });
  });

  searchInput.addEventListener('input', () => {
    currentPage = 1;
    renderTable();
  });

  ratingFilter.addEventListener('change', () => {
    currentPage = 1;
    renderTable();
  });

  yearFilter.addEventListener('change', () => {
    currentPage = 1;
    renderTable();
  });

  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage -= 1;
      renderTable();
    }
  });

  nextPageBtn.addEventListener('click', () => {
    const filteredMovies = getFilteredMovies();
    const totalPages = Math.max(1, Math.ceil(filteredMovies.length / pageSize));
    if (currentPage < totalPages) {
      currentPage += 1;
      renderTable();
    }
  });

  renderTable();
}

function initAnalyticsPage() {
  if (!window.chartData) return;
  const { topMovies, ratingDistribution, moviesByYear, decadeDistribution } = window.chartData;

  const buildBarChart = (canvasId, labels, data, label, color) => {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label,
          data,
          backgroundColor: color,
          borderRadius: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: false } }
      }
    });
  };

  buildBarChart(
    'topMoviesChart',
    topMovies.map((movie) => movie.title),
    topMovies.map((movie) => movie.rating),
    'IMDb Rating',
    'rgba(139, 92, 246, 0.8)'
  );

  buildBarChart(
    'ratingDistributionChart',
    ratingDistribution.map((point) => point.label),
    ratingDistribution.map((point) => point.count),
    'Movies',
    'rgba(52, 211, 153, 0.8)'
  );

  buildBarChart(
    'yearChart',
    moviesByYear.map((point) => point.year),
    moviesByYear.map((point) => point.count),
    'Movies',
    'rgba(59, 130, 246, 0.8)'
  );

  if (decadeDistribution && decadeDistribution.length > 0) {
    buildBarChart(
      'decadeChart',
      decadeDistribution.map((point) => point.label),
      decadeDistribution.map((point) => point.count),
      'Movies',
      'rgba(251, 146, 60, 0.8)'
    );
  }
}
