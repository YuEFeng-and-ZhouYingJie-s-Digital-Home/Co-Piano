'use client';

import { useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Lock, Loader2, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api, ApiError } from '@/lib/api';

const schema = z
  .object({
    current: z.string().min(8, '请输入当前密码'),
    next: z.string().min(8, '新密码至少 8 位'),
    confirm: z.string(),
  })
  .refine((d) => d.next === d.confirm, {
    message: '两次密码不一致',
    path: ['confirm'],
  });
type FormData = z.infer<typeof schema>;

export function ChangePasswordForm() {
  const [pending, startTransition] = useTransition();
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => {
    setError(null);
    setSuccess(false);
    startTransition(async () => {
      try {
        await api.post('/api/v1/users/me/change-password', {
          current_password: data.current,
          new_password: data.next,
        });
        setSuccess(true);
        reset();
        setTimeout(() => setSuccess(false), 3000);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '修改失败');
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Lock className="h-4 w-4" />
          修改密码
        </CardTitle>
        <CardDescription>定期更换密码可提升账户安全</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current">当前密码</Label>
            <Input
              id="current"
              type="password"
              autoComplete="current-password"
              {...register('current')}
            />
            {errors.current && (
              <p className="text-xs text-destructive">{errors.current.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="next">新密码</Label>
            <Input
              id="next"
              type="password"
              autoComplete="new-password"
              {...register('next')}
            />
            {errors.next && (
              <p className="text-xs text-destructive">{errors.next.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">确认新密码</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              {...register('confirm')}
            />
            {errors.confirm && (
              <p className="text-xs text-destructive">{errors.confirm.message}</p>
            )}
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-md bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
              <Check className="h-3.5 w-3.5" />
              密码已更新
            </div>
          )}

          <Button type="submit" variant="outline" disabled={pending}>
            {pending && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            更新密码
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
