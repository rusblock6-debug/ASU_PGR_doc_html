/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

/**
 * Дополнительные переменные окружения, используемые в клиенте.
 */
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_TRIP_SERVICE_URL?: string;
  readonly VITE_VEHICLE_ID?: string;
  readonly VITE_KIOSK_VEHICLE_LABEL?: string;
  readonly VITE_KIOSK_DRIVER_NAME?: string;
}

/**
 * Расширение ImportMeta с типизированным env.
 */
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
