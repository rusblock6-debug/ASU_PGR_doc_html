import { delay, http, HttpResponse } from 'msw';

import type { Vehicle, VehiclesResponse } from '@/shared/api/endpoints/vehicles';

import { mswConfig } from '../config';
import { generateVehicles } from '../generators';

const vehiclesDb: Vehicle[] = generateVehicles(mswConfig.paginatedListSize);

export const vehiclesHandlers = [
  // GET /api/vehicles
  http.get('/api/vehicles', async ({ request }) => {
    await delay(mswConfig.delay);

    const url = new URL(request.url);
    const page = Number(url.searchParams.get('page')) || 1;
    const size = Number(url.searchParams.get('size')) || 100;
    const vehicleType = url.searchParams.get('vehicle_type');

    let filtered = vehiclesDb;

    if (vehicleType) {
      filtered = filtered.filter((v) => v.vehicle_type === vehicleType);
    }

    const total = filtered.length;
    const pages = Math.ceil(total / size);
    const start = (page - 1) * size;
    const items = filtered.slice(start, start + size);

    const response: VehiclesResponse = {
      items,
      total,
      page,
      size,
      pages,
    };

    return HttpResponse.json(response);
  }),

  // GET /api/vehicles/:id
  http.get('/api/vehicles/:id', async ({ params }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const vehicle = vehiclesDb.find((v) => v.id === id);

    if (!vehicle) {
      return new HttpResponse(null, { status: 404 });
    }

    return HttpResponse.json(vehicle);
  }),

  // POST /api/vehicles
  http.post('/api/vehicles', async ({ request }) => {
    await delay(mswConfig.delay);

    const body = (await request.json()) as Partial<Vehicle>;
    const newId = Math.max(...vehiclesDb.map((v) => v.id), 0) + 1;
    const now = new Date().toISOString();

    const newVehicle: Vehicle = {
      id: newId,
      enterprise_id: body.enterprise_id ?? 1,
      vehicle_type: body.vehicle_type ?? 'shas',
      name: body.name ?? `VEHICLE-${newId}`,
      model_id: body.model_id ?? null,
      model: null,
      serial_number: body.serial_number ?? null,
      registration_number: body.registration_number ?? null,
      status: body.status ?? 'active',
      is_active: body.is_active ?? true,
      active_from: body.active_from ?? now,
      active_to: body.active_to ?? null,
      created_at: now,
      updated_at: now,
    };

    vehiclesDb.push(newVehicle);

    return HttpResponse.json(newVehicle, { status: 201 });
  }),

  // PUT /api/vehicles/:id
  http.put('/api/vehicles/:id', async ({ params, request }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const vehicleIndex = vehiclesDb.findIndex((v) => v.id === id);

    if (vehicleIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }

    const body = (await request.json()) as Partial<Vehicle>;
    const updatedVehicle: Vehicle = {
      ...vehiclesDb[vehicleIndex],
      ...body,
      updated_at: new Date().toISOString(),
    };

    vehiclesDb[vehicleIndex] = updatedVehicle;

    return HttpResponse.json(updatedVehicle);
  }),

  // DELETE /api/vehicles/:id
  http.delete('/api/vehicles/:id', async ({ params }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const vehicleIndex = vehiclesDb.findIndex((v) => v.id === id);

    if (vehicleIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }

    vehiclesDb.splice(vehicleIndex, 1);

    return new HttpResponse(null, { status: 204 });
  }),
];
