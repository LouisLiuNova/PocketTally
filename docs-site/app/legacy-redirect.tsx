import { redirect } from 'next/navigation';

export function LegacyRedirect({ path }: { path: string }): null {
  redirect(`/PocketTally/docs/${path}/`);
  return null;
}
