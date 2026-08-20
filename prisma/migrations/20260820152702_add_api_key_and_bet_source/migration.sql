-- AlterTable
ALTER TABLE "Settings" ADD COLUMN "apiKey" TEXT;

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Bet" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "placedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "league" TEXT NOT NULL,
    "homeTeam" TEXT NOT NULL,
    "awayTeam" TEXT NOT NULL,
    "matchDate" DATETIME NOT NULL,
    "market" TEXT NOT NULL,
    "selection" TEXT NOT NULL,
    "odds" REAL NOT NULL,
    "stake" REAL NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'PENDING',
    "payout" REAL,
    "notes" TEXT,
    "source" TEXT NOT NULL DEFAULT 'MANUAL',
    "fixtureId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Bet_fixtureId_fkey" FOREIGN KEY ("fixtureId") REFERENCES "Fixture" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_Bet" ("awayTeam", "createdAt", "fixtureId", "homeTeam", "id", "league", "market", "matchDate", "notes", "odds", "payout", "placedAt", "selection", "stake", "status", "updatedAt") SELECT "awayTeam", "createdAt", "fixtureId", "homeTeam", "id", "league", "market", "matchDate", "notes", "odds", "payout", "placedAt", "selection", "stake", "status", "updatedAt" FROM "Bet";
DROP TABLE "Bet";
ALTER TABLE "new_Bet" RENAME TO "Bet";
CREATE INDEX "Bet_matchDate_idx" ON "Bet"("matchDate");
CREATE INDEX "Bet_status_idx" ON "Bet"("status");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE UNIQUE INDEX "Settings_apiKey_key" ON "Settings"("apiKey");

