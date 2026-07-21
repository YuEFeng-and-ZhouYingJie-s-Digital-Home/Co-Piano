import 'next-auth';
import 'next-auth/jwt';

/**
 * NextAuth 类型扩展 — 给 session.user 加 id,给 session 加 accessToken
 */

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
    refreshToken?: string;
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }

  interface User {
    id?: string;
    accessToken?: string;
    refreshToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    userId?: string;
  }
}
