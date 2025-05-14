/**
 * Main application script for cryptocurrency price tracker
 * This app fetches data from CoinGecko API, handles caching,
 * and provides search and display functionality with fallbacks
 * for when API limits are reached.
 */

// Store all cryptocurrency data fetched from API for search functionality
let allCryptoData = [];

// Auto refresh timer
let autoRefreshTimer = null;

// Store the currently changed prices for animation
let changedPrices = {};

/**
 * Theme management system
 * Handles toggling between light and dark themes with localStorage persistence
 * and synchronized transitions
 */
const themeManager = {
  init: function () {
    // Set initial theme based on localStorage or system preference
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) {
      document.documentElement.setAttribute("data-theme", savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;
      if (prefersDark) {
        document.documentElement.setAttribute("data-theme", "dark");
      }
    }

    // Add theme toggle event listener - handled in DOMContentLoaded now
    // for better synchronization

    // Listen for system preference changes
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", (e) => {
        // Only update if user hasn't manually set a preference
        if (!localStorage.getItem("theme")) {
          // Add transitioning class for smooth change
          document.documentElement.classList.add("theme-transitioning");

          setTimeout(() => {
            document.documentElement.setAttribute(
              "data-theme",
              e.matches ? "dark" : "light"
            );
          }, 50);

          // Remove transitioning class after transition completes
          setTimeout(() => {
            document.documentElement.classList.remove("theme-transitioning");
          }, parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--transition-duration")) * 1000 + 50);
        }
      });
  },

  toggleTheme: function () {
    const currentTheme =
      document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "light" ? "dark" : "light";

    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
  },
};

/**
 * API response cache system
 * Stores API responses in memory and localStorage with expiration times
 * to reduce API calls and provide data when offline or rate-limited
 */
const apiCache = {
  // In-memory cache storage
  cache: {},

  /**
   * Get data from cache if valid and not expired
   * @param {string} key - Cache key to retrieve
   * @returns {object|null} - Cached data or null if invalid/expired
   */
  get: function (key) {
    const cachedItem = this.cache[key];
    if (!cachedItem) return null;

    // Check if cache entry is expired (5 minutes)
    const now = Date.now();
    if (now - cachedItem.timestamp > 5 * 60 * 1000) {
      delete this.cache[key];
      return null;
    }

    return cachedItem.data;
  },

  /**
   * Store data in cache with timestamp
   * Also persists to localStorage for reuse across sessions
   * @param {string} key - Cache key
   * @param {object} data - Data to store
   */
  set: function (key, data) {
    this.cache[key] = {
      data: data,
      timestamp: Date.now(),
    };

    // Persist to localStorage for use across sessions
    try {
      const storageItem = {
        data: data,
        timestamp: Date.now(),
      };
      localStorage.setItem("crypto_cache_" + key, JSON.stringify(storageItem));
    } catch (e) {
      console.warn("Failed to store in localStorage:", e);
    }
  },

  /**
   * Initialize cache from localStorage on page load
   * Restores previously cached data if not expired
   */
  init: function () {
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith("crypto_cache_")) {
          const cacheKey = key.replace("crypto_cache_", "");
          const item = JSON.parse(localStorage.getItem(key));

          // Check if item is expired (10 minutes)
          const now = Date.now();
          if (now - item.timestamp <= 10 * 60 * 1000) {
            this.cache[cacheKey] = item;
          } else {
            localStorage.removeItem(key);
          }
        }
      }
    } catch (e) {
      console.warn("Failed to load from localStorage:", e);
    }
  },
};

/**
 * Request throttling system to manage API rate limits
 * Queues requests and implements exponential backoff for retries
 * when rate limits are encountered
 */
const requestThrottler = {
  queue: [],
  inProgress: false,
  retryDelay: 1000,

  /**
   * Add a request to the queue for processing
   * @param {Function} requestFn - Function that returns a Promise for the API request
   * @param {Function} onSuccess - Callback for successful requests
   * @param {Function} onError - Callback for failed requests
   */
  add: function (requestFn, onSuccess, onError) {
    this.queue.push({
      requestFn,
      onSuccess,
      onError,
      attempt: 0,
    });

    if (!this.inProgress) {
      this.processNext();
    }
  },

  /**
   * Process the next request in the queue
   * Implements retry logic with exponential backoff for rate limit errors
   */
  processNext: function () {
    if (this.queue.length === 0) {
      this.inProgress = false;
      return;
    }

    this.inProgress = true;
    const request = this.queue.shift();

    request
      .requestFn()
      .then((data) => {
        request.onSuccess(data);
        // Small delay between requests to avoid rate limiting
        setTimeout(() => this.processNext(), 300);
      })
      .catch((error) => {
        // Handle rate limit errors with exponential backoff
        if (error.status === 429 || error.message?.includes("rate limit")) {
          request.attempt++;
          const delay = Math.min(
            30000,
            this.retryDelay * Math.pow(2, request.attempt - 1)
          );

          console.log(`Rate limit hit. Retrying in ${delay / 1000} seconds...`);

          // Requeue with backoff if under max attempts
          if (request.attempt < 4) {
            setTimeout(() => {
              this.queue.unshift(request);
              this.processNext();
            }, delay);
          } else {
            request.onError(error);
            setTimeout(() => this.processNext(), 1000);
          }
        } else {
          request.onError(error);
          setTimeout(() => this.processNext(), 500);
        }
      });
  },
};

/**
 * Fallback data for popular cryptocurrencies if API is unavailable/rate-limited
 * These values will be used when CoinGecko API cannot be accessed
 */
const popularCryptos = {
  bitcoin: {
    id: "bitcoin",
    name: "Bitcoin",
    symbol: "BTC",
    price: 67500,
    change: 2.5,
  },
  ethereum: {
    id: "ethereum",
    name: "Ethereum",
    symbol: "ETH",
    price: 3400,
    change: 1.8,
  },
  dogecoin: {
    id: "dogecoin",
    name: "Dogecoin",
    symbol: "DOGE",
    price: 0.14,
    change: 1.2,
  },
  solana: {
    id: "solana",
    name: "Solana",
    symbol: "SOL",
    price: 152,
    change: 3.1,
  },
  ripple: {
    id: "ripple",
    name: "XRP",
    symbol: "XRP",
    price: 0.49,
    change: -0.8,
  },
  cardano: {
    id: "cardano",
    name: "Cardano",
    symbol: "ADA",
    price: 0.45,
    change: 0.3,
  },
  tether: {
    id: "tether",
    name: "Tether",
    symbol: "USDT",
    price: 1,
    change: 0.01,
  },
  binancecoin: {
    id: "binancecoin",
    name: "BNB",
    symbol: "BNB",
    price: 560,
    change: 1.5,
  },
  polkadot: {
    id: "polkadot",
    name: "Polkadot",
    symbol: "DOT",
    price: 6.7,
    change: 0.7,
  },
};

