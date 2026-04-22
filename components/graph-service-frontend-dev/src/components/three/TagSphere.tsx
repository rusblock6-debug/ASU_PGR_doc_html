/**
 * Компонент для отрисовки метки в 3D
 */
import React from 'react';
import { Sphere, Text, Billboard } from '@react-three/drei';
import { Tag } from '../../types/graph';
import { useSettings } from '../../hooks/useSettings';
import { getPlaceLonLat } from '../../utils/placeLocation';

interface TagSphereProps {
  tag: Tag;
}


// ОПТИМИЗАЦИЯ: React.memo предотвращает лишние ререндеры при неизменных props
export const TagSphere = React.memo(function TagSphere({ tag }: TagSphereProps) {
  const settings = useSettings();
  
  // Преобразуем GPS координаты метки в Canvas координаты (метры)
  // В legacy режиме координаты могут быть в tag.place.location (в т.ч. GeoJSON) или в tag.x/tag.y
  const lonLat = React.useMemo(() => (tag.place ? getPlaceLonLat(tag.place) : null), [tag]);
  const gpsLat = lonLat?.lat ?? (tag.y ?? 0);
  const gpsLon = lonLat?.lon ?? (tag.x ?? 0);
  const canvasCoords = React.useMemo(
    () => settings.transformGPStoCanvas(gpsLat, gpsLon),
    [gpsLat, gpsLon, settings]
  );

  const radius = tag.radius || 25;
  
  return (
    <group position={[canvasCoords.x, tag.z || 0, -canvasCoords.y]}>
      {/* Зона действия - прозрачная сфера ярко-оранжевого цвета */}
      <Sphere args={[radius, 16, 16]} renderOrder={0}>
        <meshBasicMaterial
          color="#FF6600" // Ярко-оранжевый цвет
          transparent
          opacity={0.1} // Увеличена прозрачность для лучшей видимости элементов
          depthWrite={false} // Не записывать в буфер глубины, чтобы не перекрывать другие объекты
        />
      </Sphere>

      {/* Центр метки (сердцевина) - ярко-оранжевая, увеличенная для лучшей видимости */}
      <Sphere args={[2.5, 16, 16]}>
        <meshStandardMaterial 
          color="#FF6600" // Ярко-оранжевый цвет
          emissive="#FF8844" // Свечение для лучшей видимости
          emissiveIntensity={0.8}
          metalness={0.1}
          roughness={0.3}
        />
      </Sphere>
      
      {/* Название метки - поднято выше, чтобы не перекрывалось радиусом, повернуто к экрану */}
      <Billboard
        position={[0, radius + 15, 0]}
        follow={true}
        lockX={false}
        lockY={false}
        lockZ={false}
      >
        <Text
          fontSize={3.8}
          color="#FEFCF9"
          anchorX="center"
          anchorY="middle"
          position={[0, 0, 0]}
          outlineWidth={0.5}
          outlineColor="#000000"
        >
          {tag.name || tag.beacon_id || tag.tag_id || 'Tag'}
        </Text>
      </Billboard>
      
    </group>
  );
}, (prevProps, nextProps) => {
  // Кастомная функция сравнения для оптимизации
  return (
    prevProps.tag.id === nextProps.tag.id &&
    prevProps.tag.x === nextProps.tag.x &&
    prevProps.tag.y === nextProps.tag.y &&
    prevProps.tag.z === nextProps.tag.z &&
    prevProps.tag.radius === nextProps.tag.radius &&
    prevProps.tag.name === nextProps.tag.name
  );
});



