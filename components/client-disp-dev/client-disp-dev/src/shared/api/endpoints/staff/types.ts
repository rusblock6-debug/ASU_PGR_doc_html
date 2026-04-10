import type { Pagination } from '@/shared/api/types';

/** Представляет модель единицы персонала. */
export interface Staff {
  /** Возвращает идентификатор. */
  readonly staff_id: number;
  /** Возвращает имя. */
  readonly name: string;
  /** Возвращает фамилию. */
  readonly surname: string;
  /** Возвращает табельный номер. */
  readonly personnel_number: string;
  /** Возвращает имя пользователя для авторизации. */
  readonly username: string;
  /** Возвращает пароль. */
  readonly password: string;
  /** Возвращает идентификатор пользователя. */
  readonly user_id: number;
  /** Возвращает идентификатор роли. */
  readonly role_id: number;
  /** Возвращает наименование роли. */
  readonly role_name: string;
  /** Возвращает отчество. */
  readonly patronymic?: string | null;
  /** Возвращает дату рождения. */
  readonly birth_date?: string | null;
  /** Возвращает номер телефона. */
  readonly phone?: string | null;
  /** Возвращает адрес электронной почты. */
  readonly email?: string | null;
  /** Возвращает позицию. */
  readonly position?: string | null;
  /** Возвращает отдел. */
  readonly department?: string | null;
}

/** Представляет модель данных, получаемую по запросу персонала. */
export interface StaffResponse extends Pagination {
  /** Возвращает список персонала. */
  readonly items: readonly Staff[];
}

/** Представляет модель данных для создания единицы персонала. */
export interface CreateStaffRequest {
  /** Возвращает имя. */
  readonly name: string;
  /** Возвращает фамилию. */
  readonly surname: string;
  /** Возвращает табельный номер. */
  readonly personnel_number: string;
  /** Возвращает имя пользователя для авторизации. */
  readonly username: string;
  /** Возвращает пароль. */
  readonly password: string;
  /** Возвращает идентификатор роли. */
  readonly role_id: number;
  /** Возвращает отчество. */
  readonly patronymic?: string | null;
  /** Возвращает дату рождения. */
  readonly birth_date?: string | null;
  /** Возвращает номер телефона. */
  readonly phone?: string | null;
  /** Возвращает адрес электронной почты. */
  readonly email?: string | null;
  /** Возвращает позицию. */
  readonly position?: string | null;
  /** Возвращает отдел. */
  readonly department?: string | null;
}

/** Представляет модель данных для редактирования единицы персонала. */
export interface UpdateStaffRequest {
  /** Возвращает имя. */
  readonly name?: string | null;
  /** Возвращает фамилию. */
  readonly surname?: string | null;
  /** Возвращает отчество. */
  readonly patronymic?: string | null;
  /** Возвращает табельный номер. */
  readonly personnel_number?: string | null;
  /** Возвращает имя пользователя для авторизации. */
  readonly username?: string | null;
  /** Возвращает пароль. */
  readonly password?: string | null;
  /** Возвращает идентификатор роли. */
  readonly role_id?: number | null;
  /** Возвращает дату рождения. */
  readonly birth_date?: string | null;
  /** Возвращает номер телефона. */
  readonly phone?: string | null;
  /** Возвращает адрес электронной почты. */
  readonly email?: string | null;
  /** Возвращает позицию. */
  readonly position?: string | null;
  /** Возвращает отдел. */
  readonly department?: string | null;
}

/** Представляет модель данных, получаемую по запросу подразделений. */
export interface StaffDepartmentResponse {
  /** Возвращает список подразделений. */
  readonly items: readonly string[];
}

/** Представляет модель данных, получаемую по запросу должностей. */
export interface StaffPositionResponse {
  /** Возвращает список должностей. */
  readonly items: readonly string[];
}
