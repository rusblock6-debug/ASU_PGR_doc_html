/**
 * Компонент для отрисовки винтообразного ребра (лестницы) в 3D
 */
import React from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import { GraphNode } from '../../types/graph';
import { useSettings } from '../../hooks/useSettings';

interface SpiralEdgeProps {
  fromNode: GraphNode;
  toNode: GraphNode;
  levelColor?: string;  // Цвет из уровня (если не задан - используем дефолт)
}

// ОПТИМИЗАЦИЯ: React.memo предотвращает лишние ререндеры при неизменных props
export const SpiralEdge = React.memo(function SpiralEdge({ fromNode, toNode, levelColor }: SpiralEdgeProps) {
  const settings = useSettings();
  
  const spiralPoints = React.useMemo(() => {
    // Преобразуем GPS координаты узлов в Canvas координаты
    const fromCanvas = settings.transformGPStoCanvas(fromNode.y, fromNode.x);
    const toCanvas = settings.transformGPStoCanvas(toNode.y, toNode.x);
    
    const height = Math.abs(toNode.z - fromNode.z);
    const spiralRadius = 12; // Радиус спирали 12 метров для проезда самосвала
    const turnsPerHeight = 1 / 15; // 1 виток на 15 метров высоты (~10° угол подъема)
    const totalTurns = Math.max(height * turnsPerHeight, 0.5); // Минимум 0.5 оборота
    const segments = Math.ceil(totalTurns * 32); // 32 сегмента на оборот для плавности
    
    const points: THREE.Vector3[] = [];
    
    // Определяем нижний и верхний узлы
    const lowerNode = fromNode.z < toNode.z ? fromNode : toNode;
    const upperNode = fromNode.z < toNode.z ? toNode : fromNode;
    const lowerCanvas = fromNode.z < toNode.z ? fromCanvas : toCanvas;
    const upperCanvas = fromNode.z < toNode.z ? toCanvas : fromCanvas;
    
    // Начальная и конечная точки (в Canvas координатах)
    const startX = lowerCanvas.x;
    const startY = lowerCanvas.y;
    const startZ = lowerNode.z;
    const endX = upperCanvas.x;
    const endY = upperCanvas.y;
    const endZ = upperNode.z;
    
    // Центр спирали
    const centerX = (startX + endX) / 2;
    const centerY = (startY + endY) / 2;
    
    // Начальный угол - от центра к нижнему узлу
    const startAngle = Math.atan2(startY - centerY, startX - centerX);
    
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const currentZ = startZ + (endZ - startZ) * t;
      
      // Плавное изменение радиуса: начинаем от точки, расширяемся, затем сужаемся к точке
      let radiusFactor: number;
      if (t < 0.1) {
        // Первые 10% - расширение от точки
        radiusFactor = t / 0.1;
      } else if (t > 0.9) {
        // Последние 10% - сужение к точке
        radiusFactor = (1 - t) / 0.1;
      } else {
        // Середина - полный радиус
        radiusFactor = 1;
      }
      
      const currentRadius = spiralRadius * radiusFactor;
      
      // Угол спирали
      const spiralAngle = startAngle + (t * totalTurns * Math.PI * 2);
      
      // Координаты точки на спирали
      const x = centerX + Math.cos(spiralAngle) * currentRadius;
      const y = centerY + Math.sin(spiralAngle) * currentRadius;
      
      // Линейная интерполяция от начальной к конечной точке (для плавного перехода на краях)
      const finalX = startX + (endX - startX) * t;
      const finalY = startY + (endY - startY) * t;
      
      // Первые и последние 5% - прямая линия к/от узлов, остальное - спираль
      points.push(new THREE.Vector3(
        t < 0.05 || t > 0.95 ? finalX : x,
        currentZ,
        t < 0.05 || t > 0.95 ? -finalY : -y
      ));
    }
    
    return points;
  }, [fromNode.x, fromNode.y, fromNode.z, toNode.x, toNode.y, toNode.z, settings]);
  
  return (
    <Line
      points={spiralPoints}
      color={levelColor || '#9C27B0'}  // Используем цвет из уровня или дефолтный фиолетовый
      lineWidth={6}
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