// List of cryptocurrency IDs to fetch by default
const cryptoIds = [
  "bitcoin",
  "ethereum",
  "solana",
  "the-open-network",
  "tether",
  "ripple",
];

// Map of crypto IDs to their display names and symbols
const cryptoMap = {
  bitcoin: { name: "Bitcoin", symbol: "BTC" },
  ethereum: { name: "Ethereum", symbol: "ETH" },
  solana: { name: "Solana", symbol: "SOL" },
  "the-open-network": { name: "Toncoin", symbol: "TON" },
  tether: { name: "Tether", symbol: "USDT" },
  ripple: { name: "XRP", symbol: "XRP" },
};

/**
 * Format price values for display
 * Adjusts decimal places based on price magnitude
 * @param {number} price - The price value to format
 * @returns {string} - Formatted price string
 */
function formatPrice(price) {
  if (price >= 1000) {
    return price.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  } else if (price >= 1) {
    return price.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  } else {
    return price.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  }
}

/**
 * Format large numbers with B/M/T suffixes
 * @param {number} num - The number to format
 * @returns {string} - Formatted number with appropriate suffix
 */
function formatLargeNumber(num) {
  if (num >= 1e12) {
    return (num / 1e12).toFixed(2) + "T";
  } else if (num >= 1e9) {
    return (num / 1e9).toFixed(2) + "B";
  } else if (num >= 1e6) {
    return (num / 1e6).toFixed(2) + "M";
  } else {
    return num.toLocaleString();
  }
}

/**
 * Main function to fetch cryptocurrency price data
 * Handles API requests, caching, and fallback strategies
 */
async function fetchCryptoPrices() {
  const loadingContainer = document.getElementById("loadingContainer");
  const errorContainer = document.getElementById("errorContainer");
  const cryptoGrid = document.getElementById("cryptoGrid");

  // Only show loading if grid is not already displayed
  if (cryptoGrid.style.display !== "grid") {
    loadingContainer.style.display = "flex";
  }

  errorContainer.style.display = "none";

  // Store previous data for animation comparison
  changedPrices = {};
  if (allCryptoData.length > 0) {
    allCryptoData.forEach((crypto) => {
      changedPrices[crypto.id] = {
        price: crypto.current_price,
        change: crypto.price_change_percentage_24h,
      };
    });
  }

  // Check for cached data first
  const cacheKey = `markets_${cryptoIds.join("_")}`;
  const cachedData = apiCache.get(cacheKey);

  if (cachedData) {
    console.log("Using cached data");

    // Update the last updated timestamp
    const now = new Date();
    document.getElementById(
      "lastUpdated"
    ).textContent = `Last updated: ${now.toLocaleString()} (cached)`;

    // Only animate if we had previous data
    const shouldAnimate = allCryptoData.length > 0;

    // Update our global data
    allCryptoData = cachedData;

    // Process and display the data
    renderCryptoCards(cachedData, shouldAnimate);

    // Show the grid and hide loading
    loadingContainer.style.display = "none";
    cryptoGrid.style.display = "grid";

    return;
  }

  try {
    // CoinGecko API endpoint for multiple coins
    const url = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${cryptoIds.join(
      ","
    )}&order=market_cap_desc&per_page=100&page=1&sparkline=true&price_change_percentage=24h`;

    // Use the throttler for this request
    await new Promise((resolve, reject) => {
      requestThrottler.add(
        // Request function
        () =>
          fetch(url).then((response) => {
            if (!response.ok) {
              throw {
                status: response.status,
                message: `API request failed with status ${response.status}`,
              };
            }
            return response.json();
          }),
        // Success handler
        (data) => {
          // Only animate if we had previous data
          const shouldAnimate = allCryptoData.length > 0;

          // Store the data in our global variable for search functionality
          allCryptoData = data;

          // Cache the successful response
          apiCache.set(cacheKey, data);

          // Update the last updated timestamp
          const now = new Date();
          document.getElementById(
            "lastUpdated"
          ).textContent = `Last updated: ${now.toLocaleString()}`;

          // Process and display the data
          renderCryptoCards(data, shouldAnimate);

          // Show the grid and hide loading
          loadingContainer.style.display = "none";
          cryptoGrid.style.display = "grid";

          resolve();
        },
        // Error handler
        (error) => {
          console.error("Error fetching data:", error);

          // Try to use fallback data for the main currencies
          const fallbackData = cryptoIds.map((id) => {
            const fallback = popularCryptos[id];
            if (fallback) {
              return {
                id: fallback.id,
                name: fallback.name,
                symbol: fallback.symbol,
                current_price: fallback.price,
                price_change_percentage_24h: fallback.change,
                total_volume: 1000000000,
                market_cap: 10000000000,
                image: `https://assets.coingecko.com/coins/images/1/small/bitcoin.png`,
              };
            }
            return {
              id: id,
              name: cryptoMap[id]?.name || id,
              symbol: cryptoMap[id]?.symbol || id.toUpperCase(),
              current_price: "N/A",
              price_change_percentage_24h: 0,
              total_volume: "N/A",
              market_cap: "N/A",
              image: null,
            };
          });

          // Show error message
          errorContainer.innerHTML = `
                <div class="error-message">
                  <strong>Error loading data:</strong> ${
                    error.message || "Unknown error"
                  }
                  <p>Using cached data where possible. This could be due to CoinGecko API rate limits.</p>
                </div>
              `;

          // Use fallback data
          renderCryptoCards(fallbackData, false);

          loadingContainer.style.display = "none";
          errorContainer.style.display = "block";
          cryptoGrid.style.display = "grid";

          reject(error);
        }
      );
    });
  } catch (error) {
    console.error("Error in fetch flow:", error);
  } finally {
    // Schedule next auto-refresh (every 5 minutes)
    scheduleNextRefresh();
  }
}

/**
 * Schedule the next automatic refresh
 * Handles clearing existing timers and setting up new ones
 */
function scheduleNextRefresh() {
  // Clear any existing timer
  if (autoRefreshTimer) {
    clearTimeout(autoRefreshTimer);
  }

  // Set next refresh for 5 minutes (300000 ms)
  autoRefreshTimer = setTimeout(() => {
    fetchCryptoPrices();
  }, 300000);

  console.log("Scheduled next auto-refresh for 5 minutes from now");
}

