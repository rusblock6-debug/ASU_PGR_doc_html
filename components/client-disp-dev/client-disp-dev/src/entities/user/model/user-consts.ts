export const UserRole = {
  ADMIN: 'ADMIN',
  USER: 'USER',
  MANAGER: 'MANAGER',
} as const;

export type UserRoleType = (typeof UserRole)[keyof typeof UserRole];
