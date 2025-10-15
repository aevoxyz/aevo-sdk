# Étapes de déploiement (Hardhat)

1. Copier `.env.example` en `.env` et renseigner les variables (RPC + PRIVATE_KEY testnet).
2. Installer: `pnpm install` (ou `yarn` / `npm i`).
3. Compiler: `pnpm hardhat compile`.
4. Déployer Greeter sur Base Sepolia:
   ```
   pnpm hardhat run scripts/deploy_greeter.ts --network baseSepolia
   ```
5. L'adresse est écrite dans `addresses/base-sepolia.json`.
6. (Optionnel) Vérifier le contrat sur BaseScan:
   ```
   VERIFY_ADDRESS=0x... pnpm hardhat verify --network baseSepolia 0x...
   ```
