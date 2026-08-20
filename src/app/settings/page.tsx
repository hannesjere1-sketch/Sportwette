import { getSettings } from "@/lib/settings";
import { PageHeader, Card } from "@/components/ui";
import { SettingsForm } from "@/components/settings-form";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const settings = await getSettings();

  return (
    <div className="max-w-2xl">
      <PageHeader title="Einstellungen" description="Bankroll, Staking-Strategie und Datenquellen konfigurieren" />
      <Card>
        <SettingsForm settings={settings} />
      </Card>
    </div>
  );
}
