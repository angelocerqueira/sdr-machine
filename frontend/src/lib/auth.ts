import { betterAuth } from "better-auth";
import { Pool } from "pg";

const trustedOrigins =
  process.env.BETTER_AUTH_TRUSTED_ORIGINS?.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean) ?? [];

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),
  trustedOrigins,
  emailAndPassword: {
    enabled: true,
    // signUp temporariamente habilitado para criar primeiro usuario
  },
  session: {
    expiresIn: 60 * 60 * 24 * 30, // 30 dias
    updateAge: 60 * 60 * 24, // renova a cada 1 dia de uso
    cookieCache: {
      enabled: true,
      maxAge: 60 * 60 * 24 * 7, // 7 dias — deve acompanhar o tempo de sessao pra evitar 401 prematuro
    },
  },
  advanced: {
    cookies: {
      session_data: {
        attributes: {
          httpOnly: false, // JS precisa ler este cookie para enviar Bearer token ao backend cross-origin
          secure: process.env.NODE_ENV === "production",
          sameSite: "lax" as const,
        },
      },
    },
  },
});
