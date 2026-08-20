import { headers } from "next/headers";
import { getSettings } from "@/lib/settings";
import { PageHeader, Card } from "@/components/ui";
import { SettingsForm } from "@/components/settings-form";
import { ApiKeyPanel } from "@/components/api-key-panel";

export const dynamic = "force-dynamic";

async function currentOrigin(): Promise<string> {
  const hdrs = await headers();
  const host = hdrs.get("host") ?? "localhost:3000";
  const proto = hdrs.get("x-forwarded-proto") ?? (host.startsWith("localhost") || host.startsWith("127.") ? "http" : "https");
  return `${proto}://${host}`;
}

export default async function SettingsPage() {
  const [settings, origin] = await Promise.all([getSettings(), currentOrigin()]);

  return (
    <div className="max-w-2xl">
      <PageHeader title="Einstellungen" description="Bankroll, Staking-Strategie und Datenquellen konfigurieren" />
      <Card>
        <SettingsForm settings={settings} />
      </Card>

      <div className="mt-6">
        <h2 className="mb-1 text-sm font-semibold text-slate-200">Browser-Erweiterung (Tipico-Import)</h2>
        <p className="mb-3 text-xs text-slate-500">
          Diese Zugangsdaten in der Wettportal-Erweiterung hinterlegen, um platzierte Wetten mit einem Klick zu übernehmen.
        </p>
        <Card>
          <ApiKeyPanel initialApiKey={settings.apiKey ?? ""} origin={origin} />
        </Card>
      </div>
    </div>
  );
}
