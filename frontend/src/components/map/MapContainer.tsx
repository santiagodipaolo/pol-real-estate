"use client";

import { useRef, useEffect, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapContainerProps {
  className?: string;
  center?: [number, number];
  zoom?: number;
  onMapReady?: (map: maplibregl.Map) => void;
  children?: React.ReactNode;
}

const BUENOS_AIRES_CENTER: [number, number] = [-58.4370, -34.6083];
const STYLE_URL =
  process.env.NEXT_PUBLIC_MAPLIBRE_STYLE ||
  "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export default function MapContainer({
  className = "w-full h-full",
  center = BUENOS_AIRES_CENTER,
  zoom = 12,
  onMapReady,
  children,
}: MapContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center,
      zoom,
      minZoom: 10,
      maxZoom: 18,
      maxBounds: [
        [-58.65, -34.80],
        [-58.25, -34.50],
      ],
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      setIsReady(true);
      onMapReady?.(map);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={`relative ${className}`}>
      <div ref={containerRef} className="w-full h-full rounded-lg" />
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-100 rounded-lg">
          <p className="text-slate-400 animate-pulse">Cargando mapa...</p>
        </div>
      )}
      {children}
    </div>
  );
}
