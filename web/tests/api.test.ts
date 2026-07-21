import { describe, it, expect } from 'vitest';
import { ApiError } from '@/lib/api';

describe('api client', () => {
  it('ApiError carries status + detail', () => {
    const err = new ApiError(401, 'Unauthorized');
    expect(err.status).toBe(401);
    expect(err.detail).toBe('Unauthorized');
    expect(err.name).toBe('ApiError');
    expect(err.message).toContain('401');
  });
});
