-- CreateTable
CREATE TABLE "Bet" (
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
    "fixtureId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Bet_fixtureId_fkey" FOREIGN KEY ("fixtureId") REFERENCES "Fixture" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Fixture" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "externalId" TEXT,
    "league" TEXT NOT NULL,
    "homeTeam" TEXT NOT NULL,
    "awayTeam" TEXT NOT NULL,
    "kickoff" DATETIME NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'SCHEDULED',
    "source" TEXT NOT NULL DEFAULT 'MANUAL',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "Settings" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT DEFAULT 1,
    "startingBankroll" REAL NOT NULL DEFAULT 1000,
    "stakingMethod" TEXT NOT NULL DEFAULT 'FLAT',
    "flatStakeAmount" REAL NOT NULL DEFAULT 20,
    "percentageStake" REAL NOT NULL DEFAULT 2,
    "kellyFraction" REAL NOT NULL DEFAULT 0.5,
    "footballDataApiToken" TEXT,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE INDEX "Bet_matchDate_idx" ON "Bet"("matchDate");

-- CreateIndex
CREATE INDEX "Bet_status_idx" ON "Bet"("status");

-- CreateIndex
CREATE UNIQUE INDEX "Fixture_externalId_key" ON "Fixture"("externalId");

-- CreateIndex
CREATE INDEX "Fixture_kickoff_idx" ON "Fixture"("kickoff");
