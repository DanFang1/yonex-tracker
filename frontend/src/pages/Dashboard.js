import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, deleteProduct, addProduct, getPriceGraph } from '../api/products';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import './Dashboard.css';

const TIME_RANGES = ['1M', '3M', '6M', 'All'];

function filterByRange(data, range) {
  if (range === 'All' || !data.length) return data;
  const days = range === '1M' ? 30 : range === '3M' ? 90 : 180;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return data.filter(d => new Date(d.date) >= cutoff);
}

export default function Dashboard() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [productUrl, setProductUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [graphData, setGraphData] = useState([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [timeRange, setTimeRange] = useState('3M');
  const navigate = useNavigate();

  const fetchProducts = useCallback(async () => {
    try {
      const response = await getDashboard();
      setProducts(Array.isArray(response.data.products) ? response.data.products : []);
    } catch (err) {
      setError('Failed to load dashboard');
      if (err.response?.status === 401) navigate('/login');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const handleSelectProduct = async (product) => {
    setSelected(product);
    setTimeRange('3M');
    setGraphLoading(true);
    try {
      const response = await getPriceGraph(product[0]);
      setGraphData(response.data.data);
    } catch {
      setGraphData([]);
    } finally {
      setGraphLoading(false);
    }
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    try {
      await addProduct(productUrl, targetPrice);
      setProductUrl('');
      setTargetPrice('');
      setShowAddForm(false);
      fetchProducts();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to add product');
    }
  };

  const handleDeleteProduct = async (productId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this product?')) {
      try {
        await deleteProduct(productId);
        if (selected && selected[0] === productId) setSelected(null);
        fetchProducts();
      } catch {
        alert('Failed to delete product');
      }
    }
  };

  const filteredProducts = products.filter(p =>
    p[1].toLowerCase().includes(searchQuery.toLowerCase())
  );

  const visibleGraphData = filterByRange(graphData, timeRange);
  const prices = visibleGraphData.map(d => d.price);
  const lowestEver = prices.length ? Math.min(...prices) : null;
  const highestEver = prices.length ? Math.max(...prices) : null;

  if (loading) return <div className="app-shell"><div className="loading">Loading...</div></div>;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-logo">&#9775;</span>
          <span className="topbar-name"><strong>YONEX</strong> Price Tracker</span>
        </div>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="search-bar">
              <input
                type="text"
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="product-list">
            {error && <p className="sidebar-error">{error}</p>}
            {filteredProducts.length === 0 && !error && (
              <p className="sidebar-empty">
                {products.length === 0 ? 'No products tracked yet.' : 'No results found.'}
              </p>
            )}
            {filteredProducts.map((product) => {
              const currentPrice = parseFloat(product[2]);
              const initialPrice = product[4] ? parseFloat(product[4]) : null;
              const pctChange = initialPrice && initialPrice !== 0
                ? ((currentPrice - initialPrice) / initialPrice) * 100
                : null;
              const pctLabel = pctChange !== null
                ? `${pctChange >= 0 ? '+' : ''}${pctChange.toFixed(1)}%`
                : null;
              const pctClass = pctChange === null ? '' : pctChange < 0 ? 'pct-down' : 'pct-up';
              const isActive = selected && selected[0] === product[0];

              return (
                <div
                  key={product[0]}
                  className={`product-item${isActive ? ' product-item--active' : ''}`}
                  onClick={() => handleSelectProduct(product)}
                >
                  <div className="product-item-info">
                    <span className="product-item-name">{product[1]}</span>
                    <span className="product-item-target">Target: ${product[3]}</span>
                  </div>
                  <div className="product-item-right">
                    <div className="product-item-price-col">
                      <span className="product-item-price">${currentPrice.toFixed(2)}</span>
                      {pctLabel && (
                        <span className={`product-item-pct ${pctClass}`}>{pctLabel}</span>
                      )}
                    </div>
                    <button
                      className="product-item-delete"
                      onClick={(e) => handleDeleteProduct(product[0], e)}
                      title="Remove"
                    >
                      &#10005;
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="sidebar-footer">
            <span className="tracked-count">{products.length} product{products.length !== 1 ? 's' : ''} tracked</span>
            <button className="logout-btn" onClick={() => navigate('/login')}>Logout</button>
          </div>
        </aside>

        <main className="main-content">
          {!selected ? (
            <div className="detail-empty">
              <p>Select a product to view details</p>
            </div>
          ) : (
            <div className="detail-panel">
              <div className="detail-header">
                <div className="detail-header-left">
                  <h1 className="detail-name">{selected[1]}</h1>
                  <a
                    className="detail-buy-btn"
                    href={selected[5]}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Buy Now
                  </a>
                </div>
                <div className="detail-header-right">
                  <span className="detail-current-price">${parseFloat(selected[2]).toFixed(2)}</span>
                </div>
              </div>

              <div className="stat-cards">
                <div className="stat-card">
                  <span className="stat-label">CURRENT PRICE</span>
                  <span className="stat-value stat-blue">${parseFloat(selected[2]).toFixed(2)}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">LOWEST EVER</span>
                  <span className="stat-value stat-green">
                    {lowestEver !== null ? `$${lowestEver.toFixed(2)}` : '—'}
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">HIGHEST EVER</span>
                  <span className="stat-value stat-red">
                    {highestEver !== null ? `$${highestEver.toFixed(2)}` : '—'}
                  </span>
                </div>
              </div>

              <div className="chart-section">
                <div className="chart-header">
                  <span className="chart-title">PRICE HISTORY</span>
                  <div className="time-range-btns">
                    {TIME_RANGES.map(r => (
                      <button
                        key={r}
                        className={`time-btn${timeRange === r ? ' time-btn--active' : ''}`}
                        onClick={() => setTimeRange(r)}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {graphLoading ? (
                  <div className="chart-loading">Loading chart...</div>
                ) : visibleGraphData.length === 0 ? (
                  <div className="chart-loading">No data for this range.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={visibleGraphData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: '#6e7681', fontSize: 11 }}
                        axisLine={{ stroke: '#21262d' }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: '#6e7681', fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={v => `$${v}`}
                        width={60}
                        domain={['auto', 'auto']}
                      />
                      <Tooltip
                        contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}
                        labelStyle={{ color: '#8b949e', fontSize: 12 }}
                        itemStyle={{ color: '#58a6ff' }}
                        formatter={v => [`$${v.toFixed(2)}`, 'Price']}
                      />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="#58a6ff"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: '#58a6ff' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {showAddForm && (
        <div className="add-modal-overlay" onClick={() => setShowAddForm(false)}>
          <form
            className="add-modal"
            onSubmit={handleAddProduct}
            onClick={(e) => e.stopPropagation()}
          >
            <h3>Track a Product</h3>
            <input
              type="url"
              placeholder="Product URL"
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
              required
            />
            <input
              type="number"
              placeholder="Target Price"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              required
            />
            <div className="add-modal-actions">
              <button type="button" onClick={() => setShowAddForm(false)}>Cancel</button>
              <button type="submit">Add</button>
            </div>
          </form>
        </div>
      )}

      <button className="fab" onClick={() => setShowAddForm(true)} title="Track a product">+</button>
    </div>
  );
}
