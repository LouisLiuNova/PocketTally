import { redirect } from 'next/navigation';

export function LegacyRedirect({ path }: { path: string }): null {
  redirect(`/docs/${path}/`);
  return null;
}
