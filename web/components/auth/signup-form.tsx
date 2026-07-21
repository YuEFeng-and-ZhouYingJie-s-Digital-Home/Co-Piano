'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Mail, Lock, User as UserIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { loginWithCredentials } from '@/lib/auth-helpers';

const signupSchema = z
  .object({
    name: z.string().min(1, '请输入昵称').max(50),
    email: z.string().email('请输入有效邮箱'),
    password: z.string().min(8, '密码至少 8 位'),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: '两次密码不一致',
    path: ['confirm'],
  });

type SignupInput = z.infer<typeof signupSchema>;

export function SignupForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
  });

  const onSubmit = async (data: SignupInput) => {
    setError(null);
    setPending(true);
    try {
      // 1. 注册到后端
      await api.post('/api/v1/auth/signup', {
        email: data.email,
        password: data.password,
        name: data.name,
      });

      // 2. 自动登录
      const res = await loginWithCredentials(data.email, data.password);
      if (res?.error) {
        setError('注册成功但自动登录失败,请手动登录');
        router.push('/login');
        return;
      }
      router.push('/app');
      router.refresh();
    } catch (err) {
      const message =
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail: unknown }).detail)
          : '注册失败,请稍后重试';
      setError(message);
    } finally {
      setPending(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">昵称</Label>
        <div className="relative">
          <UserIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="name"
            type="text"
            autoComplete="nickname"
            placeholder="你的称呼"
            className="pl-9"
            {...register('name')}
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
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            className="pl-9"
            {...register('email')}
          />
        </div>
        {errors.email && (
          <p className="text-xs text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">密码</Label>
        <div className="relative">
          <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="至少 8 位"
            className="pl-9"
            {...register('password')}
          />
        </div>
        {errors.password && (
          <p className="text-xs text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirm">确认密码</Label>
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

      <Button type="submit" variant="piano" className="w-full" disabled={pending}>
        {pending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            创建账号中...
          </>
        ) : (
          '免费开始'
        )}
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        注册即表示你同意我们的{' '}
        <Link href="/terms" className="underline hover:text-foreground">
          服务条款
        </Link>{' '}
        和{' '}
        <Link href="/privacy" className="underline hover:text-foreground">
          隐私政策
        </Link>
      </p>
    </form>
  );
}
