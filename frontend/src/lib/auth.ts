import { betterAuth } from "better-auth";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),
  emailAndPassword: {
    enabled: true,
    // signUp temporariamente habilitado para criar primeiro usuario
  },
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5, // 5 min
    },
  },
  advanced: {
    cookies: {
      session_data: {
        attributes: {
          httpOnly: false, // JS precisa ler este cookie para enviar Bearer token ao backend cross-origin
        },
      },
    },
  },
});
