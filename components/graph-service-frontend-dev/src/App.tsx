/**
 * Основной компонент приложения с роутингом
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import GraphEditor from './components/GraphEditor';
import ThreeView from './components/ThreeView';
import './App.css';

function App() {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/" element={<ThreeView />} />
        <Route path="/2d" element={<GraphEditor />} />
        <Route path="/3d-view" element={<ThreeView />} />
      </Routes>
    </Router>
  );
}

export default App;