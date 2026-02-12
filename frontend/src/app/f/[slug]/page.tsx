import { fetchFunnel } from '@/lib/api';
import FunnelWizard from '@/components/funnel/FunnelWizard';
import { notFound } from 'next/navigation';

interface FunnelPageProps {
  params: { slug: string };
}

export default async function FunnelPage({ params }: FunnelPageProps) {
  let funnel;
  try {
    funnel = await fetchFunnel(params.slug);
  } catch {
    notFound();
  }

  return <FunnelWizard funnel={funnel} />;
}
