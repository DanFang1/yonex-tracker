import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, deleteProduct, addProduct, getPriceGraph} from '../api/products';
import PriceGraph from '../components/PriceGraph';
import './Dashboard.css';


export default function Dashboard() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [productUrl, setProductUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [showGraph, setShowGraph] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [graphProductName, setGraphProductName] = useState('');
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
      alert(err.response?.data || 'Failed to add product');
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

  const handleViewGraph = async (productId, productName) => {
    try {
      const response = await getPriceGraph(productId);
      setGraphData(response.data.data);
      setGraphProductName(productName);
      setShowGraph(true);
    } catch (err) {
      alert('Failed to view graph');
    }
  };

  const handleCloseGraph = () => {
    setShowGraph(false);
    setGraphData(null);
    setGraphProductName('');
  };
    
  if (loading) return <div className="dashboard">Loading...</div>;

  return (
    <div className="dashboard"> 
      <header className="dashboard-header">
        <h1 id="title-font">Yonex Tracker</h1>    
      </header>

      <div className="dashboard-content">
      {error && <p className="error">{error}</p>}

      {showAddForm && (
        <form className="add-product-form" onSubmit={handleAddProduct}>
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
          <button type="submit">Add Product</button>
        </form>
      )}

      <div className="products-grid">
        {products.map((product) => (
          <div key={product[0]} className="product-card">
            <h3>{product[1]}</h3>
            <p>Current Price: <strong>${product[2]}</strong></p>
            <p>Target Price: <strong>${product[3]}</strong></p>
            <button 
              className="delete-btn"
              onClick={() => handleViewGraph(product[0], product[1])}
            >
              Graph
            </button>
            <button
              className="delete-btn"
              onClick={() => handleDeleteProduct(product[0])}
            >
              Delete
            </button>
          </div>
        ))}
      </div>

      {products.length === 0 && (
        <p className="empty-state">No products tracked yet. Add one to get started!</p>
      )}
      </div> 

      <button 
        className="add-btn"
        onClick={() => setShowAddForm(!showAddForm)}
      >
        {showAddForm ? 'Cancel' : '+'}
      </button>

      <button id="logout-button" onClick={() => navigate('/login')}>Logout</button>

      {showGraph && (
        <PriceGraph 
          data={graphData} 
          productName={graphProductName}
          onClose={handleCloseGraph}
        />
      )}
    </div>
  );
}
