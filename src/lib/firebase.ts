/**
 * Inicialização e exportação do Firebase SDK para o frontend do SAGA.
 *
 * Responsabilidades:
 * - Inicializar o Firebase App com as variáveis de ambiente do Vite:
 *   VITE_FIREBASE_API_KEY, VITE_FIREBASE_PROJECT_ID, VITE_AUTH_DOMAIN,
 *   VITE_FIRESTORE_DB.
 * - Exportar `auth` (getAuth) para uso no hook useAuth e nas páginas de login
 *   e primeiro acesso (signInWithEmailAndPassword, sendPasswordResetEmail,
 *   onAuthStateChanged).
 * - Exportar `db` (getFirestore) para uso no hook useNotifications via onSnapshot
 *   na coleção notifications/ filtrada por destinatario_id do usuário logado.
 * - Garantir inicialização única (singleton) independente de quantos módulos importem
 *   este arquivo.
 */

import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app, import.meta.env.VITE_FIRESTORE_DB);
