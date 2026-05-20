#!/usr/bin/env python3
"""
get_eos_token.py — Obtenir un EOS Token Rocket League (flux 3 étapes).

Usage : python get_eos_token.py
"""
import webbrowser
import sys
import os

# Ajoute le dossier parent au path pour importer rlapi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rlapi.egs import EGS


def main():
    print("=" * 55)
    print("  Epic Games — EOS Token pour Rocket League")
    print("=" * 55)
    print()
    print("Flux en 3 étapes :")
    print("  1. Connexion Epic (navigateur)")
    print("  2. Échange du code → token launcher")
    print("  3. Échange → token EOS Rocket League  ← le bon")
    print()
    print("⚠️  Copie vite le code, il expire en ~2 minutes !\n")

    input("Appuie sur Entrée pour ouvrir le navigateur...")

    egs = EGS()

    # ── Étape 1 : Ouvrir l'URL de login ───────────────────────────────────
    url = egs.get_auth_url()
    webbrowser.open(url)

    print("\nNavigateur ouvert.")
    print('Dans le JSON, copie la valeur de "authorizationCode"\n')

    auth_code = input("authorizationCode : ").strip()
    if not auth_code:
        print("❌ Aucun code fourni.")
        return

    try:
        # ── Étape 2 : Token launcher EGS ──────────────────────────────────
        print("\n⏳ Étape 2/3 — Token launcher...")
        launcher_token = egs.authenticate_with_code(auth_code)
        print(f"   ✅ Connecté en tant que : {launcher_token.display_name}")

        # ── Étape 3 : Exchange code → token EOS RL ────────────────────────
        print("⏳ Étape 3/3 — Token EOS Rocket League...")
        exchange_code = egs.get_exchange_code(launcher_token.access_token)
        eos_token = egs.exchange_eos_token(exchange_code)
        print("   ✅ Token EOS obtenu !")

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        return
    finally:
        egs.close()

    print("\n" + "─" * 55)
    print(f'EOS_TOKEN        = "{eos_token.access_token}"')
    print(f'EOS_REFRESH_TOKEN = "{eos_token.refresh_token}"')
    print(f'EPIC_ACCOUNT_ID  = "{eos_token.account_id}"')
    print(f'ACCOUNT_NAME     = "{launcher_token.display_name}"')
    print(f"Expire dans      : {eos_token.expires_in}s")
    print("─" * 55)
    print()
    print("→ Colle ces valeurs dans get_rank.py et lance :")
    print("  python get_rank.py epic <pseudo_cible>")


if __name__ == "__main__":
    main()