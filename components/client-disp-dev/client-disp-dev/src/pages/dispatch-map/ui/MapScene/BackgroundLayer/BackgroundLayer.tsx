import { useEffect, useState } from 'react';
import type { Texture } from 'three';
import { CanvasTexture, LinearFilter } from 'three';

import { toast } from '@/shared/ui/Toast';

import { MAP_SCENE } from '../../../config/map-scene';
import { METERS_TO_SCENE } from '../../../lib/coordinates';
import { useBackgroundLayer } from '../../../lib/hooks/useBackgroundLayer';

const TEXTURE_MAX_SIDE = 4096;
const DEFAULT_PLANE_SIZE = 1000;
const MM_TO_METERS = 0.00166;

/**
 * Парсит SVG, извлекает реальные размеры из viewBox (в мм)
 * и выставляет атрибуты width/height для качественной растеризации в canvas.
 *
 * @returns Размеры в мм, размеры canvas и модифицированный SVG-текст, или null.
 */
function prepareSvg(svgText: string) {
  const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  const svg = doc.querySelector('svg');
  if (!svg) return null;

  let width = 0;
  let height = 0;

  const viewBox = svg.getAttribute('viewBox');
  if (viewBox) {
    const parts = viewBox.split(/[\s,]+/).map(Number);
    if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
      width = parts[2];
      height = parts[3];
    }
  }

  if (!width || !height) {
    width = parseFloat(svg.getAttribute('width') ?? '') || 0;
    height = parseFloat(svg.getAttribute('height') ?? '') || 0;
  }

  if (!width || !height) return null;

  const aspect = width / height;
  const canvasWidth = aspect >= 1 ? TEXTURE_MAX_SIDE : Math.round(TEXTURE_MAX_SIDE * aspect);
  const canvasHeight = aspect >= 1 ? Math.round(TEXTURE_MAX_SIDE / aspect) : TEXTURE_MAX_SIDE;

  svg.setAttribute('width', String(canvasWidth));
  svg.setAttribute('height', String(canvasHeight));

  return {
    width,
    height,
    canvasWidth,
    canvasHeight,
    modifiedSvgText: new XMLSerializer().serializeToString(doc),
  };
}

/**
 * Рендерит подложку текущего горизонта на карте.
 */
export function BackgroundLayer() {
  const props = useBackgroundLayer();

  const [texture, setTexture] = useState<Texture | null>(null);
  const [planeWidth, setPlaneWidth] = useState(DEFAULT_PLANE_SIZE);
  const [planeHeight, setPlaneHeight] = useState(DEFAULT_PLANE_SIZE);

  const planeCenterX = props?.centerX ?? 0;
  const planeCenterZ = props?.centerZ ?? 0;

  useEffect(() => {
    if (!props?.url) return;

    let cancelled = false;
    let objectUrl: string | null = null;
    let createdTexture: Texture | null = null;

    const load = async () => {
      const response = await fetch(props.url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const svgText = await response.text();
      const svgData = prepareSvg(svgText);

      if (!svgData) {
        throw new Error('Failed to parse SVG dimensions');
      }

      const blob = new Blob([svgData.modifiedSvgText], { type: 'image/svg+xml' });
      objectUrl = URL.createObjectURL(blob);

      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = objectUrl;
      await img.decode();

      if (cancelled) return;

      const canvas = document.createElement('canvas');
      canvas.width = svgData.canvasWidth;
      canvas.height = svgData.canvasHeight;

      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('Canvas 2D context unavailable');
      }

      ctx.drawImage(img, 0, 0, svgData.canvasWidth, svgData.canvasHeight);

      const tex = new CanvasTexture(canvas);
      tex.minFilter = LinearFilter;
      tex.magFilter = LinearFilter;
      tex.needsUpdate = true;

      createdTexture = tex;
      setTexture(tex);
      setPlaneWidth(svgData.width * MM_TO_METERS * METERS_TO_SCENE);
      setPlaneHeight(svgData.height * MM_TO_METERS * METERS_TO_SCENE);
    };

    load().catch(() => {
      toast.error({ message: 'Не удалось загрузить подложку' });

      if (!cancelled) {
        setTexture(null);
      }
    });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
      setTexture(null);
      createdTexture?.dispose();
    };
  }, [props?.url]);

  if (!texture) return null;

  return (
    <mesh
      position={[planeCenterX, MAP_SCENE.BACKGROUND_Y, planeCenterZ]}
      rotation={[-Math.PI / 2, 0, 0]}
      renderOrder={MAP_SCENE.BACKGROUND_Y}
    >
      <planeGeometry args={[planeWidth, planeHeight]} />
      <meshBasicMaterial
        map={texture}
        opacity={props?.opacity}
        transparent
        depthWrite={false}
      />
    </mesh>
  );
}
