/**
 * Компонент для отрисовки узла графа в 3D
 */
import React from 'react';
import { Sphere } from '@react-three/drei';
import { GraphNode } from '../../types/graph';
import { useSettings } from '../../hooks/useSettings';

interface NodeSphereProps {
  node: GraphNode;
  isSelected?: boolean;
}

// ОПТИМИЗАЦИЯ: React.memo предотвращает лишние ререндеры при неизменных props
export const NodeSphere = React.memo(function NodeSphere({ node, isSelected }: NodeSphereProps) {
  const settings = useSettings();
  const color = node.node_type === 'road' ? '#4CAF50' : node.node_type === 'ladder' ? '#9C27B0' : '#2196F3';
  
  // Преобразуем GPS координаты узла в Canvas координаты (метры)
  // node.x = longitude (GPS градусы), node.y = latitude (GPS градусы)
  const canvasCoords = React.useMemo(
    () => settings.transformGPStoCanvas(node.y, node.x),
    [node.y, node.x, settings]
  );
  
  return (
    <Sphere
      position={[canvasCoords.x, node.z, -canvasCoords.y]}  // Canvas координаты в метрах
      args={[1.6, 10, 10]}  // Соответствует ядру меток
    >
      <meshBasicMaterial  // Используем meshBasicMaterial вместо meshStandardMaterial (быстрее)
        color={isSelected ? '#FF5722' : color}
      />
    </Sphere>
  );
}, (prevProps, nextProps) => {
  // Кастомная функция сравнения для оптимизации
  // Компонент обновляется только если изменились критичные поля
  return (
    prevProps.node.id === nextProps.node.id &&
    prevProps.node.x === nextProps.node.x &&
    prevProps.node.y === nextProps.node.y &&
    prevProps.node.z === nextProps.node.z &&
    prevProps.node.node_type === nextProps.node.node_type &&
    prevProps.isSelected === nextProps.isSelected
  );
});



