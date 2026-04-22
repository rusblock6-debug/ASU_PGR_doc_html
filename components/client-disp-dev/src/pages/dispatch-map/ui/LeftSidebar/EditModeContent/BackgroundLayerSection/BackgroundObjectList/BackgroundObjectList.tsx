import { useState } from 'react';

import type { SubstrateResponse } from '@/shared/api/endpoints/substrates';
import { useDeleteSubstrateMutation, useUpdateSubstrateMutation } from '@/shared/api/endpoints/substrates';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import SunlightLight from '@/shared/assets/icons/ic-sunlight-light.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import type { SortState } from '@/shared/lib/sort-by-field';
import { Select } from '@/shared/ui/Select';
import { toast } from '@/shared/ui/Toast';
import { Tooltip } from '@/shared/ui/Tooltip';

import type { BackgroundUploadState } from '../../../../../lib/hooks/useBackgroundUpload';
import type { BackgroundSortField } from '../../../../../model/types';
import { IconButton } from '../../../IconButton';
import { SortIconButton } from '../../../SortIconButton';
import { BrightnessPopover } from '../BrightnessPopover';

import styles from './BackgroundObjectList.module.css';

/**
 * Пропсы компонента списка подложек.
 */
interface BackgroundObjectListProps {
  /** Список подложек. */
  readonly substrates: readonly SubstrateResponse[];
  /** Отсортированный список подложек. */
  readonly sortedSubstrates: readonly SubstrateResponse[];
  /** Готовый список для селектора. */
  readonly selectOptions: readonly { readonly value: string; readonly label: string }[];
  /** Текущее состояние сортировки. */
  readonly sortState: SortState<BackgroundSortField>;
  /** Событие на изменение сортировки. */
  readonly onSortChange: (field: BackgroundSortField) => void;
  /** Состояние загрузки. */
  readonly uploadState: BackgroundUploadState | null;
  /** Флаг состояние текущей загрузки. */
  readonly isFileUploading: boolean;
  /** Событие на замену подложки конкретного горизонта. */
  readonly onUploadHorizonChange: (value: string | null) => Promise<void>;
  /** Событие на отмену загрузки подложки. */
  readonly onCancelUpload: () => void;
}

/**
 * Grid-список подложек с возможностью смены горизонта, удаления и настройки яркости.
 * Не занимается загрузкой файлов и сортировкой — получает всё уже подготовленным через пропсы.
 */
export function BackgroundObjectList({
  substrates,
  sortedSubstrates,
  selectOptions,
  sortState,
  onSortChange,
  uploadState,
  isFileUploading,
  onUploadHorizonChange,
  onCancelUpload,
}: BackgroundObjectListProps) {
  const confirm = useConfirm();

  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [updatingHorizonId, setUpdatingHorizonId] = useState<number | null>(null);
  const [updateSubstrate] = useUpdateSubstrateMutation();
  const [deleteSubstrate] = useDeleteSubstrateMutation();

  const handleRowHorizonChange = async (substrate: SubstrateResponse, value: string | null) => {
    const newHorizonId = hasValue(value) && value !== '' ? Number(value) : null;

    if (newHorizonId === substrate.horizon_id) return;

    if (hasValue(newHorizonId)) {
      const conflicting = substrates.find((item) => item.horizon_id === newHorizonId && item.id !== substrate.id);

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
        await deleteSubstrate(conflicting.id).unwrap();
      }
    }

    setUpdatingHorizonId(substrate.id);

    try {
      await updateSubstrate({
        id: substrate.id,
        body: { horizon_id: newHorizonId },
      }).unwrap();
      toast.success({ message: 'Подложка обновлена' });
    } catch {
      toast.error({ message: 'Не удалось обновить подложку' });
    } finally {
      setUpdatingHorizonId((current) => (current === substrate.id ? null : current));
    }
  };

  const handleDelete = async (id: number) => {
    const isConfirmed = await confirm({
      title: 'Удалить подложку?',
      message: 'Подложка будет удалена без возможности восстановления.',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (!isConfirmed) return;

    setDeletingId(id);

    try {
      await deleteSubstrate(id).unwrap();
      toast.success({ message: 'Подложка удалена' });
    } catch {
      toast.error({ message: 'Возникла ошибка при удалении подложки' });
    } finally {
      setDeletingId((current) => (current === id ? null : current));
    }
  };

  return (
    <div className={styles.list}>
      <div
        className={styles.header}
        role="row"
      >
        <span className={styles.header_name}>
          Наименование
          <SortIconButton
            field="name"
            sortState={sortState}
            onSortChange={onSortChange}
          />
        </span>
        <span className={styles.header_horizon}>
          Горизонт
          <SortIconButton
            field="horizon"
            sortState={sortState}
            onSortChange={onSortChange}
          />
        </span>
        <span className={styles.actions} />
      </div>

      {uploadState && (
        <div className={styles.row}>
          <div className={styles.name_cell}>
            <span className={styles.spinner_inline} />
            <span className={cn(styles.name, styles.upload_label, 'truncate')}>
              {uploadState.fileName || 'Загрузка файла'}
            </span>
            <IconButton
              title="Отменить загрузку"
              aria-label="Отменить загрузку"
              onClick={onCancelUpload}
            >
              <CrossIcon />
            </IconButton>
          </div>

          <Select
            labelPosition="vertical"
            variant="combobox-primary"
            inputSize="combobox-xs"
            data={selectOptions}
            value={hasValue(uploadState.horizonId) ? String(uploadState.horizonId) : ''}
            onChange={onUploadHorizonChange}
            disabled={isFileUploading}
            searchable
          />

          <span className={styles.actions} />
        </div>
      )}

      {sortedSubstrates.map((substrate) => {
        const isUpdating = updatingHorizonId === substrate.id;

        return (
          <div
            key={substrate.id}
            className={styles.row}
          >
            <div className={styles.name_cell}>
              {isUpdating && <span className={styles.spinner_inline} />}
              <Tooltip label={substrate.original_filename}>
                <span className={cn(styles.name, 'truncate')}>{substrate.original_filename}</span>
              </Tooltip>
              <IconButton
                title="Удалить подложку"
                aria-label="Удалить подложку"
                onClick={() => {
                  if (!isUpdating) {
                    void handleDelete(substrate.id);
                  }
                }}
              >
                {deletingId === substrate.id ? <span className={styles.spinner_inline} /> : <TrashIcon />}
              </IconButton>
            </div>

            <Select
              labelPosition="vertical"
              variant="combobox-primary"
              inputSize="combobox-xs"
              data={selectOptions}
              value={hasValue(substrate.horizon_id) ? String(substrate.horizon_id) : ''}
              onChange={(value) => handleRowHorizonChange(substrate, value)}
              disabled={isFileUploading || isUpdating}
              searchable
            />

            <span className={styles.actions}>
              <BrightnessPopover substrate={substrate}>
                <SunlightLight />
              </BrightnessPopover>
            </span>
          </div>
        );
      })}
    </div>
  );
}
