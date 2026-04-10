import { createContext, useContext } from 'react';

/**
 * Контекст для определения, находится ли компонент внутри WorkspacePage.
 * Используется для условной активации drag-and-drop функционала.
 */
const Workspace = createContext(false);

/** Провайдер контекста Workspace. */
export const WorkspaceProvider = Workspace.Provider;

/** Хук для проверки, находится ли компонент внутри WorkspacePage. */
export const useIsInWorkspace = () => useContext(Workspace);
