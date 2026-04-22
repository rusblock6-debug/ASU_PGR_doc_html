import { Skeleton as MantineSkeleton, type SkeletonProps as MantineSkeletonProps } from '@mantine/core';

/**
 * Представляет компонент скелетона.
 */
export function Skeleton(props: Readonly<MantineSkeletonProps>) {
  return <MantineSkeleton {...props} />;
}
