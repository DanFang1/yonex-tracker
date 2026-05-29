import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, deleteProduct, addProduct } from '../api/products';
import './Dashboard.css';

export default function Dashboard() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [productUrl, setProductUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const fetchProducts = useCallback(async () => {
    try {
      const response = await getDashboard();
      setProducts(Array.isArray(response.data.products) ? response.data.products : []);
    } catch (err) {
      setError('Failed to load dashboard');
      if (err.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

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

  const handleDeleteProduct = async (productId) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      try {
        await deleteProduct(productId);
        fetchProducts();
      } catch (err) {
        alert('Failed to delete product');
      }
    }
  };

  const filteredProducts = products.filter((product) =>
    product[1].toLowerCase().includes(searchQuery.toLowerCase())
  );

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
            <span className="search-icon">&#128269;</span>
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

          {filteredProducts.map((product) => (
            <div key={product[0]} className="product-item">
              <div className="product-item-info">
                <span className="product-item-name">{product[1]}</span>
                <span className="product-item-target">Target: ${product[3]}</span>
              </div>
              <div className="product-item-right">
                <span className="product-item-price">${product[2]}</span>
                <button
                  className="product-item-delete"
                  onClick={() => handleDeleteProduct(product[0])}
                  title="Remove"
                >
                  &#10005;
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <span className="tracked-count">{products.length} product{products.length !== 1 ? 's' : ''} tracked</span>
          <button className="logout-btn" onClick={() => navigate('/login')}>Logout</button>
        </div>
      </aside>

      <main className="main-content">
        {/* Right panel — coming soon */}
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