/**
 * Render cryptocurrency cards with data
 * Creates HTML elements for each crypto and adds them to the grid
 * @param {Array} cryptoData - Array of cryptocurrency data objects
 * @param {boolean} animate - Whether to animate changes
 */
function renderCryptoCards(cryptoData, animate = false) {
  const grid = document.getElementById("cryptoGrid");
  grid.innerHTML = "";

  cryptoData.forEach((crypto) => {
    const isPositive = crypto.price_change_percentage_24h > 0;
    const cardElement = document.createElement("div");
    cardElement.className = "crypto-card";

    // Get display name and symbol from our map, or use API values as fallback
    const displayInfo = cryptoMap[crypto.id] || {
      name: crypto.name,
      symbol: crypto.symbol.toUpperCase(),
    };

    // Create the URL for the coin on CoinGecko
    const coinUrl = `https://www.coingecko.com/en/coins/${crypto.id}`;

    // Check if price has changed for animation
    let priceChanged = false;
    let changeDirection = "";

    if (animate && changedPrices[crypto.id]) {
      const oldPrice = changedPrices[crypto.id].price;
      const oldChange = changedPrices[crypto.id].change;

      // Only animate meaningful changes
      if (
        typeof oldPrice === "number" &&
        typeof crypto.current_price === "number"
      ) {
        if (Math.abs(oldPrice - crypto.current_price) / oldPrice > 0.0001) {
          priceChanged = true;
          changeDirection =
            crypto.current_price > oldPrice ? "increase" : "decrease";
        }
      }

      // Also detect significant change in the 24h percentage
      if (
        typeof oldChange === "number" &&
        typeof crypto.price_change_percentage_24h === "number"
      ) {
        if (Math.abs(oldChange - crypto.price_change_percentage_24h) > 0.1) {
          priceChanged = true;
        }
      }
    }

    cardElement.innerHTML = `
          <div class="card-header">
            ${
              crypto.image
                ? `<div class="crypto-icon">
                 <img src="${crypto.image}" alt="${crypto.name}" 
                      onerror="this.onerror=null; this.style.display='none'; this.parentNode.innerHTML='${crypto.symbol
                        .charAt(0)
                        .toUpperCase()}';">
               </div>`
                : `<div class="crypto-icon-fallback" style="background-color: #${Math.floor(
                    Math.random() * 16777215
                  ).toString(16)}">
                ${crypto.symbol.charAt(0).toUpperCase()}
              </div>`
            }
            <div class="crypto-title">
              <div class="crypto-name">
                <a href="${coinUrl}" target="_blank" rel="noopener noreferrer" class="crypto-name-link" title="View ${
      displayInfo.name
    } on CoinGecko">
                  ${displayInfo.name}
                </a>
              </div>
              <div class="crypto-symbol">${displayInfo.symbol}</div>
            </div>
          </div>
          <div class="card-body">
            <div class="price ${
              priceChanged ? "price-update" : ""
            }" data-change="${changeDirection}">$${formatPrice(
      crypto.current_price
    )}</div>
            <div class="price-chart-container">
              <canvas class="mini-chart" id="chart-${crypto.id}"></canvas>
            </div>
            <div class="price-change ${isPositive ? "positive" : "negative"} ${
      priceChanged ? "price-update" : ""
    }">
              ${isPositive ? "↑" : "↓"} ${Math.abs(
      crypto.price_change_percentage_24h
    ).toFixed(2)}%
            </div>
            <div class="stats">
              <div class="stat-item">
                <div class="stat-label">Volume (24h)</div>
                <div class="stat-value">$${formatLargeNumber(
                  crypto.total_volume
                )}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">Market Cap</div>
                <div class="stat-value">$${formatLargeNumber(
                  crypto.market_cap
                )}</div>
              </div>
            </div>
          </div>
        `;

    grid.appendChild(cardElement);

    // Create sparkline chart if sparkline data is available
    if (crypto.sparkline_in_7d && crypto.sparkline_in_7d.price) {
      createSparklineChart(
        `chart-${crypto.id}`,
        crypto.sparkline_in_7d.price,
        isPositive
      );
    }
  });
}

// Function to create a small sparkline chart
function createSparklineChart(elementId, priceData, isPositive) {
  const ctx = document.getElementById(elementId);
  if (!ctx) {
    console.warn(`Canvas element with ID ${elementId} not found`);
    return;
  }

  // Make sure priceData is valid
  if (!Array.isArray(priceData) || priceData.length === 0) {
    console.warn(`Invalid price data for chart ${elementId}`);
    return;
  }

  const chartColor = isPositive ? "#4CAF50" : "#ff5e62";

  // Destroy any existing chart on this canvas
  if (ctx.chart) {
    ctx.chart.destroy();
  }

  // Make sure the canvas is visible before creating the chart
  ctx.style.display = "block";

  try {
    // Create the new chart
    const chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: Array(priceData.length).fill(""),
        datasets: [
          {
            data: priceData,
            borderColor: chartColor,
            borderWidth: 1.5,
            fill: true,
            backgroundColor: isPositive
              ? "rgba(76, 175, 80, 0.1)"
              : "rgba(255, 94, 98, 0.1)",
            tension: 0.4,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            enabled: false,
          },
        },
        scales: {
          x: {
            display: false,
            grid: {
              display: false,
            },
          },
          y: {
            display: false,
            grid: {
              display: false,
            },
            min: Math.min(...priceData) * 0.99,
            max: Math.max(...priceData) * 1.01,
          },
        },
        animation: {
          duration: 200, // Faster animation
        },
        layout: {
          padding: 0,
        },
        elements: {
          line: {
            borderWidth: 1.5,
          },
        },
      },
    });

    // Store chart instance on the canvas element for potential future reference
    ctx.chart = chart;
  } catch (err) {
    console.error(`Error creating chart for ${elementId}:`, err);
  }
}

// Track search operations that are in progress to prevent duplicates
const searchInProgress = {};

