export type ErrorContext = 'analysis' | 'fix' | 'request';
export function getUserFriendlyError(error: unknown, context?: ErrorContext): string;
