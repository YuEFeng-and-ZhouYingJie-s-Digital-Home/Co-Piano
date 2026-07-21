'use client';

import { useState } from 'react';
import { LogOut, Settings, User as UserIcon, CreditCard } from 'lucide-react';
import Link from 'next/link';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { logout } from '@/lib/auth-helpers';

interface UserMenuProps {
  name?: string | null;
  email?: string | null;
}

function getInitials(name?: string | null, email?: string | null): string {
  if (name) {
    return name.slice(0, 2);
  }
  if (email) {
    return email[0]?.toUpperCase() ?? '?';
  }
  return '?';
}

export function UserMenu({ name, email }: UserMenuProps) {
  const [pending, setPending] = useState(false);

  const onLogout = async () => {
    setPending(true);
    try {
      await logout();
    } finally {
      setPending(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-full p-1 hover:bg-muted">
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-piano-500/10 text-piano-700 dark:text-piano-300">
            {getInitials(name, email)}
          </AvatarFallback>
        </Avatar>
        <span className="hidden sm:inline text-sm font-medium pr-2">
          {name ?? email ?? '用户'}
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="font-medium">{name ?? '用户'}</div>
          <div className="text-xs text-muted-foreground truncate">{email}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/app/settings" className="cursor-pointer">
            <UserIcon className="mr-2 h-4 w-4" />
            账户
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/app/settings#subscription" className="cursor-pointer">
            <CreditCard className="mr-2 h-4 w-4" />
            订阅
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/app/settings" className="cursor-pointer">
            <Settings className="mr-2 h-4 w-4" />
            设置
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={onLogout}
          disabled={pending}
          className="text-destructive focus:text-destructive cursor-pointer"
        >
          <LogOut className="mr-2 h-4 w-4" />
          {pending ? '退出中...' : '退出登录'}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