// Initialize the application when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Initialize cache from localStorage
  apiCache.init();

  // Initialize theme manager
  themeManager.init();

  const searchInput = document.getElementById("cryptoSearch");
  const searchResults = document.getElementById("searchResults");
  const searchButton = document.getElementById("searchButton");

  // Search input debounce timer
  let searchDebounceTimer;

  // Search input event listener with debouncing
  searchInput.addEventListener("input", function (event) {
    // Clear any existing timer
    clearTimeout(searchDebounceTimer);

    // Set a new timer to execute search after user stops typing
    searchDebounceTimer = setTimeout(() => {
      handleSearch(event);
    }, 800); // 800ms debounce time
  });

  // Search button click event
  searchButton.addEventListener("click", () => {
    clearTimeout(searchDebounceTimer);
    handleSearch({ target: searchInput });
  });

  // Close search results when clicking outside
  document.addEventListener("click", function (event) {
    if (!event.target.closest(".search-container")) {
      searchResults.classList.remove("active");
    }
  });

  // Handle Enter key in search input
  searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      clearTimeout(searchDebounceTimer);
      const firstResult = searchResults.querySelector(".result-item");
      if (
        firstResult &&
        !firstResult.classList.contains("loading-item") &&
        firstResult.textContent !== "No results found" &&
        firstResult.textContent !== "Error searching. Try again later."
      ) {
        firstResult.click();
      }
    }
  });

  // Enhanced theme toggling with better synchronization
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      // Remove any existing animation that might still be running
      document.querySelectorAll(".theme-transitioning").forEach((el) => {
        el.classList.remove("theme-transitioning");
      });

      // Get current theme to determine transition direction
      const currentTheme =
        document.documentElement.getAttribute("data-theme") || "light";
      const newTheme = currentTheme === "light" ? "dark" : "light";

      // Add transitioning-to class to help with specific transitions
      document.documentElement.classList.add(
        `theme-transitioning-to-${newTheme}`
      );

      // Add a special class to help with transition synchronization
      document.documentElement.classList.add("theme-transitioning");

      // For the header, apply special handling
      const header = document.querySelector("header");
      if (header) {
        // Temporarily force the header to use solid background color during transition
        header.style.background = "none";
      }

      // Delay the actual theme change slightly to ensure all elements are ready to transition
      setTimeout(() => {
        themeManager.toggleTheme();
      }, 50);

      // Remove the transition classes when transitions are likely complete
      const transitionDuration =
        parseFloat(
          getComputedStyle(document.documentElement).getPropertyValue(
            "--transition-duration"
          )
        ) *
          1000 +
        50;

      setTimeout(() => {
        document.documentElement.classList.remove("theme-transitioning");
        document.documentElement.classList.remove(
          `theme-transitioning-to-${newTheme}`
        );

        // Restore header background
        if (header) {
          header.style.background = "";
        }
      }, transitionDuration);
    });
  }

  // Initial fetch and auto-refresh setup
  fetchCryptoPrices();
});

/**
 * Handle search input and show results
 * Uses multiple sources: local data, cached results, and API search
 * @param {Event} event - The event that triggered the search
 */
function handleSearch(event) {
  const searchTerm = event.target.value.trim().toLowerCase();
  const searchResults = document.getElementById("searchResults");

  // Clear previous results
  searchResults.innerHTML = "";

  if (searchTerm.length < 2) {
    searchResults.classList.remove("active");
    return;
  }

  // Show searching state immediately
  searchResults.innerHTML = `
        <div class="search-loading">
          <div class="search-loading-spinner"></div>
          <div>Searching cryptocurrencies...</div>
        </div>
      `;
  searchResults.classList.add("active");

  // Check if we have popular crypto matching the search
  const popularMatches = Object.values(popularCryptos).filter(
    (crypto) =>
      crypto.name.toLowerCase().includes(searchTerm) ||
      crypto.symbol.toLowerCase().includes(searchTerm)
  );

  // Filter existing loaded cryptocurrencies based on search term
  const matchingCryptos = allCryptoData.filter(
    (crypto) =>
      crypto.name.toLowerCase().includes(searchTerm) ||
      crypto.symbol.toLowerCase().includes(searchTerm)
  );

  // First check if we have cached search results
  const cacheKey = `search_${searchTerm}`;
  const cachedResults = apiCache.get(cacheKey);

  if (cachedResults) {
    console.log("Using cached search results");
    displaySearchResults(cachedResults, searchResults, event);
    return;
  }

  if (matchingCryptos.length > 0) {
    // Display results from existing data
    displaySearchResults(matchingCryptos, searchResults, event);
  } else if (popularMatches.length > 0) {
    // Convert popular matches to expected format and display
    const formattedPopularMatches = popularMatches.map((crypto) => ({
      id: crypto.id,
      name: crypto.name,
      symbol: crypto.symbol,
      // Fix the image URL to use a more accurate format with the correct ID
      image: `https://assets.coingecko.com/coins/images/${getCoinImageId(
        crypto.id
      )}/small/${crypto.id}.png`,
      current_price: crypto.price,
      price_change_percentage_24h: crypto.change,
      total_volume: 1000000000,
      market_cap: 10000000000,
    }));

    // Add a note that these are cached results
    searchResults.innerHTML =
      '<div class="result-item" style="background:#f9f9f9;cursor:default;">⚠️ Using cached data due to API limits</div>';
    displaySearchResults(formattedPopularMatches, searchResults, event);
  } else {
    // Search for cryptocurrency on CoinGecko API
    searchCoinGecko(searchTerm, searchResults, event);
  }
}

/**
 * Search for cryptocurrencies using CoinGecko API
 * Handles rate limits, caching, and fallback mechanisms
 * @param {string} searchTerm - The search query
 * @param {HTMLElement} searchResults - The results container element
 * @param {Event} event - The event that triggered the search
 */
