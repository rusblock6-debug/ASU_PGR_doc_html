/**
 * Компонент для отрисовки обычного ребра графа в 3D
 */
import React from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import { GraphNode } from '../../types/graph';
import { useSettings } from '../../hooks/useSettings';

interface EdgeLineProps {
  fromNode: GraphNode;
  toNode: GraphNode;
  levelColor?: string;  // Цвет из уровня (если не задан - используем дефолт)
}

// ОПТИМИЗАЦИЯ: React.memo предотвращает лишние ререндеры при неизменных props
export const EdgeLine = React.memo(function EdgeLine({ fromNode, toNode, levelColor }: EdgeLineProps) {
  const settings = useSettings();
  
  // ОПТИМИЗАЦИЯ: Мемоизируем вычисление точек для предотвращения лишних вычислений при ререндерах
  const points = React.useMemo(() => {
    // Преобразуем GPS координаты узлов в Canvas координаты
    const fromCanvas = settings.transformGPStoCanvas(fromNode.y, fromNode.x);
    const toCanvas = settings.transformGPStoCanvas(toNode.y, toNode.x);
    
    return [
      new THREE.Vector3(fromCanvas.x, fromNode.z, -fromCanvas.y),
      new THREE.Vector3(toCanvas.x, toNode.z, -toCanvas.y),
    ];
  }, [fromNode.x, fromNode.y, fromNode.z, toNode.x, toNode.y, toNode.z, settings]);
  
  return (
    <Line
      points={points}
      color={levelColor || '#2196F3'}  // Используем цвет из уровня или дефолтный синий
      lineWidth={3}
    />
  );
}, (prevProps, nextProps) => {
  // Кастомная функция сравнения для оптимизации
  return (
    prevProps.fromNode.id === nextProps.fromNode.id &&
    prevProps.fromNode.x === nextProps.fromNode.x &&
    prevProps.fromNode.y === nextProps.fromNode.y &&
    prevProps.fromNode.z === nextProps.fromNode.z &&
    prevProps.toNode.id === nextProps.toNode.id &&
    prevProps.toNode.x === nextProps.toNode.x &&
    prevProps.toNode.y === nextProps.toNode.y &&
    prevProps.toNode.z === nextProps.toNode.z &&
    prevProps.levelColor === nextProps.levelColor
  );
});



