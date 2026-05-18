import axios from 'axios';

const client = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  withCredentials: true, // Enable cookies for session
});

export default client;