async function searchCoinGecko(searchTerm, searchResults, event) {
  // Check rate limit tracking in localStorage
  let rateLimitInfo = { count: 0, resetTime: 0 };
  try {
    const storedInfo = localStorage.getItem("cg_rate_limit");
    if (storedInfo) {
      rateLimitInfo = JSON.parse(storedInfo);
    }
  } catch (e) {
    console.warn("Failed to read rate limit info:", e);
  }

  const now = Date.now();

  // Reset count if the reset time has passed
  if (now > rateLimitInfo.resetTime) {
    rateLimitInfo = { count: 0, resetTime: now + 60000 }; // Reset in 1 minute
  }

  // Check if we're approaching rate limit (CoinGecko allows ~10-30 requests per minute)
  if (rateLimitInfo.count >= 25) {
    searchResults.innerHTML = `
          <div class="result-item">
            <div style="color: #ff5e62; font-weight: bold; margin-bottom: 5px;">⚠️ API Rate Limit Reached</div>
            <div>Using cached/fallback data. Prices may not be current.</div>
          </div>
        `;

    // Try to use fallback data
    const fallbackResults = Object.values(popularCryptos)
      .filter(
        (crypto) =>
          crypto.name.toLowerCase().includes(searchTerm) ||
          crypto.symbol.toLowerCase().includes(searchTerm)
      )
      .map((crypto) => ({
        id: crypto.id,
        name: crypto.name,
        symbol: crypto.symbol,
        image: `https://assets.coingecko.com/coins/images/${getCoinImageId(
          crypto.id
        )}/small/${crypto.id}.png`,
        current_price: crypto.price,
        price_change_percentage_24h: crypto.change,
        total_volume: crypto.price * 1000000000 * (0.8 + Math.random() * 0.4), // More realistic volume
        market_cap: crypto.price * 10000000000 * (0.8 + Math.random() * 0.4), // More realistic market cap
        is_fallback_data: true, // Mark as fallback data for transparency
      }));

    if (fallbackResults.length > 0) {
      // Display results with clear indication they are fallback data
      displaySearchResults(fallbackResults, searchResults, event);
    } else {
      searchResults.innerHTML +=
        '<div class="result-item">No matching cryptocurrencies found in fallback data.</div>';
    }
    return;
  }

  // Increment count and save
  rateLimitInfo.count++;
  try {
    localStorage.setItem("cg_rate_limit", JSON.stringify(rateLimitInfo));
  } catch (e) {
    console.warn("Failed to save rate limit info:", e);
  }

  try {
    // First check if search is already in progress for this term
    if (searchInProgress[searchTerm]) {
      console.log("Search already in progress, waiting for results...");
      return;
    }

    searchInProgress[searchTerm] = true;

    // Use CoinGecko search API endpoint with proper error handling
    const searchUrl = `https://api.coingecko.com/api/v3/search?query=${encodeURIComponent(
      searchTerm
    )}`;

    // Check for cached search results first
    const cacheKey = `search_${searchTerm}`;
    const cachedResults = apiCache.get(cacheKey);

    if (cachedResults) {
      console.log("Using cached search results");
      displaySearchResults(cachedResults, searchResults, event);
      searchInProgress[searchTerm] = false;
      return;
    }

    // Use the throttler for this request
    await new Promise((resolve, reject) => {
      requestThrottler.add(
        // Request function
        () =>
          fetch(searchUrl).then((response) => {
            if (response.status === 429) {
              throw { status: 429, message: "Rate limit reached" };
            }
            if (!response.ok) {
              throw {
                status: response.status,
                message: `API search request failed with status ${response.status}`,
              };
            }
            return response.json();
          }),
        // Success handler
        async (data) => {
          // Extract coin data from response
          const coins = data.coins || [];

          if (coins.length === 0) {
            searchResults.innerHTML =
              '<div class="result-item">No results found</div>';
            searchInProgress[searchTerm] = false;
            resolve();
            return;
          }

          // Limit to top 5 results to avoid overwhelming the user
          const topResults = coins.slice(0, 5);

          // Show temporary results with loading state
          searchResults.innerHTML = "";
          topResults.forEach((coin) => {
            const resultItem = document.createElement("div");
            resultItem.className = "result-item loading-item";
            resultItem.innerHTML = `
                  <img src="${coin.thumb}" class="result-icon" alt="${
              coin.name
            }">
                  <div class="result-info">
                    <div class="result-name">${coin.name}</div>
                    <div class="result-symbol">${coin.symbol.toUpperCase()}</div>
                  </div>
                  <div class="search-loading-spinner" style="width: 12px; height: 12px;"></div>
                `;
            searchResults.appendChild(resultItem);
          });

          try {
            // Fetch detailed information for each coin - one at a time to avoid rate limits
            const detailedResults = [];

            for (const coin of topResults) {
              try {
                // Check if we have coin details in the cache
                const coinCacheKey = `coin_${coin.id}`;
                const cachedCoinDetails = apiCache.get(coinCacheKey);

                if (cachedCoinDetails) {
                  detailedResults.push(cachedCoinDetails);
                  continue;
                }

                // Increment API request count
                rateLimitInfo.count++;
                localStorage.setItem(
                  "cg_rate_limit",
                  JSON.stringify(rateLimitInfo)
                );

                // Check if we're over rate limit protection threshold
                if (rateLimitInfo.count >= 25) {
                  // Use fallback for remaining coins
                  const fallback = popularCryptos[coin.id] || {
                    id: coin.id,
                    name: coin.name,
                    symbol: coin.symbol.toUpperCase(),
                    price: "N/A",
                    change: 0,
                  };

                  const fallbackResult = {
                    id: fallback.id,
                    name: fallback.name,
                    symbol: fallback.symbol,
                    image: coin.large || coin.thumb,
                    current_price:
                      fallback.price === "N/A" ? "N/A" : fallback.price,
                    price_change_percentage_24h: fallback.change,
                    total_volume: "N/A",
                    market_cap: "N/A",
                    is_fallback_data: true, // Mark as fallback data
                  };

                  // Generate fake sparkline data
                  fallbackResult.sparkline_in_7d = {
                    price: generateFakeSparkline(
                      fallbackResult.current_price,
                      fallbackResult.price_change_percentage_24h > 0
                    ),
                  };

                  detailedResults.push(fallbackResult);
                  continue;
                }

                const detailUrl = `https://api.coingecko.com/api/v3/coins/${coin.id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=true`;

                // Fetch with error handling
                const fetchResult = await fetch(detailUrl);

                if (fetchResult.status === 429) {
                  // Fall back to basic info on rate limit
                  const fallback = popularCryptos[coin.id] || {
                    price: "N/A",
                    change: 0,
                  };

                  const basicInfo = {
                    id: coin.id,
                    name: coin.name,
                    symbol: coin.symbol.toUpperCase(),
                    image: coin.large || coin.thumb,
                    current_price:
                      fallback.price === "N/A" ? "N/A" : fallback.price,
                    price_change_percentage_24h: fallback.change,
                    total_volume: "N/A",
                    market_cap: "N/A",
                    is_fallback_data: true, // Mark as fallback data
                  };

                  // Generate fake sparkline data
                  basicInfo.sparkline_in_7d = {
                    price: generateFakeSparkline(
                      basicInfo.current_price,
                      basicInfo.price_change_percentage_24h > 0
                    ),
                  };

                  detailedResults.push(basicInfo);
                  // Still cache this limited data
                  apiCache.set(coinCacheKey, basicInfo);

                  // Update our rate limit info
                  rateLimitInfo.count = 30; // Force slowdown
                  localStorage.setItem(
                    "cg_rate_limit",
                    JSON.stringify(rateLimitInfo)
                  );

                  continue;
                }

                if (!fetchResult.ok) {
                  throw new Error(`Failed to get details for ${coin.id}`);
                }

                const detail = await fetchResult.json();

                // Ensure we have valid data with fallbacks
                const currentPrice = detail.market_data?.current_price?.usd;
                const priceChange =
                  detail.market_data?.price_change_percentage_24h || 0;
                const totalVolume = detail.market_data?.total_volume?.usd;
                const marketCap = detail.market_data?.market_cap?.usd;

                // Format the data to match our existing structure
                const coinDetail = {
                  id: detail.id,
                  name: detail.name,
                  symbol: detail.symbol.toUpperCase(),
                  image: detail.image?.large || coin.large || coin.thumb,
                  current_price:
                    currentPrice !== undefined && currentPrice !== null
                      ? currentPrice
                      : "N/A",
                  price_change_percentage_24h: priceChange,
                  total_volume:
                    totalVolume !== undefined && totalVolume !== null
                      ? totalVolume
                      : "N/A",
                  market_cap:
                    marketCap !== undefined && marketCap !== null
                      ? marketCap
                      : "N/A",
                  sparkline_in_7d: detail.market_data?.sparkline_7d || null,
                };

                detailedResults.push(coinDetail);

                // Cache the individual coin detail
                apiCache.set(coinCacheKey, coinDetail);

                // Wait a bit longer between requests to avoid rate limiting
                await new Promise((resolve) => setTimeout(resolve, 600));
              } catch (error) {
                console.error(`Error fetching details for ${coin.id}:`, error);

                // Use fallback data on error
                const fallback = popularCryptos[coin.id] || {
                  price: "N/A",
                  change: 0,
                };

                const fallbackResult = {
                  id: coin.id,
                  name: coin.name,
                  symbol: coin.symbol.toUpperCase(),
                  image: coin.large || coin.thumb,
                  current_price:
                    fallback.price === "N/A" ? "N/A" : fallback.price,
                  price_change_percentage_24h: fallback.change,
                  total_volume: "N/A",
                  market_cap: "N/A",
                  is_fallback_data: true, // Mark as fallback data
                };

                // Generate fake sparkline data
                fallbackResult.sparkline_in_7d = {
                  price: generateFakeSparkline(
                    fallbackResult.current_price,
                    fallbackResult.price_change_percentage_24h > 0
                  ),
                };

                detailedResults.push(fallbackResult);
              }
            }

            // Cache these results for future use
            apiCache.set(cacheKey, detailedResults);

            // Try to fetch sparkline data for all results
            try {
              const coinIds = detailedResults.map((c) => c.id).join(",");
              const sparklineUrl = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${coinIds}&sparkline=true&price_change_percentage=24h`;
              const sparklineResponse = await fetch(sparklineUrl);

              if (sparklineResponse.ok) {
                const sparklineData = await sparklineResponse.json();

                // Add sparkline data to detailed results
                for (let i = 0; i < detailedResults.length; i++) {
                  const matchingCoin = sparklineData.find(
                    (s) => s.id === detailedResults[i].id
                  );
                  if (matchingCoin && matchingCoin.sparkline_in_7d) {
                    detailedResults[i].sparkline_in_7d =
                      matchingCoin.sparkline_in_7d;
                  }
                }

                // Update the cache with the sparkline data
                apiCache.set(cacheKey, detailedResults);
              }
            } catch (e) {
              console.error("Failed to fetch sparkline data:", e);
            }

            // Display final results
            displaySearchResults(detailedResults, searchResults, event);
            searchInProgress[searchTerm] = false;
            resolve();
          } catch (error) {
            console.error("Error processing search details:", error);
            searchResults.innerHTML =
              '<div class="result-item">Error obtaining details. Using limited data.</div>';

            // Use basic info from the search
            const basicResults = topResults.map((coin) => ({
              id: coin.id,
              name: coin.name,
              symbol: coin.symbol.toUpperCase(),
              image: coin.large || coin.thumb,
              current_price: "N/A",
              price_change_percentage_24h: 0,
              total_volume: "N/A",
              market_cap: "N/A",
            }));

            // Try to fetch sparkline data for these basic results
            try {
              const coinIds = basicResults.map((c) => c.id).join(",");
              const sparklineUrl = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${coinIds}&sparkline=true&price_change_percentage=24h`;
              const sparklineResponse = await fetch(sparklineUrl);

              if (sparklineResponse.ok) {
                const sparklineData = await sparklineResponse.json();

                // Add sparkline data to basic results
                for (let i = 0; i < basicResults.length; i++) {
                  const matchingCoin = sparklineData.find(
                    (s) => s.id === basicResults[i].id
                  );
                  if (matchingCoin) {
                    if (matchingCoin.sparkline_in_7d) {
                      basicResults[i].sparkline_in_7d =
                        matchingCoin.sparkline_in_7d;
                    }
                    // Also update price data if available
                    if (matchingCoin.current_price) {
                      basicResults[i].current_price =
                        matchingCoin.current_price;
                    }
                    if (matchingCoin.price_change_percentage_24h) {
                      basicResults[i].price_change_percentage_24h =
                        matchingCoin.price_change_percentage_24h;
                    }
                  }
                }
              }
            } catch (e) {
              console.error(
                "Failed to fetch sparkline data for basic results:",
                e
              );
            }

            displaySearchResults(basicResults, searchResults, event);
          }

          searchInProgress[searchTerm] = false;
          resolve();
        },
        // Error handler
        (error) => {
          console.error("Error searching CoinGecko:", error);

          if (error.status === 429) {
            searchResults.innerHTML =
              '<div class="result-item">API rate limit reached. Using fallback data.</div>';

            // If rate limited, use popular cryptos as fallback
            const fallbackResults = Object.values(popularCryptos)
              .filter(
                (crypto) =>
                  crypto.name.toLowerCase().includes(searchTerm) ||
                  crypto.symbol.toLowerCase().includes(searchTerm)
              )
              .map((crypto) => ({
                id: crypto.id,
                name: crypto.name,
                symbol: crypto.symbol,
                image: `https://assets.coingecko.com/coins/images/${getCoinImageId(
                  crypto.id
                )}/small/${crypto.id}.png`,
                current_price: crypto.price,
                price_change_percentage_24h: crypto.change,
                total_volume: 1000000000,
                market_cap: 10000000000,
              }));

            if (fallbackResults.length > 0) {
              // Generate fake sparkline data as a fallback
              for (let i = 0; i < fallbackResults.length; i++) {
                // Generate 168 random price points (24 * 7 = week of hourly data)
                const fakePrices = Array.from({ length: 168 }, () => {
                  const basePrice = fallbackResults[i].current_price || 100;
                  const randomFactor = 1 + (Math.random() * 0.1 - 0.05); // ±5% variation
                  return basePrice * randomFactor;
                });

                fallbackResults[i].sparkline_in_7d = { price: fakePrices };
              }

              displaySearchResults(fallbackResults, searchResults, event);

              // Try to fetch real sparkline data in the background
              const coinIds = fallbackResults.map((c) => c.id).join(",");
              const sparklineUrl = `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${coinIds}&sparkline=true&price_change_percentage=24h`;

              fetch(sparklineUrl)
                .then((response) => {
                  if (response.ok) return response.json();
                  throw new Error("Failed to fetch sparkline data");
                })
                .then((sparklineData) => {
                  // Create updated results with real sparkline data
                  const updatedResults = [...fallbackResults];

                  // Add sparkline data to results
                  for (let i = 0; i < updatedResults.length; i++) {
                    const matchingCoin = sparklineData.find(
                      (s) => s.id === updatedResults[i].id
                    );
                    if (matchingCoin && matchingCoin.sparkline_in_7d) {
                      updatedResults[i].sparkline_in_7d =
                        matchingCoin.sparkline_in_7d;
                    }
                  }

                  // Update the display with real data
                  displaySearchResults(updatedResults, searchResults, event);
                })
                .catch((e) => {
                  console.error(
                    "Failed to fetch sparkline data for fallback results:",
                    e
                  );
                });
            } else {
              searchResults.innerHTML +=
                '<div class="result-item">No matches in fallback data.</div>';
            }

            // Update our rate limit info - assume we're at limit
            rateLimitInfo.count = 30;
            localStorage.setItem(
              "cg_rate_limit",
              JSON.stringify(rateLimitInfo)
            );
          } else {
            searchResults.innerHTML =
              '<div class="result-item">Error searching. Try again later.</div>';
          }

          searchInProgress[searchTerm] = false;
          reject(error);
        }
      );
    });
  } catch (error) {
    console.error("Error in search flow:", error);
    searchResults.innerHTML =
      '<div class="result-item">Error searching. Try again later.</div>';
    searchInProgress[searchTerm] = false;
  }
}

