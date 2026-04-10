import { useRef, useState, type ChangeEvent } from 'react';

import type { SubstrateResponse } from '@/shared/api/endpoints/substrates';
import {
  useCreateSubstrateMutation,
  useDeleteSubstrateMutation,
  useUpdateSubstrateMutation,
} from '@/shared/api/endpoints/substrates';
import { useConfirm } from '@/shared/lib/confirm';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { toast } from '@/shared/ui/Toast';

/**
 * Состояние текущей загрузки файла подложки.
 */
export interface BackgroundUploadState {
  /** Имя файла. */
  readonly fileName: string;
  /** Идентификатор горизонта. */
  readonly horizonId: number | null;
}

/**
 * Параметры и данные для инициализации хука загрузки подложек.
 */
interface UseBackgroundUploadParams {
  /** Список подложек. */
  readonly substrates: readonly SubstrateResponse[];
  /** Список горизонтов. */
  readonly horizons: readonly { readonly id: number; readonly height: number }[];
}

/**
 * Хук отвечает за загрузку файлов подложки и выбор горизонта во время загрузки.
 * Инкапсулирует работу с RTK-мутаторами, confirm-модалкой и toast-уведомлениями.
 */
export function useBackgroundUpload({ substrates, horizons }: UseBackgroundUploadParams) {
  const [uploadState, setUploadState] = useState<BackgroundUploadState | null>(null);
  const [isFileUploading, setIsFileUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadCanceledRef = useRef(false);
  const uploadHorizonRef = useRef<number | null>(null);

  const [createSubstrate] = useCreateSubstrateMutation();
  const [updateSubstrate] = useUpdateSubstrateMutation();
  const [deleteSubstrate] = useDeleteSubstrateMutation();

  const uploadRequestRef = useRef<ReturnType<typeof createSubstrate> | null>(null);

  const confirm = useConfirm();

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const [file] = Array.from(event.target.files ?? []);

    if (!file) return;

    uploadCanceledRef.current = false;
    uploadHorizonRef.current = null;

    setUploadState({
      fileName: file.name,
      horizonId: null,
    });
    setIsFileUploading(true);

    const request = createSubstrate({ file });

    uploadRequestRef.current = request;

    try {
      const created = await request.unwrap();

      if (uploadCanceledRef.current) {
        await deleteSubstrate(created.id).unwrap();
        return;
      }

      const horizonId = uploadHorizonRef.current;

      if (hasValue(horizonId)) {
        await updateSubstrate({
          id: created.id,
          body: { horizon_id: horizonId },
        }).unwrap();
      }

      const horizon = horizonId !== null ? (horizons.find((item) => item.id === horizonId) ?? null) : null;

      const message = horizon
        ? `Файл загружен и привязан к горизонту ${formatNumber(horizon.height)} м`
        : 'Файл загружен';

      toast.success({ message });
    } catch {
      if (!uploadCanceledRef.current) {
        toast.error({ message: 'Не удалось загрузить подложку' });
      }
    } finally {
      uploadRequestRef.current = null;
      setIsFileUploading(false);
      setUploadState(null);
    }
  };

  const handleCancelUpload = () => {
    uploadCanceledRef.current = true;
    uploadRequestRef.current?.abort?.();
    uploadRequestRef.current = null;
    setUploadState(null);
    toast.success({ message: 'Загрузка файла отменена' });
  };

  const handleUploadHorizonChange = async (value: string | null) => {
    const newHorizonId = hasValueNotEmpty(value) ? Number(value) : null;

    if (!uploadState) {
      uploadHorizonRef.current = newHorizonId;
      return;
    }

    if (hasValue(newHorizonId)) {
      const conflicting = substrates.find((item) => item.horizon_id === newHorizonId);

      if (conflicting) {
        const isConfirmed = await confirm({
          title: 'Вы действительно хотите изменить подложку у горизонта?',
          message: 'Предыдущий файл будет удалён',
          confirmText: 'Изменить',
          cancelText: 'Отмена',
        });

        if (!isConfirmed) {
          return;
        }
        try {
          await deleteSubstrate(conflicting.id).unwrap();
        } catch {
          toast.error({ message: 'Возникла ошибка замены подложки' });
        }
      }
    }

    uploadHorizonRef.current = newHorizonId;

    setUploadState({
      fileName: uploadState.fileName,
      horizonId: newHorizonId,
    });
  };

  return {
    fileInputRef,
    uploadState,
    isFileUploading,
    handleUploadClick,
    handleFileChange,
    handleCancelUpload,
    handleUploadHorizonChange,
  };
}
