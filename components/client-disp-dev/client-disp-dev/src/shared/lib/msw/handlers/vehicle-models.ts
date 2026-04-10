import { delay, http, HttpResponse } from 'msw';

import type { EquipmentModel, EquipmentModelsApiResponse } from '@/shared/api/endpoints/equipment-models';

import { mswConfig } from '../config';
import { generateVehicleModels } from '../generators';

const vehicleModelsDb: EquipmentModel[] = generateVehicleModels(mswConfig.dictionarySize);

export const vehicleModelsHandlers = [
  // GET /api/vehicle-models
  http.get('/api/vehicle-models', async ({ request }) => {
    await delay(mswConfig.delay);

    const url = new URL(request.url);
    const page = Number(url.searchParams.get('page')) || 1;
    const size = Number(url.searchParams.get('size')) || 100;
    const consist = url.searchParams.get('consist');

    let filtered = vehicleModelsDb;

    if (consist) {
      filtered = filtered.filter((m) => m.name.toLowerCase().includes(consist.toLowerCase()));
    }

    const total = filtered.length;
    const pages = Math.ceil(total / size);
    const start = (page - 1) * size;
    const items = filtered.slice(start, start + size);

    const response: EquipmentModelsApiResponse = {
      items,
      total,
      page,
      size,
      pages,
    };

    return HttpResponse.json(response);
  }),

  // GET /api/vehicle-models/:id
  http.get('/api/vehicle-models/:id', async ({ params }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const model = vehicleModelsDb.find((m) => m.id === id);

    if (!model) {
      return new HttpResponse(null, { status: 404 });
    }

    return HttpResponse.json(model);
  }),

  // POST /api/vehicle-models
  http.post('/api/vehicle-models', async ({ request }) => {
    await delay(mswConfig.delay);

    const body = (await request.json()) as Partial<EquipmentModel>;
    const newId = Math.max(...vehicleModelsDb.map((m) => m.id), 0) + 1;
    const now = new Date().toISOString();

    const newModel: EquipmentModel = {
      id: newId,
      name: body.name ?? `Model-${newId}`,
      max_speed: body.max_speed ?? null,
      tank_volume: body.tank_volume ?? null,
      load_capacity_tons: body.load_capacity_tons ?? null,
      volume_m3: body.volume_m3 ?? null,
      created_at: now,
      updated_at: now,
    };

    vehicleModelsDb.push(newModel);

    return HttpResponse.json(newModel, { status: 201 });
  }),

  // PUT /api/vehicle-models/:id
  http.put('/api/vehicle-models/:id', async ({ params, request }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const modelIndex = vehicleModelsDb.findIndex((m) => m.id === id);

    if (modelIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }

    const body = (await request.json()) as Partial<EquipmentModel>;
    const updatedModel: EquipmentModel = {
      ...vehicleModelsDb[modelIndex],
      ...body,
      updated_at: new Date().toISOString(),
    };

    vehicleModelsDb[modelIndex] = updatedModel;

    return HttpResponse.json(updatedModel);
  }),

  // DELETE /api/vehicle-models/:id
  http.delete('/api/vehicle-models/:id', async ({ params }) => {
    await delay(mswConfig.delay);

    const id = Number(params.id);
    const modelIndex = vehicleModelsDb.findIndex((m) => m.id === id);

    if (modelIndex === -1) {
      return new HttpResponse(null, { status: 404 });
    }

    vehicleModelsDb.splice(modelIndex, 1);

    return new HttpResponse(null, { status: 204 });
  }),
];