/**
 * Display search results in the dropdown
 * @param {Array} cryptos - Array of cryptocurrency data objects
 * @param {HTMLElement} searchResults - The results container element
 * @param {Event} event - The event that triggered the search
 */
function displaySearchResults(cryptos, searchResults, event) {
  // Clear previous results
  searchResults.innerHTML = "";

  // Create result items
  cryptos.forEach((crypto) => {
    const resultItem = document.createElement("div");
    resultItem.className = "result-item";

    // Check if this is fallback data and add indicator if it is
    if (crypto.is_fallback_data) {
      resultItem.classList.add("fallback-data");
    }

    // Create icon with error handling
    const backgroundColor = `#${Math.floor(Math.random() * 16777215).toString(
      16
    )}`;
    let iconHTML = "";

    if (crypto.image) {
      // Create image with fallback
      iconHTML = `
            <img 
              src="${crypto.image}" 
              class="result-icon" 
              alt="${crypto.name}" 
              onerror="this.onerror=null; this.style.display='none'; this.parentNode.innerHTML='<div class=\\'result-icon-fallback\\' style=\\'background-color: ${backgroundColor}\\'>${crypto.symbol
        .charAt(0)
        .toUpperCase()}</div>';"
            >
          `;
    } else {
      // Fallback icon using first letter of symbol
      iconHTML = `
            <div class="result-icon-fallback" style="background-color: ${backgroundColor}">
              ${crypto.symbol.charAt(0).toUpperCase()}
            </div>
          `;
    }

    // Create the URL for the coin on CoinGecko
    const coinUrl = `https://www.coingecko.com/en/coins/${crypto.id}`;

    // Check if price change is available
    const priceChange = crypto.price_change_percentage_24h || 0;
    const isPositive = priceChange > 0;

    // Format price for display
    const formattedPrice =
      crypto.current_price === "N/A"
        ? "N/A"
        : `$${formatPrice(crypto.current_price)}`;

    // Add fallback data indicator if needed
    const fallbackIndicator = crypto.is_fallback_data
      ? '<div class="fallback-indicator">⚠️ Estimated Data</div>'
      : "";

    resultItem.innerHTML = `
          ${iconHTML}
          <div class="result-info">
            <div class="result-name">
              <a href="${coinUrl}" target="_blank" rel="noopener noreferrer" class="crypto-name-link" title="View ${
      crypto.name
    } on CoinGecko">
                ${crypto.name}
              </a>
              ${fallbackIndicator}
            </div>
            <div class="result-symbol">${crypto.symbol.toUpperCase()}</div>
            <div class="result-price ${isPositive ? "positive" : "negative"}">
              ${formattedPrice} <span class="result-change">${
      isPositive ? "↑" : "↓"
    } ${Math.abs(priceChange).toFixed(2)}%</span>
            </div>
            <div class="price-chart-container">
              <canvas class="mini-chart" id="search-chart-${
                crypto.id
              }"></canvas>
            </div>
          </div>
        `;

    // We'll keep the click behavior on the entire result item to show the modal
    // but clicking specifically on the name link will go to CoinGecko
    resultItem.addEventListener("click", function (e) {
      // Only show modal if the click wasn't on the name link
      if (!e.target.closest(".crypto-name-link")) {
        showCryptoModal(crypto);
        searchResults.classList.remove("active");
        event.target.value = "";
      }
    });

    searchResults.appendChild(resultItem);

    // Create sparkline chart if sparkline data is available
    if (crypto.sparkline_in_7d && crypto.sparkline_in_7d.price) {
      // Slight delay to ensure the canvas is in the DOM
      setTimeout(() => {
        createSparklineChart(
          `search-chart-${crypto.id}`,
          crypto.sparkline_in_7d.price,
          isPositive
        );
      }, 10);
    } else {
      // Show "No Data Available" message instead of generating fake data
      setTimeout(() => {
        createNoDataChart(`search-chart-${crypto.id}`);
      }, 10);
    }
  });

  searchResults.classList.add("active");
}

