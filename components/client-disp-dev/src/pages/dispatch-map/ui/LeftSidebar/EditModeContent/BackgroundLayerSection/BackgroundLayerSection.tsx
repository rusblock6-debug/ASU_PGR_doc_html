import { Collapsible } from '@/shared/ui/Collapsible';

import { useBackgroundSubstrates } from '../../../../lib/hooks/useBackgroundSubstrates';
import { useBackgroundUpload } from '../../../../lib/hooks/useBackgroundUpload';
import { useTreeNodeExpanded } from '../../../../lib/hooks/useTreeNodeExpanded';
import { TreeNode } from '../../../../model/types';
import { AddButton } from '../../AddButton';

import { BackgroundObjectList } from './BackgroundObjectList';

/**
 * Секция «Подложка» — сворачиваемый список фоновых слоёв карты.
 */
export function BackgroundLayerSection() {
  const [isExpanded, toggle] = useTreeNodeExpanded(TreeNode.BACKGROUND_LAYERS);
  const { substrates, sortedSubstrates, selectOptions, sortState, handleSortChange, horizons } =
    useBackgroundSubstrates();
  const {
    fileInputRef,
    uploadState,
    isFileUploading,
    handleUploadClick,
    handleFileChange,
    handleCancelUpload,
    handleUploadHorizonChange,
  } = useBackgroundUpload({ substrates, horizons });

  return (
    <>
      <Collapsible
        label="Подложка"
        opened={isExpanded}
        onToggle={toggle}
        disabled={substrates.length === 0}
        leftSection={<AddButton onClick={handleUploadClick} />}
      >
        <BackgroundObjectList
          substrates={substrates}
          sortedSubstrates={sortedSubstrates}
          selectOptions={selectOptions}
          sortState={sortState}
          onSortChange={handleSortChange}
          uploadState={uploadState}
          isFileUploading={isFileUploading}
          onUploadHorizonChange={handleUploadHorizonChange}
          onCancelUpload={handleCancelUpload}
        />
      </Collapsible>

      <input
        type="file"
        accept=".dwg,.dxf,.svg,.pdf"
        className="g-screen-reader-only"
        id="background-substrate-upload"
        onChange={handleFileChange}
        ref={fileInputRef}
      />
    </>
  );
}
