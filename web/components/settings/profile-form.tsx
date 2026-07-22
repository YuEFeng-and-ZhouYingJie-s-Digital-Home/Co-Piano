'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Check, User as UserIcon, Mail } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api, ApiError } from '@/lib/api';

const schema = z.object({
  name: z.string().min(1, '昵称不能为空').max(50, '最多 50 字'),
});
type FormData = z.infer<typeof schema>;

interface ProfileFormProps {
  initial: { name: string; email: string };
}

export function ProfileForm({ initial }: ProfileFormProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: initial.name },
  });

  const onSubmit = (data: FormData) => {
    setError(null);
    setSuccess(false);
    startTransition(async () => {
      try {
        await api.patch('/api/v1/users/me', { name: data.name });
        setSuccess(true);
        router.refresh();
        setTimeout(() => setSuccess(false), 3000);
      } catch (e) {
        setError(e instanceof ApiError ? e.detail : '保存失败');
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">个人资料</CardTitle>
        <CardDescription>更新你的昵称</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">昵称</Label>
            <div className="relative">
              <UserIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="name"
                {...register('name')}
                className="pl-9"
                placeholder="你的称呼"
              />
            </div>
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">邮箱</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="email"
                value={initial.email}
                readOnly
                disabled
                className="pl-9 bg-muted"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              邮箱不可修改。如需更换请联系客服。
            </p>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-md bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
              <Check className="h-3.5 w-3.5" />
              已保存
            </div>
          )}

          <Button type="submit" variant="piano" disabled={pending || !isDirty}>
            {pending ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : null}
            保存
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