/**
 * Generate fake sparkline data for a given price
 * @param {number|string} price - The current price to base the fake data on
 * @param {boolean} isPositive - Whether the trend should be positive or negative
 * @returns {Array} - Array of price points for sparkline
 */
function generateFakeSparkline(price, isPositive) {
  // Handle case where price is "N/A"
  const basePrice = price === "N/A" ? 100 : parseFloat(price);

  // Create 168 data points (24h * 7d)
  const sparkline = [];
  let currentPrice = basePrice;

  for (let i = 0; i < 168; i++) {
    // Create a slight trend in the direction of isPositive
    const trendFactor = isPositive ? 1.0002 : 0.9998;
    // Add some randomness
    const randomFactor = 0.99 + Math.random() * 0.02; // 99% to 101%

    currentPrice = currentPrice * trendFactor * randomFactor;
    sparkline.push(currentPrice);
  }

  return sparkline;
}

/**
 * Show detailed modal for a cryptocurrency
 * Creates a modal popup with comprehensive information
 * @param {Object} crypto - The cryptocurrency data object
 */
function showCryptoModal(crypto) {
  // Remove any existing modal
  let existingModal = document.querySelector(".modal-overlay");
  if (existingModal) {
    document.body.removeChild(existingModal);
  }

  // Create modal overlay
  const modalOverlay = document.createElement("div");
  modalOverlay.className = "modal-overlay";

  // Create crypto card for modal
  const modalCard = document.createElement("div");
  modalCard.className = "modal-crypto-card";

  // Handle the case where price change might be missing
  const priceChange = crypto.price_change_percentage_24h || 0;
  const isPositive = priceChange > 0;

  // Format prices and values correctly
  const formattedPrice =
    crypto.current_price === "N/A"
      ? "N/A"
      : `$${formatPrice(crypto.current_price)}`;
  const formattedVolume =
    crypto.total_volume === "N/A"
      ? "N/A"
      : `$${formatLargeNumber(crypto.total_volume)}`;
  const formattedMarketCap =
    crypto.market_cap === "N/A"
      ? "N/A"
      : `$${formatLargeNumber(crypto.market_cap)}`;

  // Create the URL for the coin on CoinGecko
  const coinUrl = `https://www.coingecko.com/en/coins/${crypto.id}`;

  // Add fallback data warning if applicable
  const fallbackWarning = crypto.is_fallback_data
    ? '<div class="modal-warning">⚠️ Showing estimated data due to API limitations</div>'
    : "";

  modalCard.innerHTML = `
        <button class="modal-close" title="Close cryptocurrency details">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        ${fallbackWarning}
        <div class="card-header">
          ${
            crypto.image
              ? `<div class="crypto-icon">
               <img src="${crypto.image}" alt="${crypto.name}" 
                    onerror="this.onerror=null; this.style.display='none'; this.parentNode.innerHTML='${crypto.symbol
                      .charAt(0)
                      .toUpperCase()}';">
             </div>`
              : `<div class="crypto-icon-fallback" style="background-color: #${Math.floor(
                  Math.random() * 16777215
                ).toString(16)}">
              ${crypto.symbol.charAt(0).toUpperCase()}
            </div>`
          }
          <div class="crypto-title">
            <div class="crypto-name">
              <a href="${coinUrl}" target="_blank" rel="noopener noreferrer" class="crypto-name-link" title="View ${
    crypto.name
  } on CoinGecko">
                ${crypto.name}
              </a>
            </div>
            <div class="crypto-symbol">${crypto.symbol.toUpperCase()}</div>
          </div>
        </div>
        <div class="card-body">
          <div class="price">${formattedPrice}</div>
          <div class="price-chart-container">
            <canvas class="mini-chart" id="modal-chart-${crypto.id}"></canvas>
          </div>
          <div class="price-change ${isPositive ? "positive" : "negative"}">
            ${isPositive ? "↑" : "↓"} ${Math.abs(priceChange).toFixed(2)}%
          </div>
          <div class="stats">
            <div class="stat-item">
              <div class="stat-label">Volume (24h)</div>
              <div class="stat-value">${formattedVolume}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Market Cap</div>
              <div class="stat-value">${formattedMarketCap}</div>
            </div>
          </div>
        </div>
      `;

  // Add modal to the document
  modalOverlay.appendChild(modalCard);
  document.body.appendChild(modalOverlay);

  // Add slight delay before adding active class to trigger animation
  setTimeout(() => {
    modalOverlay.classList.add("active");

    // Create chart if sparkline data is available
    if (crypto.sparkline_in_7d && crypto.sparkline_in_7d.price) {
      createSparklineChart(
        `modal-chart-${crypto.id}`,
        crypto.sparkline_in_7d.price,
        isPositive
      );
    } else {
      // Show "No Data Available" message instead of generating fake data
      createNoDataChart(`modal-chart-${crypto.id}`);
    }
  }, 10);

  // Close modal event
  const closeButton = modalOverlay.querySelector(".modal-close");
  closeButton.addEventListener("click", function () {
    closeModal(modalOverlay);
  });

  // Close modal when clicking outside the card
  modalOverlay.addEventListener("click", function (event) {
    if (event.target === modalOverlay) {
      closeModal(modalOverlay);
    }
  });

  // Close modal on Escape key
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeModal(modalOverlay);
    }
  });
}

/**
 * Close the modal with animation
 * @param {HTMLElement} modalOverlay - The modal overlay element
 */
function closeModal(modalOverlay) {
  modalOverlay.classList.remove("active");

  // Remove modal after animation completes
  setTimeout(() => {
    if (modalOverlay.parentNode) {
      document.body.removeChild(modalOverlay);
    }
  }, 300);
}

/**
 * Helper function to get the correct image ID for popular cryptocurrencies
 * Maps cryptocurrency IDs to their CoinGecko image IDs
 * @param {string} coinId - The cryptocurrency ID
 * @returns {number} - The corresponding image ID for CoinGecko URLs
 */
function getCoinImageId(coinId) {
  // Common coin mappings based on CoinGecko's image repository
  const coinImageMap = {
    bitcoin: 1,
    ethereum: 279,
    tether: 325,
    binancecoin: 825,
    ripple: 44,
    dogecoin: 5,
    cardano: 2010,
    solana: 4128,
    polkadot: 12171,
    "the-open-network": 16638,
  };

  return coinImageMap[coinId] || 1; // Default to 1 if not found
}

/**
 * Create a "No Data Available" message using an HTML overlay
 * @param {string} elementId - The ID of the canvas element
 */
function createNoDataChart(elementId) {
  const canvas = document.getElementById(elementId);
  if (!canvas) {
    console.warn(`Canvas element with ID ${elementId} not found`);
    return;
  }

  // Destroy any existing chart on this canvas
  if (canvas.chart) {
    canvas.chart.destroy();
  }

  // Get the parent container
  const container = canvas.parentElement;
  if (!container) return;

  // Remove any existing no-data overlay
  const existingOverlay = container.querySelector(".no-data-overlay");
  if (existingOverlay) {
    container.removeChild(existingOverlay);
  }

  // Create the overlay
  const overlay = document.createElement("div");
  overlay.className = "no-data-overlay";
  overlay.innerHTML = "<span>No Chart Data</span>";

  // Add the overlay
  canvas.style.display = "none";
  container.appendChild(overlay);
}
